import os
import json
from time import sleep

import cudatext as ct
import cudatext_cmd as ct_cmd
import cudax_lib as ctx

from . import differ as df
from .scroll import ScrollSplittedTab
from .ui import DifferDialog, file_history


DIFF_TAG = 148
NKIND_DELETED = 24
NKIND_ADDED = 25
NKIND_CHANGED = 26
GAP_WIDTH = 5000
DECOR_CHAR = '■'
DEFAULT_SYNC_SCROLL = '1'

METAJSONFILE = os.path.dirname(__file__) + os.sep + 'differ_opts.json'
JSONFILE = 'cuda_differ.json'  # To store in settings/cuda_differ.json
JSONPATH = ct.app_path(ct.APP_DIR_SETTINGS) + os.sep + JSONFILE
OPTS_META = [
    {'opt': 'differ.changed_color',
     'cmt': 'Color of changed lines',
     'def': '',
     'frm': '#rgb-e',
     'chp': 'colors',
     },
    {'opt': 'differ.added_color',
     'cmt': 'Color of added lines',
     'def': '',
     'frm': '#rgb-e',
     'chp': 'colors',
     },
    {'opt': 'differ.deleted_color',
     'cmt': 'Color of deleted lines',
     'def': '',
     'frm': '#rgb-e',
     'chp': 'colors',
     },
    {'opt': 'differ.gap_color',
     'cmt': 'Color of inter-line gap background',
     'def': '',
     'frm': '#rgb-e',
     'chp': 'colors',
     },
    {'opt': 'differ.sync_scroll',
     'cmt': 'Use synchronized scrolling (vertical/horizontal) in two compared files',
     'def': True,
     'frm': 'bool',
     'chp': 'config',
     },
    {'opt': 'differ.compare_with_details',
     'cmt': 'Perform detailed comparision',
     'def': True,
     'frm': 'bool',
     'chp': 'config',
     },
    {'opt': 'differ.ratio_percents',
     'cmt': 'Measure of the sequences’ similarity, in percents',
     'def':  75,
     'frm': 'int',
     'chp': 'config',
     },
    {'opt': 'differ.keep_caret_visible',
     'cmt': 'On sync-scrolling, keep carets in both editors visible on current screen area',
     'def':  False,
     'frm': 'bool',
     'chp': 'config',
     },
]


