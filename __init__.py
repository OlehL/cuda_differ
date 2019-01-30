import os
import json
import cudatext as ct
from .differ import Differ
from .scroll import Scroll2Tab
from .ui import DifferDialog


DIFF_TAG = 148
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
        self.files = [None, None]

    def change_config(self):
        self.config()
        ct.file_open(INIFILE)

    def run(self):
        self.files = DifferDialog().run()  # return (f1, f2)
        if None not in self.files:
            self.scroll = Scroll2Tab(__name__)
            self.open_files(*self.files)
            self.refresh()

            # warning! next functions can broke editors nandle.
            self.a_ed.set_prop(ct.PROP_INDEX_GROUP, 0)
            self.b_ed.set_prop(ct.PROP_INDEX_GROUP, 1)
            ct.file_open(self.files[0], group=0)
            ct.file_open(self.files[1], group=1)

    def open_files(self, f1, f2):
        if ct.app_proc(ct.PROC_GET_GROUPING, '') == ct.GROUPS_ONE:
            ct.app_proc(ct.PROC_SET_GROUPING, ct.GROUPS_2VERT)

        ct.file_open(f1, group=0)
        self.a_ed = self._ed(f1)
        self.a_ed.set_prop(ct.PROP_WRAP, ct.WRAP_OFF)
        a = self.a_ed.get_text_all().splitlines(True)

        ct.file_open(f2, group=1)
        self.b_ed = self._ed(f2)
        self.b_ed.set_prop(ct.PROP_WRAP, ct.WRAP_OFF)
        b = self.b_ed.get_text_all().splitlines(True)

        self.diff.set_seqs(a, b)

        a_tab_id = self.a_ed.get_prop(ct.PROP_TAB_ID)
        b_tab_id = self.b_ed.get_prop(ct.PROP_TAB_ID)
        self.scroll.tab_ids = [a_tab_id, b_tab_id]
        self.scroll.toggle()

    def on_scroll(self, ed_self):
        self.scroll.on_scroll(ed_self)

    def on_state(self, ed_self, state):
        self.scroll.on_state(ed_self, state)

    def on_tab_change(self, ed_self):
        self.scroll.on_tab_change(ed_self)

    def refresh(self):
        self.config()
        self.clear()
        if None in self.files:
            return

        if self.diff.a == self.diff.b:
            ct.msg_box('The two files are identical.', ct.MB_OK)
            return

        for d in self.diff.compare():
            diff_id, x, y, nlen = d
            if diff_id == '-':
                # msg('Delete line {} in file {}'.format(y, self.files[0]))
                self.set_attribute(self.a_ed, x, y, nlen, self.color_changed)
                self.set_decor(self.a_ed, y, '■', self.color_changed)
            elif diff_id == '+':
                # msg('Insert line {} in file {}'.format(y, self.files[1]))
                self.set_attribute(self.b_ed, x, y, nlen, self.color_changed)
                self.set_decor(self.b_ed, y, '■', self.color_changed)
            elif diff_id == '*-':
                self.set_gap(self.a_ed, y, nlen)
            elif diff_id == '*+':
                self.set_gap(self.b_ed, y, nlen)
            elif '++' in diff_id:
                self.set_attribute(self.b_ed, x, y, nlen, self.color_added)
                self.set_decor(self.b_ed, y, '■', self.color_added)
            elif '--' in diff_id:
                self.set_attribute(self.a_ed, x, y, nlen, self.color_deleted)
                self.set_decor(self.a_ed, y, '■', self.color_deleted)

    def _ed(self, f):
        "return editor object for f"
        for h in ct.ed_handles():
            e = ct.Editor(h)
            if f.lower() == e.get_filename().lower():
                return e

    def set_attribute(self, e, x, y, nlen, bg):
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

    def clear(self):
        for h in ct.ed_handles():
            e = ct.Editor(h)
            e.attr(ct.MARKERS_DELETE_BY_TAG, DIFF_TAG)
            e.gap(ct.GAP_DELETE_ALL, 0, 0)
            e.decor(ct.DECOR_DELETE_BY_TAG, tag=DIFF_TAG)

    def config(self):
        if not os.path.exists(INIFILE):
            ct.ini_write(INIFILE, 'colors', 'changed', '')
            ct.ini_write(INIFILE, 'colors', 'added', '')
            ct.ini_write(INIFILE, 'colors', 'deleted', '')
        self.color_changed = get_color('LightBG2', 'changed', 0x003030)
        self.color_added = get_color('LightBG3', 'added', 0x124200)
        self.color_deleted = get_color('LightBG1', 'deleted', 0x07003D)
        self.color_gaps = ct.ed.get_prop(ct.PROP_COLOR, ct.COLOR_ID_TextBg)
