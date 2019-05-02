import os
import cudatext as ct
import cudatext_cmd as ct_cmd
from .differ import Differ
from .scroll import ScrollSplittedTab
from .ui import DifferDialog, file_history

import json
import cudax_lib    as ctx
import cuda_options_editor as op_ed


DIFF_TAG = 148
NKIND_DELETED = 24
NKIND_ADDED = 25
NKIND_CHANGED = 26
GAP_WIDTH = 5000
DECOR_CHAR = '■'
DEFAULT_SYNC_SCROLL = '1'


METAJSONFILE = os.path.dirname(__file__)+os.sep+'differ_opts.json'
JSONFILE     = 'cuda_differ.json'    # To store in settings/cuda_differ.json
JSONPATH     = ct.app_path(ct.APP_DIR_SETTINGS)+os.sep+JSONFILE
OPTS_META    = [
    {'opt':'differ.changed_color',
     'cmt':'Color of changed lines',
     'def':'',
     'frm':'#rgb-e',
     'chp':'colors',
    },
    {'opt':'differ.added_color',
     'cmt':'Color of added lines',
     'def':'',
     'frm':'#rgb-e',
     'chp':'colors',
    },
    {'opt':'differ.deleted_color',
     'cmt':'Color of deleted lines',
     'def':'',
     'frm':'#rgb-e',
     'chp':'colors',
    },
    {'opt':'differ.gap_color',
     'cmt':'Color of inter-line gap background',
     'def':'',
     'frm':'#rgb-e',
     'chp':'colors',
    },
    {'opt':'differ.enable_scroll_default',
     'cmt':'Enable automatical sync-scrolling in both compared files',
     'def':True,
     'frm':'bool',
     'chp':'config',
    },
    {'opt':'differ.compare_with_details',
     'cmt':'Detailed compare',
     'def':True,
     'frm':'bool',
     'chp':'config',
    },
    {'opt':'differ.ratio',
     'cmt':'Measure of the sequences’ similarity, float value in the range [0, 1]',
     'def': 0.75,
     'frm':'float',
     'chp':'config',
    },
]

def get_opt(key, dval=''):
    return  ctx.get_opt('differ.'+key,     dval,    user_json=JSONFILE) if ctx.version(0)>='0.6.8' else \
            ctx.get_opt('differ.'+key,     dval)

#def set_opt(section, key, val):
#   return ctx.set_opt('differ.'+section+'.'+key,     val,      user_json=JSONFILE)

def msg(s, level=0):
    PLG_NAME = 'Differ'
    if level == 0:
        print(PLG_NAME + ':', s)
    elif level == 1:
        print(PLG_NAME + ' WARNING:', s)
    elif level == 2:
        print(PLG_NAME + ' ERROR:', s)


