import os
import json
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
INIFILE = os.path.join(ct.app_path(ct.APP_DIR_SETTINGS), 'cuda_differ.ini')


def msg(s, level=0):
    PLG_NAME = 'Differ'
    if level == 0:
        print(PLG_NAME + ':', s)
    elif level == 1:
        print(PLG_NAME + ' WARNING:', s)
    elif level == 2:
        print(PLG_NAME + ' ERROR:', s)


def get_color(color_id, key, default_color):
    color = default_color
    s = ct.ini_read(INIFILE, 'colors', key, '')
    f = s.find('#') == 0
    s = s.strip().lstrip('#')
    slen = len(s)
    if slen == 3 and f:
        color = int(s[0]*2 + s[1]*2 + s[2]*2, 16)
    elif slen == 6 and f:
        color = int(s[4:6] + s[2:4] + s[0:2], 16)
    else:
        for i in ct.app_proc(ct.PROC_THEME_SYNTAX_DATA_GET, ''):
            if i.get('name') == color_id:
                color = i.get('color_back', default_color)
                break
    return color


class Command:
    def __init__(self):
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
                               '\nYES-save and continue\n' + \
                               "NO-don't save (changes will be lost)"
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

        ct.file_open(files)
        a = ct.Editor(ct.ed.get_prop(ct.PROP_HANDLE_PRIMARY))
        b = ct.Editor(ct.ed.get_prop(ct.PROP_HANDLE_SECONDARY))
        a.set_prop(ct.PROP_WRAP, ct.WRAP_OFF)
        b.set_prop(ct.PROP_WRAP, ct.WRAP_OFF)

        self.refresh()

    def on_scroll(self, ed_self):
        self.scroll.on_scroll(ed_self)

    def on_tab_change(self, ed_self):
        self.config()
        self.scroll.toggle(self.enable_scroll)

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

        self.clear(a_ed)
        self.clear(b_ed)
        self.config()

        self.diff.set_seqs(a_text_all.splitlines(True),
                           b_text_all.splitlines(True))

        self.scroll.tab_id.add(ct.ed.get_prop(ct.PROP_TAB_ID))
        self.scroll.toggle(self.enable_scroll)

        for d in self.diff.compare():
            diff_id, y = d[0], d[1]
            if diff_id == '-':
                self.set_bookmark2(a_ed, y, NKIND_DELETED)
                self.set_decor(a_ed, y, '■', self.color_deleted)
            elif diff_id == '+':
                self.set_bookmark2(b_ed, y, NKIND_ADDED)
                self.set_decor(b_ed, y, '■', self.color_added)
            elif diff_id == '-*':
                self.set_bookmark2(a_ed, y, NKIND_CHANGED)
            elif diff_id == '+*':
                self.set_bookmark2(b_ed, y, NKIND_CHANGED)
            elif diff_id == '-^':
                self.set_gap(a_ed, y, d[2])
            elif diff_id == '+^':
                self.set_gap(b_ed, y, d[2])
            elif diff_id == '++':
                self.set_attr(b_ed, d[2], y, d[3], self.color_added)
            elif diff_id == '--':
                self.set_attr(a_ed, d[2], y, d[3], self.color_deleted)
            elif diff_id == '-y':
                self.set_decor(a_ed, y, '■', self.color_changed)
            elif diff_id == '+y':
                self.set_decor(b_ed, y, '■', self.color_changed)
            elif diff_id == '-r':
                self.set_decor(a_ed, y, '■', self.color_deleted)
            elif diff_id == '+g':
                self.set_decor(b_ed, y, '■', self.color_added)

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
        _, h = e.get_prop(ct.PROP_CELL_SIZE)
        h_size = h * n - 2
        id_bitmap, id_canvas = e.gap(ct.GAP_MAKE_BITMAP, GAP_WIDTH, h_size)
        ct.canvas_proc(id_canvas, ct.CANVAS_SET_BRUSH, color=self.color_gaps)
        ct.canvas_proc(id_canvas, ct.CANVAS_SET_ANTIALIAS,
                       style=ct.ANTIALIAS_ON)
        ct.canvas_proc(id_canvas, ct.CANVAS_RECT_FILL,
                       x=0, y=0, x2=GAP_WIDTH, y2=h_size)
        e.gap(ct.GAP_ADD,
              row-1,
              id_bitmap,
              tag=DIFF_TAG
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
        if not os.path.exists(INIFILE):
            ct.ini_write(INIFILE, 'colors', 'changed', '')
            ct.ini_write(INIFILE, 'colors', 'added', '')
            ct.ini_write(INIFILE, 'colors', 'deleted', '')
            ct.ini_write(INIFILE, 'config',
                         'enable_scroll_default', '1')
        self.color_changed = get_color('LightBG2', 'changed', 0x003030)
        self.color_added = get_color('LightBG3', 'added', 0x124200)
        self.color_deleted = get_color('LightBG1', 'deleted', 0x07003D)
        self.color_gaps = ct.ed.get_prop(ct.PROP_COLOR, ct.COLOR_ID_TextBg)

        on = ct.ini_read(INIFILE, 'config', 'enable_scroll_default', '1')
        self.enable_scroll = on=='1'

        def new_nkind(val, color):
            ct.ed.bookmark(ct.BOOKMARK_SETUP, 0,
                           nkind=val,
                           ncolor=color,
                           text=''
                           )

        new_nkind(NKIND_DELETED, self.color_deleted)
        new_nkind(NKIND_ADDED, self.color_added)
        new_nkind(NKIND_CHANGED, self.color_changed)
