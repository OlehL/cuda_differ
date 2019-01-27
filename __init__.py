import os
from configparser import ConfigParser
import json
import cudatext as ct
from .differ import Differ
from .scroll import Scroll2Tab
from .ui import DifferDialog


DIFF_TAG = 148
GAP_WIDTH = 5000
INIFILE = os.path.join(ct.app_path(ct.APP_DIR_SETTINGS), 'cuda_differ.ini')
COLOR_CHANGED_LINE = 0x003030
COLOR_DETAIL_ADD = 0x124200
COLOR_DETAIL_DEL = 0x07003D


def html_color_to_int(s):
    """ Convert HTML color '#RRGGBB' or '#RGB' to int """
    s = s.strip().lstrip('#')
    slen = len(s)
    if slen == 3:
        return int(s[0]*2 + s[1]*2 + s[2]*2, 16)
    elif slen == 6:
        return int(s[4:6] + s[2:4] + s[0:2], 16)
    else:
        raise Exception('Incorrect color token: '+s)


def settings():
    global COLOR_CHANGED_LINE
    global COLOR_DETAIL_ADD
    global COLOR_DETAIL_DEL
    ini = ConfigParser()
    if os.path.isfile(INIFILE):
        ini.read(INIFILE, 'utf8')
        COLOR_CHANGED_LINE = html_color_to_int(
            ini.get('colors', 'color_changed_line'))
        COLOR_DETAIL_ADD = html_color_to_int(
            ini.get('colors', 'color_detail_add'))
        COLOR_DETAIL_DEL = html_color_to_int(
            ini.get('colors', 'color_detail_del'))
    else:
        ini['colors'] = {'color_changed_line': '#505000',
                         'color_detail_add': '#004212',
                         'color_detail_del': '#3D0007'
                         }
        with open(INIFILE, 'w', encoding='utf8') as configfile:
            ini.write(configfile)


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
        self.diff = Differ()
        self.f1 = None
        self.f2 = None

    def change_settings(self):
        settings()
        ct.file_open(INIFILE)

    def run(self):
        uidiff = DifferDialog().run()
        if None not in uidiff:
            self.f1, self.f2 = uidiff
            self.scroll = Scroll2Tab(__name__)
            self.open_files(self.f1, self.f2)
            self.refresh()

            # warning! next functions can broke editors nandle.
            self.a_ed.set_prop(ct.PROP_INDEX_GROUP, 0)
            self.b_ed.set_prop(ct.PROP_INDEX_GROUP, 1)
            ct.file_open(self.f1, group=0)
            ct.file_open(self.f2, group=1)

    def open_files(self, f1, f2):
        if ct.app_proc(ct.PROC_GET_GROUPING, '') == ct.GROUPS_ONE:
            ct.app_proc(ct.PROC_SET_GROUPING, ct.GROUPS_2VERT)

        # group=0
        ct.file_open(f1, group=0)
        self.a_ed = self._ed(f1)
        a = self.a_ed.get_text_all().splitlines(True)

        # group=1
        ct.file_open(f2, group=1)
        self.b_ed = self._ed(f2)
        b = self.b_ed.get_text_all().splitlines(True)

        self.a_ed.set_prop(ct.PROP_WRAP, ct.WRAP_OFF)
        self.b_ed.set_prop(ct.PROP_WRAP, ct.WRAP_OFF)

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
        settings()
        self.clear()
        if not self.f1 or not self.f2:
            return

        if self.diff.a == self.diff.b:
            msg('The two files are identical.')
            return

        for d in self.diff.compare():
            # print(d)
            diff_id, x, y, nlen = d
            if diff_id == '-':
                msg('Delete line {} in file {}'.format(y, self.f1))
                self.set_attribute(self.a_ed, x, y, nlen, COLOR_CHANGED_LINE)
            elif diff_id == '+':
                msg('Insert line {} in file {}'.format(y, self.f2))
                self.set_attribute(self.b_ed, x, y, nlen, COLOR_CHANGED_LINE)
            elif diff_id == '*-':
                self.set_gap(self.a_ed, y, nlen)
            elif diff_id == '*+':
                self.set_gap(self.b_ed, y, nlen)
            elif '++' in diff_id:
                self.set_attribute(self.b_ed, x, y, nlen, COLOR_DETAIL_ADD)
            elif '--' in diff_id:
                self.set_attribute(self.a_ed, x, y, nlen, COLOR_DETAIL_DEL)

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
        # print('gap', e, row, n)
        _, h = e.get_prop(ct.PROP_CELL_SIZE)
        h_size = h * n - 2
        c = e.get_prop(ct.PROP_COLOR, ct.COLOR_ID_TextBg)
        id_bitmap, id_canvas = e.gap(ct.GAP_MAKE_BITMAP, GAP_WIDTH, h_size)
        ct.canvas_proc(id_canvas, ct.CANVAS_SET_BRUSH, color=c)
        ct.canvas_proc(id_canvas, ct.CANVAS_SET_ANTIALIAS,
                       style=ct.ANTIALIAS_ON)
        ct.canvas_proc(id_canvas, ct.CANVAS_RECT_FILL,
                       x=0, y=0, x2=GAP_WIDTH, y2=h_size)
        e.gap(ct.GAP_ADD,
              row-1,
              id_bitmap,
              tag=DIFF_TAG
              )

    def clear(self):
        for h in ct.ed_handles():
            e = ct.Editor(h)
            e.attr(ct.MARKERS_DELETE_BY_TAG, DIFF_TAG)
            e.gap(ct.GAP_DELETE_ALL, 0, 0)
