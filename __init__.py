import os
import json
from time import sleep
import typing as tp
from pathlib import Path
from datetime import datetime
#from time import strftime

import cudatext as ct
import cudatext_cmd as ct_cmd
import cudax_lib as ctx

from . import differ as df
from .scroll import ScrollSplittedTab
from .ui import DifferDialog, file_history

from cudax_lib import get_translation
_ = get_translation(__file__)  # I18N


DIFF_TAG = 148
NKIND_DELETED = 24
NKIND_ADDED = 25
NKIND_CHANGED = 26
GAP_WIDTH = 5000
DECOR_CHAR = '■'
DEFAULT_SYNC_SCROLL = '1'
U_PREFIX = 'untitled:'

PLG_NAME = _('Differ')
METAJSONFILE = os.path.dirname(__file__) + os.sep + 'differ_opts.json'
JSONFILE = 'cuda_differ.json'  # To store in settings/cuda_differ.json
JSONPATH = ct.app_path(ct.APP_DIR_SETTINGS) + os.sep + JSONFILE

OPTS_META = [
    {'opt': 'differ.changed_color',
     'cmt': _('Color of changed lines'),
     'def': '',
     'frm': '#rgb-e',
     'chp': 'colors',
     },
    {'opt': 'differ.added_color',
     'cmt': _('Color of added lines'),
     'def': '',
     'frm': '#rgb-e',
     'chp': 'colors',
     },
    {'opt': 'differ.deleted_color',
     'cmt': _('Color of deleted lines'),
     'def': '',
     'frm': '#rgb-e',
     'chp': 'colors',
     },
    {'opt': 'differ.gap_color',
     'cmt': _('Color of inter-line gap background'),
     'def': '',
     'frm': '#rgb-e',
     'chp': 'colors',
     },
    {'opt': 'differ.sync_scroll',
     'cmt': _('Use synchronized scrolling (vertical/horizontal) in two compared files'),
     'def': True,
     'frm': 'bool',
     'chp': 'config',
     },
    {'opt': 'differ.compare_with_details',
     'cmt': _('Perform detailed comparision'),
     'def': True,
     'frm': 'bool',
     'chp': 'config',
     },
    {'opt': 'differ.ratio_percents',
     'cmt': _('Measure of the sequences’ similarity, in percents'),
     'def':  75,
     'frm': 'int',
     'chp': 'config',
     },
    {'opt': 'differ.enable_sync_caret',
     'cmt': _('Keep carets in both editors visible on current screen area'),
     'def':  False,
     'frm': 'bool',
     'chp': 'config',
     },
    {'opt': 'differ.enable_auto_refresh',
     'cmt': _('Auto diff refresh after changes'),
     'def':  False,
     'frm': 'bool',
     'chp': 'config',
     },
     {'opt': 'differ.diff_context',
     'cmt': _('Number of lines of context displayed when diffing files'),
     'def':  3,
     'frm': 'int',
     'chp': 'config',
     },
]

TEMP_DIR = os.path.join(ct.app_path(ct.APP_DIR_SETTINGS), 'differ_backup')
DIFF_TAB_COUNT = 1
TIMESTAMP_BEGIN = '_{'
TIMESTAMP_END = '}.txt'


def get_temp_name(e: ct.Editor):
    global TEMP_DIR
    if not os.path.isdir(TEMP_DIR):
        os.mkdir(TEMP_DIR)
    if not os.path.isdir(TEMP_DIR):
        return
    cnt = 0
    now = datetime.now()
    title = e.get_prop(ct.PROP_TAB_TITLE)
    while True:
        cnt += 1
        fn = os.path.join(TEMP_DIR, title+TIMESTAMP_BEGIN+now.strftime('%Y.%m.%d-%H.%M')+'-'+str(cnt)+TIMESTAMP_END)
        if not os.path.isfile(fn):
            return fn


_homedir = os.path.expanduser('~')

