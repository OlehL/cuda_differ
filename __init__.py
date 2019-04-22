import os
import cudatext as ct
import cudatext_cmd as ct_cmd
from .differ import Differ
from .scroll import ScrollSplittedTab
from .ui import DifferDialog


DIFF_TAG = 148
NKIND_DELETED = 24
NKIND_ADDED = 25
NKIND_CHANGED = 26
GAP_WIDTH = 5000
DECOR_CHAR = '■'
INIFILE = os.path.join(ct.app_path(ct.APP_DIR_SETTINGS), 'cuda_differ.ini')
DEFAULT_SYNC_SCROLL = '1'


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
        self.config()
        ct.file_open(INIFILE)

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
        ini_time = os.path.getmtime(INIFILE)
        theme_name = ct.app_proc(ct.PROC_THEME_SYNTAX_GET, '')
        if self.cfg.get('ini_time') == ini_time \
                and self.cfg.get('theme_name') == theme_name:
            return
        self.cfg = self.get_config()

    def get_config(self):
        if not os.path.exists(INIFILE):
            ct.ini_write(INIFILE, 'colors', 'changed', '')
            ct.ini_write(INIFILE, 'colors', 'added', '')
            ct.ini_write(INIFILE, 'colors', 'deleted', '')
            ct.ini_write(INIFILE, 'colors', 'gap', '')
            ct.ini_write(INIFILE, 'config', 'enable_scroll_default', DEFAULT_SYNC_SCROLL),
            ct.ini_write(INIFILE, 'config', 'compare_with_details', '1'),
            ct.ini_write(INIFILE, 'config', 'ratio', '0.75')

        def get_color(key, default_color):
            s = ct.ini_read(INIFILE, 'colors', key, '')
            f = s.find('#') == 0
            s = s.strip().lstrip('#')
            slen = len(s)
            if slen == 3 and f:
                return int(s[2]*2 + s[1]*2 + s[0]*2, 16)
            elif slen == 6 and f:
                return int(s[4:6] + s[2:4] + s[0:2], 16)
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
        # on = ct.ini_read(INIFILE, 'config', 'enable_scroll_default', '1')
        config = {
            'ini_time': os.path.getmtime(INIFILE),
            'theme_name': ct.app_proc(ct.PROC_THEME_SYNTAX_GET, ''),
            'color_changed': get_color('changed', t.get('color_changed')),
            'color_added': get_color('added', t.get('color_added')),
            'color_deleted': get_color('deleted', t.get('color_deleted')),
            'color_gaps': get_color('gap', ct.COLOR_NONE),
            'enable_scroll': ct.ini_read(INIFILE, 'config', 'enable_scroll_default', DEFAULT_SYNC_SCROLL) == '1',
            'compare_with_details': ct.ini_read(INIFILE, 'config', 'compare_with_details', '1') == '1',
            'ratio': float(ct.ini_read(INIFILE, 'config', 'ratio', '0.75'))
        }

        new_nkind(NKIND_DELETED, config.get('color_deleted'))
        new_nkind(NKIND_ADDED, config.get('color_added'))
        new_nkind(NKIND_CHANGED, config.get('color_changed'))

        return config