def get_opt(key, dval=''):
    return ctx.get_opt('differ.' + key, dval, user_json=JSONFILE) \
           if ctx.version(0) >= '0.6.8' \
           else ctx.get_opt('differ.' + key, dval)


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
        self.scroll = ScrollSplittedTab(__name__)
        self.cfg = self.get_config()
        self.diff = df.Differ()
        self.diff_dlg = DifferDialog()
        self.curdiff = 0

    def change_config(self):
        import cuda_options_editor as op_ed
        op_ed_dlg = None
        subset = 'differ.'  # Key to isolate settings for op_ed plugin
        how = dict(hide_lex_fil = True,  # If option has not setting for lexer/cur.file
                   stor_json = JSONFILE)
        try:  # New op_ed allows to skip meta-file
            op_ed_dlg   = op_ed.OptEdD(
                path_keys_info = OPTS_META,     subset = subset, how = how)
        except:
            # Old op_ed requires to use meta-file
            if not os.path.exists(METAJSONFILE) \
            or os.path.getmtime(METAJSONFILE) < os.path.getmtime(__file__):
                # Create/update meta-info file
                open(METAJSONFILE, 'w').write(json.dumps(OPTS_META, indent=4))
            op_ed_dlg = op_ed.OptEdD(
                path_keys_info = METAJSONFILE, subset = subset, how = how)
        if op_ed_dlg.show('Differ Options'):  # Dialog caption
            # Need to use updated options
            self.config()
            self.scroll.toggle(self.cfg['sync_scroll'])
            self.scroll.keep_caret_visible = self.cfg['keep_caret_visible']

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
                    
                    ct.app_idle(True) # better close file
                    sleep(0.3)
                    ct.app_idle(True) # better close file
                    break

        ct.file_open(files, options='/nohistory')
        self.refresh()

        # if file was in group-2, and now group-2 is empty, set "one group" mode
        if ct.app_proc(ct.PROC_GET_GROUPING, '') in [ct.GROUPS_2VERT, ct.GROUPS_2HORZ]:
            e = ct.ed_group(1) # Editor obj in group-2
            if not e:
                ct.app_proc(ct.PROC_SET_GROUPING, ct.GROUPS_ONE)

    def on_state(self, ed_self, state):
        if state == ct.APPSTATE_THEME_SYNTAX:
            self.get_config()
            self.refresh()

    def on_scroll(self, ed_self):
        self.scroll.on_scroll(ed_self)

    def on_tab_change(self, ed_self):
        self.config()
        self.scroll.toggle(self.cfg.get('sync_scroll'))

    def refresh(self):
        self.curdiff = 0
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
        self.scroll.toggle(self.cfg.get('sync_scroll'))

        self.diff.withdetail = self.cfg.get('compare_with_details')
        self.diff.ratio = self.cfg.get('ratio')

        for d in self.diff.compare():
            diff_id, y = d[0], d[1]
            if diff_id == df.A_LINE_DEL:
                self.set_bookmark2(a_ed, y, NKIND_DELETED)
                self.set_decor(a_ed, y, DECOR_CHAR, self.cfg.get('color_deleted'))
            elif diff_id == df.B_LINE_ADD:
                self.set_bookmark2(b_ed, y, NKIND_ADDED)
                self.set_decor(b_ed, y, DECOR_CHAR, self.cfg.get('color_added'))
            elif diff_id == df.A_LINE_CHANGE:
                self.set_bookmark2(a_ed, y, NKIND_CHANGED)
            elif diff_id == df.B_LINE_CHANGE:
                self.set_bookmark2(b_ed, y, NKIND_CHANGED)
            elif diff_id == df.A_GAP:
                self.set_gap(a_ed, y, d[2])
            elif diff_id == df.B_GAP:
                self.set_gap(b_ed, y, d[2])
            elif diff_id == df.A_SYMBOL_DEL:
                self.set_attr(a_ed, d[2], y, d[3], self.cfg.get('color_deleted'))
            elif diff_id == df.B_SYMBOL_ADD:
                self.set_attr(b_ed, d[2], y, d[3], self.cfg.get('color_added'))
            elif diff_id == df.A_DECOR_YELLOW:
                self.set_decor(a_ed, y, DECOR_CHAR, self.cfg.get('color_changed'))
            elif diff_id == df.B_DECOR_YELLOW:
                self.set_decor(b_ed, y, DECOR_CHAR, self.cfg.get('color_changed'))
            elif diff_id == df.A_DECOR_RED:
                self.set_decor(a_ed, y, DECOR_CHAR, self.cfg.get('color_deleted'))
            elif diff_id == df.B_DECOR_GREEN:
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
        if self.cfg.get('opt_time') == opt_time and \
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
            data = ct.app_proc(ct.PROC_THEME_SYNTAX_DICT_GET, '')
            th = {}
            th['color_changed'] = data['LightBG2']['color_back']
            th['color_added'] = data['LightBG3']['color_back'] 
            th['color_deleted'] = data['LightBG1']['color_back']
            return th

        t = get_theme()
        config = {
            'opt_time':
                os.path.getmtime(JSONPATH) if os.path.exists(JSONPATH) else 0,
            'theme_name':
                ct.app_proc(ct.PROC_THEME_SYNTAX_GET, ''),
            'color_changed':
                get_color('changed_color', t.get('color_changed')),
            'color_added':
                get_color('added_color', t.get('color_added')),
            'color_deleted':
                get_color('deleted_color', t.get('color_deleted')),
            'color_gaps':
                get_color('gap_color', ct.COLOR_NONE),
            'sync_scroll':
                get_opt('sync_scroll', DEFAULT_SYNC_SCROLL == '1'),
            'compare_with_details':
                get_opt('compare_with_details', True),
            'ratio':
                get_opt('ratio_percents',  75)/100,
            'keep_caret_visible':
                get_opt('keep_caret_visible', False),
        }

        self.scroll.keep_caret_visible = config['keep_caret_visible']

        new_nkind(NKIND_DELETED, config.get('color_deleted'))
        new_nkind(NKIND_ADDED, config.get('color_added'))
        new_nkind(NKIND_CHANGED, config.get('color_changed'))

        return config

    def clear_history(self):
        file_history.clear()
        file_history.save()

    def jump(self):
        if not self.diff.diffmap:
            return ct.msg_status("No differences found")
        if len(self.diff.diffmap) == 1:
            ct.msg_status("Found only one difference")
        hndl_primary = ct.ed.get_prop(ct.PROP_HANDLE_PRIMARY)
        hndl_secondary = ct.ed.get_prop(ct.PROP_HANDLE_SECONDARY)
        a_ed = ct.Editor(hndl_primary)
        b_ed = ct.Editor(hndl_secondary)

        current = self.diff.diffmap[self.curdiff]
        a_ed.set_caret(0, current[0], 0, current[1], ct.CARET_SET_ONE)
        b_ed.set_caret(0, current[2], 0, current[3], ct.CARET_SET_ONE)

    def jump_next(self):
        if not self.diff.diffmap:
            return
        self.curdiff += 1
        if self.curdiff >= len(self.diff.diffmap):
            self.curdiff = 0
        self.jump()

    def jump_prev(self):
        if not self.diff.diffmap:
            return
        self.curdiff -= 1
        if self.curdiff < 0:
            self.curdiff = len(self.diff.diffmap)-1
        self.jump()

    def copy(self, copy_to_tight=True):
        if not self.diff.diffmap:
            return
        hndl_self = ct.ed.get_prop(ct.PROP_HANDLE_SELF)
        hndl_primary = ct.ed.get_prop(ct.PROP_HANDLE_PRIMARY)
        hndl_secondary = ct.ed.get_prop(ct.PROP_HANDLE_SECONDARY)
        if hndl_self == hndl_primary:
            current_primary = True
        else:
            current_primary = False

        x, y, x2, y2 = ct.ed.get_carets()[0]
        for cd in self.diff.diffmap:
            if current_primary:
                p0 = cd[0]
                p1 = cd[1]
            else:
                p0 = cd[2]
                p1 = cd[3]
            if y in range(p0, p1):
                a0, a1, b0, b1 = cd
                self.curdiff = self.diff.diffmap.index(cd)
                self.diff.diffmap.pop(self.curdiff)
                print(cd)
                break
        else:
            return

        a_ed = ct.Editor(hndl_primary)
        b_ed = ct.Editor(hndl_secondary)

        if copy_to_tight:
            text = a_ed.get_text_substr(0, a0, 0, a1)
        else:
            text = b_ed.get_text_substr(0, b0, 0, b1)
        a_ed.gap(ct.GAP_DELETE, a0-1, a1)
        b_ed.gap(ct.GAP_DELETE, b0-1, b1)
        a_ed.attr(ct.MARKERS_DELETE_BY_TAG, tag=DIFF_TAG)
        b_ed.attr(ct.MARKERS_DELETE_BY_TAG, tag=DIFF_TAG)
        a_ed.delete(0, a0, 0, a1)
        b_ed.delete(0, b0, 0, b1)
        if text:
            a_ed.insert(0, a0, text)
            b_ed.insert(0, b0, text)

        if copy_to_tight:
            delta = (b1 - b0) - (a1 - a0)
            for n in range(self.curdiff, len(self.diff.diffmap)):
                self.diff.diffmap[n][2] -= delta
                self.diff.diffmap[n][3] -= delta
        else:
            delta = (a1 - a0) - (b1 - b0)
            for n in range(self.curdiff, len(self.diff.diffmap)):
                self.diff.diffmap[n][0] -= delta
                self.diff.diffmap[n][1] -= delta

    def copy_right(self):
        self.copy(True)

    def copy_left(self):
        self.copy(False)

    # def focus_to_opposit_panel(self):
    #     if ct.ed.get_prop(ct.PROP_SPLIT)[0] == '-':
    #         print(1)
    #         return
    #     hndl_self = ct.ed.get_prop(ct.PROP_HANDLE_SELF)
    #     hndl_primary = ct.ed.get_prop(ct.PROP_HANDLE_PRIMARY)
    #     hndl_secondary = ct.ed.get_prop(ct.PROP_HANDLE_SECONDARY)
    #     print(hndl_self, hndl_primary, hndl_secondary)
    #     if hndl_self == hndl_primary:
    #         e = ct.Editor(hndl_secondary)
    #         e.focus()
    #     else:
    #         e = ct.Editor(hndl_primary)
    #         e.focus()