def collapse_filename(fn):
    if (fn+'/').startswith(_homedir+'/'):
        fn = fn.replace(_homedir, '~', 1)
    return fn


def get_opt(key, def_val: tp.Any = ''):
    return ctx.get_opt('differ.' + key, def_val, user_json=JSONFILE)


def msg(s, level=0):
    if level == 0:
        print(PLG_NAME + ':', s)
    elif level == 1:
        print(PLG_NAME + _(' WARNING:'), s)
    elif level == 2:
        print(PLG_NAME + _(' ERROR:'), s)


def prettify_pair_title(title):
    if not (TIMESTAMP_BEGIN in title and TIMESTAMP_END in title):
        return
    SEP = ' | '
    names = title.split(SEP)
    if len(names) != 2:
        return
    for (i, s) in enumerate(names):
        n = s.find(TIMESTAMP_BEGIN)
        if n>0 and s.endswith(TIMESTAMP_END):
            names[i] = s[:n]
    return SEP.join(names)



def delete_all_files_in_folder(folder_path):
    if not os.path.exists(folder_path):
        # print(f"ERROR: Differ: Folder {folder_path} does not exist")
        return

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)  # Remove the file
            # elif os.path.isdir(file_path):
            #    shutil.rmtree(file_path)  # Remove the directory
        except Exception as e:
            print(f'ERROR: Differ failed to delete "{file_path}", reason: {e}')