class Command:
    def __init__(self):
        self.cfg = self.get_config()
        self.diff = Differ()
        self.diff_dlg = DifferDialog()
        self.scroll = ScrollSplittedTab(__name__)

    def change_config(self):
        if not os.path.exists(   METAJSONFILE):     # Create meta-info file if no one
            open(METAJSONFILE, 'w').write(json.dumps(OPTS_META, indent=4))
        if op_ed.OptEdD(
                path_keys_info = METAJSONFILE,
                subset = 'differ.',                 # Key to isolate settings for op_ed plugin
                how = dict(hide_lex_fil=True,       # If option has not setting for lexer/cur.file
                           stor_json = JSONFILE),
            ).show('Differ Options'):               # Dialog caption
           # Need to use updated options
           print('Applying options...')
           #???

    def choose_files(self):
        files = self.diff_dlg.run()
        if files is None:
            return

        for f in files:
            for h in ct.ed_handles():
                e = ct.Editor(h)
                file_name = e.get_filename()
                if file_name == f:
                    if e.get_prop(ct.PROP_MODIFIED):
                        text = 'First you must save file:\n' + \
                                file_name + \
                               '\nYES: save and continue\n' + \
                               "NO: don't save (changes will be lost)"
                        mb = ct.msg_box(text,
                                        ct.MB_YESNOCANCEL+ct.MB_ICONQUESTION)
                        if mb == ct.ID_YES:
                            e.save(file_name)
                        elif mb == ct.ID_NO:
                            e.set_prop(ct.PROP_MODIFIED, False)
                        else:
                            return
                    e.focus()
                    e.cmd(ct_cmd.cmd_FileClose)
                    break

        ct.file_open(files, options='/nohistory')
        self.refresh()

        # if file was in group-2, and now group-2 is empty, set "one group" mode
        if ct.app_proc(ct.PROC_GET_GROUPING, '') in [ct.GROUPS_2VERT, ct.GROUPS_2HORZ]:
            e = ct.ed_group(1) # Editor obj in group-2
            if not e:
                ct.app_proc(ct.PROC_SET_GROUPING, ct.GROUPS_ONE)

    def on_scroll(self, ed_self):
        self.scroll.on_scroll(ed_self)

    def on_tab_change(self, ed_self):
        self.config()
        self.scroll.toggle(self.cfg.get('enable_scroll'))

    def refresh(self):
        if ct.ed.get_prop(ct.PROP_EDITORS_LINKED):
            return

        a_ed = ct.Editor(ct.ed.get_prop(ct.PROP_HANDLE_PRIMARY))
        b_ed = ct.Editor(ct.ed.get_prop(ct.PROP_HANDLE_SECONDARY))
        a_file, b_file = a_ed.get_filename(), b_ed.get_filename()

        if a_file == b_file:
            return

        a_text_all = a_ed.get_text_all()
        b_text_all = b_ed.get_text_all()

        if a_text_all == '':
            t = 'The file:\n{}\nis empty.'.format(a_file)
            ct.msg_box(t, ct.MB_OK)
            return

        if b_text_all == '':
            t = 'The file:\n{}\nis empty.'.format(b_file)
            ct.msg_box(t, ct.MB_OK)
            return

        if a_text_all == b_text_all:
            t = 'The files are identical:\n{0}\n{1}'.format(a_file, b_file)
            ct.msg_box(t, ct.MB_OK)
            return

        a_ed.set_prop(ct.PROP_WRAP, ct.WRAP_OFF)
        b_ed.set_prop(ct.PROP_WRAP, ct.WRAP_OFF)

        self.clear(a_ed)
        self.clear(b_ed)
        self.config()

        self.diff.set_seqs(a_text_all.splitlines(True),
                           b_text_all.splitlines(True))

        self.scroll.tab_id.add(ct.ed.get_prop(ct.PROP_TAB_ID))
        self.scroll.toggle(self.cfg.get('enable_scroll'))

        for d in self.diff.compare(self.cfg.get('compare_with_details'), self.cfg.get('ratio')):
            diff_id, y = d[0], d[1]
            if diff_id == '-':
                self.set_bookmark2(a_ed, y, NKIND_DELETED)
                self.set_decor(a_ed, y, DECOR_CHAR, self.cfg.get('color_deleted'))
            elif diff_id == '+':
                self.set_bookmark2(b_ed, y, NKIND_ADDED)
                self.set_decor(b_ed, y, DECOR_CHAR, self.cfg.get('color_added'))
            elif diff_id == '-*':
                self.set_bookmark2(a_ed, y, NKIND_CHANGED)
            elif diff_id == '+*':
                self.set_bookmark2(b_ed, y, NKIND_CHANGED)
            elif diff_id == '-^':
                self.set_gap(a_ed, y, d[2])
            elif diff_id == '+^':
                self.set_gap(b_ed, y, d[2])
            elif diff_id == '++':
                self.set_attr(b_ed, d[2], y, d[3], self.cfg.get('color_added'))
            elif diff_id == '--':
                self.set_attr(a_ed, d[2], y, d[3], self.cfg.get('color_deleted'))
            elif diff_id == '-y':
                self.set_decor(a_ed, y, DECOR_CHAR, self.cfg.get('color_changed'))
            elif diff_id == '+y':
                self.set_decor(b_ed, y, DECOR_CHAR, self.cfg.get('color_changed'))
            elif diff_id == '-r':
                self.set_decor(a_ed, y, DECOR_CHAR, self.cfg.get('color_deleted'))
            elif diff_id == '+g':
                self.set_decor(b_ed, y, DECOR_CHAR, self.cfg.get('color_added'))

    def set_attr(self, e, x, y, nlen, bg):
        e.attr(ct.MARKERS_ADD, DIFF_TAG,
               x,
               y,
               nlen,
               color_bg=bg,
               show_on_map=True
               )

    def set_gap(self, e, row, n=1):
        "set gap line after row line"
        # print('gap:', row, n)
        _, h = e.get_prop(ct.PROP_CELL_SIZE)
        h_size = h * n
        e.gap(ct.GAP_ADD, row-1, 0,
              tag=DIFF_TAG,
              size=h_size,
              color=self.cfg.get('color_gaps')
              )

    def set_decor(self, e, row, text, color):
        e.decor(ct.DECOR_SET, row, DIFF_TAG, text, color, bold=True)

    def set_bookmark2(self, e, row, nk):
        e.bookmark(ct.BOOKMARK2_SET, row,
                   nkind=nk,
                   text="",
                   auto_del=True,
                   show=False,
                   tag=DIFF_TAG
                   )

    def clear(self, e):
        if e is None:
            return
        e.attr(ct.MARKERS_DELETE_BY_TAG, DIFF_TAG)
        e.gap(ct.GAP_DELETE_ALL, 0, 0)
        e.decor(ct.DECOR_DELETE_BY_TAG, tag=DIFF_TAG)
        e.bookmark(ct.BOOKMARK2_DELETE_BY_TAG, 0, tag=DIFF_TAG)

    def config(self):
        opt_time = os.path.getmtime(JSONPATH) if os.path.exists(JSONPATH) else 0
        theme_name = ct.app_proc(ct.PROC_THEME_SYNTAX_GET, '')
        if self.cfg.get('opt_time') == opt_time     and \
           self.cfg.get('theme_name') == theme_name:
            return
        self.cfg = self.get_config()

    def get_config(self):

        def get_color(key, default_color):
            s = get_opt(key, '')
            if s:
                return ctx.html_color_to_int(s)
            else:
                return default_color

        def new_nkind(val, color):
            ct.ed.bookmark(ct.BOOKMARK_SETUP, 0,
                           nkind=val,
                           ncolor=color,
                           text=''
                           )

        def get_theme():
            th = {}
            for i in ct.app_proc(ct.PROC_THEME_SYNTAX_DATA_GET, ''):
                if i.get('name') == 'LightBG2':
                    cb = i.get('color_back')
                    if cb == '':
                        cb = 0x003030
                    th.setdefault('color_changed', cb)
                if i.get('name') == 'LightBG3':
                    cb = i.get('color_back')
                    if cb == '':
                        cb = 0x124200
                    th.setdefault('color_added', cb)
                if i.get('name') == 'LightBG1':
                    cb = i.get('color_back')
                    if cb == '':
                        cb = 0x07003D
                    th.setdefault('color_deleted', cb)
            return th

        t = get_theme()
        config = {
            'opt_time':     os.path.getmtime(JSONPATH) if os.path.exists(JSONPATH) else 0,
            'theme_name':   ct.app_proc(ct.PROC_THEME_SYNTAX_GET, ''),
            'color_changed':    get_color('changed_color',  t.get('color_changed')),
            'color_added':      get_color('added_color',    t.get('color_added')),
            'color_deleted':    get_color('deleted_color',  t.get('color_deleted')),
            'color_gaps':       get_color('gap_color',      ct.COLOR_NONE),
            'enable_scroll':        get_opt('enable_scroll_default', DEFAULT_SYNC_SCROLL == '1'),
            'compare_with_details': get_opt('compare_with_details', True),
            'ratio':                get_opt('ratio',  0.75)
        }

        new_nkind(NKIND_DELETED, config.get('color_deleted'))
        new_nkind(NKIND_ADDED, config.get('color_added'))
        new_nkind(NKIND_CHANGED, config.get('color_changed'))

        return config


    def clear_history(self):

        file_history.clear()
        file_history.save()


    def jump(self, next):

        # merge two lists, Decor and Gaps, into single list of line numbers

        items1 = ct.ed.decor(ct.DECOR_GET_ALL) or []
        items1 = [i['line'] for i in items1 if i['tag']==DIFF_TAG]
        #print('i1', items1)

        items2 = ct.ed.gap(ct.GAP_GET_LIST, 0, 0) or []
        items2 = [i[0] for i in items2 if i[1]==DIFF_TAG]
        #print('i2', items2)

        items2 = [i for i in items2 if i not in items1]
        items = sorted(items1+items2)
        if not items: return
        #print('i', items)

        x, y, x2, y2 = ct.ed.get_carets()[0]

        if next:
            items = [i for i in items if i>y]
            if not items:
                return ct.msg_status('Cannot find next difference')
            y = items[0]
        else:
            items = [i for i in items if i<y]
            if not items:
                return ct.msg_status('Cannot find previous difference')
            y = items[-1]

        ct.ed.set_caret(0, y, -1, -1)
        ct.msg_status('Jumped to line %d'%(y+1))


    def jump_next(self):

        self.jump(True)

    def jump_prev(self):

        self.jump(False)