class Command:
    def __init__(self):
        self.scroll = ScrollSplittedTab(__name__)
        self.cfg = self.get_config()
        self.diff = df.Differ()
        self.diff_dlg = DifferDialog()
        self.diff_tabs = []

        self.compare_menu = None
        self.menuid_sep = None
        self.menuid_withfile = None
        self.menuid_withtab = None

    def change_config(self):
        try:
            import cuda_options_editor as op_ed
        except ImportError:
            import cuda_prefs as op_ed
        op_ed_dlg = None
        subset = 'differ.'  # Key to isolate settings for op_ed plugin
        how = dict(hide_lex_fil=True,  # If option has not setting for lexer/cur.file
                   stor_json=JSONFILE)
        try:  # New op_ed allows to skip meta-file
            op_ed_dlg = op_ed.OptEdD(
                path_keys_info=OPTS_META, subset=subset, how=how)
        except:
            # Old op_ed requires to use meta-file
            if not os.path.exists(METAJSONFILE) \
            or os.path.getmtime(METAJSONFILE) < os.path.getmtime(__file__):
                # Create/update meta-info file
                open(METAJSONFILE, 'w').write(json.dumps(OPTS_META, indent=4))
            op_ed_dlg = op_ed.OptEdD(
                path_keys_info=METAJSONFILE, subset=subset, how=how)
        if op_ed_dlg.show(_('Differ Options')):  # Dialog caption
            # Need to use updated options
            self.config()
            self.scroll.toggle(self.cfg['sync_scroll'])
            # self.scroll.enable_sync_caret = self.cfg['enable_sync_caret']

    def choose_files(self):
        files = self.diff_dlg.run()
        if files is None:
            return
        self.set_files(*files)

    def on_cli(self, fn1, fn2):
        self.set_files(fn1, fn2)

    def compare_with(self):
        fn0 = self.get_name(ct.ed)
        fn = ct.dlg_file(True, '!', '', '')
        if not fn:
            return
        self.set_files(fn0, fn)

    def compare_with_tab(self):
        name0 = self.get_name(ct.ed)
        names = []
        for h in ct.ed_handles():
            e = ct.Editor(h)
            if self.is_match_name(e, name0):
                continue
            names.append(self.get_name(e))
        if not names:
            return

        res = ct.dlg_menu(ct.DMENU_LIST, names, caption=_('Compare file with tab'))
        if res is None:
            return
        name = names[res]
        self.set_files(name0, name)

    def diff_with(self):
        fn0 = self.get_name(ct.ed)
        fn = ct.dlg_file(True, '!', '', '')
        if not fn:
            return

        enc = ct.ed.get_prop(ct.PROP_ENC)
        a = ct.ed.get_text_all()
        b = Path(fn).read_text(enc)
        self.create_diff(a, b, fn0, fn)

    def diff_with_tab(self):
        name0 = self.get_name(ct.ed)

        names = []
        ed = []
        for h in ct.ed_handles():
            e = ct.Editor(h)
            if self.is_match_name(e, name0):
                continue
            names.append(self.get_name(e))
            ed.append(h)
        if not names:
            return

        res = ct.dlg_menu(ct.DMENU_LIST, names, caption=_('Diff file with tab'))
        if res is None:
            return

        name = names[res]
        a = ct.ed.get_text_all()
        b = ct.Editor(ed[res]).get_text_all()

        self.create_diff(a, b, name0, name)

    def format_untitled(self, e):
        return U_PREFIX + e.get_prop(ct.PROP_TAB_TITLE) + ' [%d]'%e.get_prop(ct.PROP_TAB_ID)

    def is_match_name(self, e, name):
        if name.startswith(U_PREFIX):
            return name == self.format_untitled(e)
        fn = e.get_filename()
        if fn:
            return fn==name
        return False

    def set_files(self, file0, file1):
        files = [file0, file1]
        lexers = [None, None]
        for (index, name) in enumerate(files):
            for h in ct.ed_handles():
                e = ct.Editor(h)
                e_titled = e.get_filename()!=''
                if self.is_match_name(e, name):
                    lexers[index] = e.get_prop(ct.PROP_LEXER_FILE)
                    if not e_titled:
                        temp_text = e.get_text_all()
                        temp_fn = get_temp_name(e)
                        with open(temp_fn, 'w', encoding='utf8') as f:
                            f.write(temp_text)
                        files[index] = temp_fn
                    else:
                        if e.get_prop(ct.PROP_MODIFIED):
                            text = _('First you must save file:\n{}').format(name)
                            mb = ct.msg_box(text, ct.MB_OKCANCEL+ct.MB_ICONQUESTION)
                            if mb == ct.ID_OK:
                                if not e.save():
                                    return
                            else:
                                return

                        e.focus()
                        e.cmd(ct_cmd.cmd_FileClose)

                        ct.app_idle(True)  # better close file
                        sleep(0.3)
                        ct.app_idle(True)  # better close file
                    break

        ct.file_open(files, options='/nohistory')

        title = ct.ed.get_prop(ct.PROP_TAB_TITLE)
        title2 = prettify_pair_title(title)
        if title2:
            title = title2
        ct.ed.set_prop(ct.PROP_TAB_TITLE, title)

        self.diff_tabs.append(title)
        
        # set lexers
        a_ed = ct.Editor(ct.ed.get_prop(ct.PROP_HANDLE_PRIMARY))
        b_ed = ct.Editor(ct.ed.get_prop(ct.PROP_HANDLE_SECONDARY))
        if lexers[0] is not None:
            a_ed.set_prop(ct.PROP_LEXER_FILE, lexers[0])
        if lexers[1] is not None:
            b_ed.set_prop(ct.PROP_LEXER_FILE, lexers[1])

        # app sets LastLineOnTop automatically on adding 'gaps', but if file don't have gaps, we must set it manually
        a_ed.set_prop(ct.PROP_LAST_LINE_ON_TOP, True)
        b_ed.set_prop(ct.PROP_LAST_LINE_ON_TOP, True)

        # if file was in group-2, and now group-2 is empty, set "one group" mode
        if ct.app_proc(ct.PROC_GET_GROUPING, '') in [ct.GROUPS_2VERT, ct.GROUPS_2HORZ]:
            e = ct.ed_group(1)  # Editor obj in group-2
            if not e:
                ct.app_proc(ct.PROC_SET_GROUPING, ct.GROUPS_ONE)

        self.refresh()

    def create_diff(self, txt0, txt1, fn0, fn1):
        if txt0[-1] != '\n': txt0 += '\n'
        if txt1[-1] != '\n': txt1 += '\n'
        a = txt0.splitlines(True)
        b = txt1.splitlines(True)
        r = self.diff.unidiff(a, b, fn0, fn1, self.cfg.get('diff_context'))

        global DIFF_TAB_COUNT
        tab = 'Diff ' + str(DIFF_TAB_COUNT)
        DIFF_TAB_COUNT += 1

        ct.file_open('')
        ct.ed.set_text_all(r)
        ct.ed.set_prop(ct.PROP_LEXER_FILE, 'Diff')
        ct.ed.set_prop(ct.PROP_RO, True)
        ct.ed.set_prop(ct.PROP_TAB_TITLE, tab)
        ct.ed.set_prop(ct.PROP_SAVE_HISTORY, False)

    def on_state(self, ed_self, state):
        if state == ct.APPSTATE_THEME_SYNTAX:
            self.get_config()
            self.refresh()

    def on_scroll(self, ed_self):
        if ed_self.get_prop(ct.PROP_TAB_TITLE, '') in self.diff_tabs:
            self.scroll.on_scroll(ed_self)

    def on_caret(self, ed_self):
        if self.cfg.get('enable_sync_caret', False):
            self.sync_caret()

    def on_change_slow(self, ed_self):
        if self.cfg.get('enable_auto_refresh', False):
            self.refresh()

    '''
    def on_tab_change(self, ed_self):
        self.config()
        self.scroll.toggle(self.cfg.get('sync_scroll'))
    '''

    def on_tab_menu(self, ed_self):
        self.tabmenu_init(ed_self)

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
            t = _('The file:\n{}\nis empty.').format(collapse_filename(a_file))
            ct.msg_box(t, ct.MB_OK)
            return

        if b_text_all == '':
            t = _('The file:\n{}\nis empty.').format(collapse_filename(b_file))
            ct.msg_box(t, ct.MB_OK)
            return

        if not a_text_all.endswith('\n'):
            a_text_all += '\n'
        if not b_text_all.endswith('\n'):
            b_text_all += '\n'

        if a_text_all == b_text_all:
            self.clear(a_ed)
            self.clear(b_ed)
            self.diff.diffmap = []
            t = _('The files are identical:\n{0}\n{1}').format(collapse_filename(a_file), collapse_filename(b_file))
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
        __, h = e.get_prop(ct.PROP_CELL_SIZE)
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

    @staticmethod
    def get_config():

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
            'enable_sync_caret':
                get_opt('enable_sync_caret', False),
            'enable_auto_refresh':
                get_opt('enable_auto_refresh', False),
            'diff_context':
                get_opt('diff_context', 3),
        }

        new_nkind(NKIND_DELETED, config.get('color_deleted'))
        new_nkind(NKIND_ADDED, config.get('color_added'))
        new_nkind(NKIND_CHANGED, config.get('color_changed'))

        return config

    def clear_history(self):
        file_history.clear()
        file_history.save()

    @property
    def focused(self):
        hndl_self = ct.ed.get_prop(ct.PROP_HANDLE_SELF)
        hndl_primary = ct.ed.get_prop(ct.PROP_HANDLE_PRIMARY)
        hndl_secondary = ct.ed.get_prop(ct.PROP_HANDLE_SECONDARY)
        eds = (ct.Editor(hndl_primary), ct.Editor(hndl_secondary))
        if hndl_self == hndl_primary:
            return 0, eds
        else:
            return 1, eds

    def jump(self, to_next=True):
        if not self.diff.diffmap:
            self.refresh()
        cnt = len(self.diff.diffmap)
        if cnt == 0:
            return ct.msg_status(_("No differences were found"))
        fc, eds = self.focused

        i = None
        if fc == 0:
            p = 0 if to_next else 1
        else:
            p = 2 if to_next else 3
        y = eds[fc].get_carets()[0][1]
        line_cnt = eds[fc].get_line_count()

        if to_next:
            for n, dif in enumerate(self.diff.diffmap):
                df_y = dif[p] if dif[p] <= line_cnt - 1 else line_cnt - 1
                if y < df_y:
                    i = n
                    break
        else: # to prev
            for n, dif in reversed(list(enumerate(self.diff.diffmap))):
                _y = y if dif[p] == dif[p-1] else y + 1 # adjust y for empty diff fragments
                if _y > dif[p]:
                    i = n
                    break

        if i is None:
            i = 0 if to_next else cnt - 1
        elif i >= cnt:
            i = 0
        elif i < 0:
            i = cnt - 1
        to = self.diff.diffmap[i]
        ct.msg_status(_("{} of {} difference").format(i+1, cnt))
        a_line_cnt = eds[0].get_line_count()
        b_line_cnt = eds[1].get_line_count()
        to0 = to[0] if to[0] <= a_line_cnt - 1 else a_line_cnt - 1
        to2 = to[2] if to[2] <= b_line_cnt - 1 else b_line_cnt - 1
        eds[0].set_caret(0, to0, id=ct.CARET_SET_ONE)
        eds[1].set_caret(0, to2, id=ct.CARET_SET_ONE)

    def jump_next(self):
        self.jump()

    def jump_prev(self):
        self.jump(False)

    @property
    def get_current_change(self):
        if not self.diff.diffmap:
            self.refresh()
        fc, eds = self.focused
        p = fc * 2
        y = eds[fc].get_carets()[0][1]
        for dif in self.diff.diffmap:
            if dif[p] <= y < dif[p+1]:
                return dif

    def select_current(self):
        cur_change = self.get_current_change
        if not cur_change:
            return
        esc = self.cfg.get('enable_sync_caret', False)
        fc, eds = self.focused
        self.cfg['enable_sync_caret'] = False
        eds[0].set_caret(0, cur_change[0], 0, cur_change[1])
        eds[1].set_caret(0, cur_change[2], 0, cur_change[3])
        self.cfg['enable_sync_caret'] = esc

    def copy(self, to_right=True):
        fc, eds = self.focused
        current = self.get_current_change
        if not current:
            return
        else:
            a0, a1, b0, b1 = current
        if to_right:
            text = eds[0].get_text_substr(0, a0, 0, a1)
            eds[1].delete(0, b0, 0, b1)
            if text:
                eds[1].insert(0, b0, text)
        else:
            text = eds[1].get_text_substr(0, b0, 0, b1)
            eds[0].delete(0, a0, 0, a1)
            if text:
                eds[0].insert(0, a0, text)
        eds[0].set_caret(0, a0)
        eds[1].set_caret(0, b0)
        self.refresh()

    def copy_right(self):
        self.copy(True)

    def copy_left(self):
        self.copy(False)

    def copy_line(self, to_right=True):
        fc, eds = self.focused
        current = self.get_current_change

        def get_lines(ed: ct.Editor):
            carets = ed.get_carets()
            if len(carets) != 1:
                return []
            caret = carets[0]
            __, y1, __, y2 = caret
            if y2 == -1:
                return ed.get_text_line(y1) + '\n'
            else:
                return ''.join([ed.get_text_line(y)+'\n' for y in range(y1, y2)])

        if not current:
            return
        else:
            a0, a1, b0, b1 = current
        if to_right:
            if fc == 1:
                return
            text = get_lines(eds[0])
            print(text)
            if text:
                eds[1].insert(0, b0, text)
        else:
            if fc == 0:
                return
            text = get_lines(eds[1])
            if text:
                eds[0].insert(0, a0, text)
        self.refresh()

    def copy_line_right(self):
        self.copy_line(True)

    def copy_line_left(self):
        self.copy_line(False)

    @staticmethod
    def set_focus_to_opposite_panel():
        ct.ed.cmd(ct_cmd.cmd_ToggleFocusSplitEditors)

    def sync_caret(self):
        if not self.diff.diffmap:
            return
        fc, eds = self.focused
        op = 0 if fc else 1
        x, y = eds[fc].get_carets()[0][:2]

        esc = self.cfg.get('enable_sync_caret', False)
        p = fc * 2
        for dif in self.diff.diffmap:
            if dif[p] <= y < dif[p+1]:
                self.cfg['enable_sync_caret'] = False
                eds[op].set_caret(0, dif[op*2])
                self.cfg['enable_sync_caret'] = esc
                return
        for dif in self.diff.diffmap:
            if y < dif[p]:
                self.cfg['enable_sync_caret'] = False
                eds[op].set_caret(x, dif[op*2]-dif[p]+y)
                self.cfg['enable_sync_caret'] = esc
                return

    def get_name(self, e):
        fn = e.get_filename()
        if fn:
            return fn
        else:
            return self.format_untitled(e)

    def tabmenu_editor_ok(self, e, disabled_fn):
        if not e.get_prop(ct.PROP_EDITORS_LINKED):
            return False
        if e.get_prop(ct.PROP_KIND) != 'text':
            return False
        fn = self.get_name(e)
        if bool(disabled_fn) and (fn==disabled_fn):
            return False
        return True

    def tabmenu_init(self, cur_ed: ct.Editor):
        cur_fn = self.get_name(cur_ed)
        path_focused = self.get_name(ct.ed)

        if self.menuid_sep is None:
            self.menuid_sep = ct.menu_proc('tab', ct.MENU_ADD,
                caption='-'
                )
            self.compare_menu = ct.menu_proc('tab', ct.MENU_ADD,
                caption=PLG_NAME
                )

        ct.menu_proc(self.compare_menu, ct.MENU_CLEAR)
        self.menuid_withfile = ct.menu_proc(self.compare_menu, ct.MENU_ADD,
            command='module=cuda_differ;cmd=tabmenu_chooser;',
            caption=_('Compare with...')
            )
        self.menuid_withfocused = ct.menu_proc(self.compare_menu, ct.MENU_ADD,
            command='module=cuda_differ;cmd=tabmenu_files;info='+cur_fn+'::'+path_focused+';',
            caption=_('Compare with focused tab')
            )
        self.menuid_withtab = ct.menu_proc(self.compare_menu, ct.MENU_ADD,
            caption=_('Compare with tab')
            )
        self.menuid_sep = ct.menu_proc(self.compare_menu, ct.MENU_ADD,
            caption='-'
            )
        self.menuid_move2septabs = ct.menu_proc(self.compare_menu, ct.MENU_ADD,
            command='module=cuda_differ;cmd=move_to_sep_tabs_context;',
            caption=_('Back to separate tabs')
            )

        handles = ct.ed_handles()[:30] # avoid too much menu items when user opens 100 files

        paths = []
        if len(handles) > 1:
            for h in handles:
                e = ct.Editor(h)
                if self.tabmenu_editor_ok(e, cur_fn):
                    path = self.get_name(e)
                    paths.append(path)

            if paths:
                ct.menu_proc(self.menuid_withtab, ct.MENU_CLEAR)

                for path in paths:
                    ct.menu_proc(self.menuid_withtab, ct.MENU_ADD,
                        command='module=cuda_differ;cmd=tabmenu_files;info='+cur_fn+'::'+path+';',
                        caption=collapse_filename(path)
                        )

        cur_ok = self.tabmenu_editor_ok(cur_ed, '')
        cur_is_focused = cur_ed.get_prop(ct.PROP_HANDLE_PRIMARY) == \
                         ct.ed.get_prop(ct.PROP_HANDLE_PRIMARY)

        ct.menu_proc(self.menuid_withtab, ct.MENU_SET_ENABLED, command=cur_ok and bool(paths))
        ct.menu_proc(self.menuid_withfile, ct.MENU_SET_ENABLED, command=cur_ok)
        ct.menu_proc(self.menuid_withfocused, ct.MENU_SET_ENABLED, command=cur_ok and not cur_is_focused)
        ct.menu_proc(self.menuid_move2septabs, ct.MENU_SET_ENABLED, command=cur_ed.get_prop(ct.PROP_EDITORS_LINKED)==False)

    def tabmenu_chooser(self):
        callback = 'module=cuda_differ;cmd=tabmenu_chooser_timer;info=_;'
        ct.timer_proc(ct.TIMER_START_ONE, callback, 100)

    def tabmenu_chooser_timer(self, tag='', info=''):
        self.compare_with()

    def tabmenu_files(self, info):
        callback = 'module=cuda_differ;cmd=tabmenu_files_timer;info='+info+';'
        #print('tabmenu_files:', info)
        ct.timer_proc(ct.TIMER_START_ONE, callback, 100)

    def tabmenu_files_timer(self, tag='', info=''):
        fn0, fn1 = info.split('::', maxsplit=1)
        self.set_files(fn0, fn1)

    def select_all_diff(self):
        if not self.diff.diffmap:
            self.refresh()
        if len(self.diff.diffmap) == 0:
            return ct.msg_status(_("No differences were found"))
        fc, eds = self.focused
        y1,y2 = (0,1) if fc == 0 else (2,3)

        for n, dif in enumerate(self.diff.diffmap):
            id = ct.CARET_SET_ONE if n == 0 else ct.CARET_ADD
            eds[fc].set_caret(0, dif[y1], 0, dif[y2], id=id)

    def move_to_sep_tabs(self):
        self.move_to_sep_tabs_ex(ct.ed)

    def move_to_sep_tabs_context(self):
        if ct.app_api_version()>='1.0.435':
            e = ct.Editor(1)
        else:
            e = ct.ed
        self.move_to_sep_tabs_ex(e)

    def move_to_sep_tabs_ex(self, e: ct.Editor):

        if e.get_prop(ct.PROP_EDITORS_LINKED):
            return
        e1 = ct.Editor(e.get_prop(ct.PROP_HANDLE_PRIMARY))
        e2 = ct.Editor(e.get_prop(ct.PROP_HANDLE_SECONDARY))

        fn1 = e1.get_filename()
        fn2 = e2.get_filename()

        e1.focus() # otherwise cmd_FileClose will be applied to wrong editor
        e1.cmd(ct_cmd.cmd_FileClose)
        
        self.reopen_sep_tabs((fn1, fn2))

    def reopen_sep_tabs(self, filenames):

        '''
        def short_title(s):
            s = os.path.basename(s)
            n = s.find(TIMESTAMP_BEGIN)
            if n>0 and s.endswith(TIMESTAMP_END):
                s = s[:n]
                return s
            return '' # '' means to remove custom title
        '''

        for fn in filenames:
            if TIMESTAMP_BEGIN in fn and fn.endswith(TIMESTAMP_END):
                # don't reopen file from 'differ_backup'
                pass
            else:
                ct.file_open(fn, options='/nohistory')

    def on_close_pre(self, ed_self: ct.Editor):

        title = ed_self.get_prop(ct.PROP_TAB_TITLE, '')
        if title in self.diff_tabs:
            self.diff_tabs.remove(title)

            # avoid 'combined' tab title 'name1 | name2' saved to 'history files.json'
            ed_self.set_prop(ct.PROP_TAB_TITLE, '')

    def move_to_sep_tabs_timer(self, tag='', info=''):

        e = ct.Editor(int(info))
        self.move_to_sep_tabs_ex(e)

    def on_exit(self, ed_self):

        opt = ctx.get_opt('ui_one_instance', True)
        if opt:
            if os.path.isdir(TEMP_DIR):
                delete_all_files_in_folder(TEMP_DIR)
