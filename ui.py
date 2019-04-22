import os
import cudatext as ct


class FileHistory:
    items = []
    max_size = 50
    section = 'recents'

    def __init__(self):

        self.filename = os.path.join(ct.app_path(ct.APP_DIR_SETTINGS), 'cuda_differ_history.ini')

    def load(self):

        self.items = []
        for i in range(self.max_size):
            fn = ct.ini_read(self.filename, self.section, str(i), '')
            if not fn: break
            self.items.append(fn)

    def save(self):

        ct.ini_proc(ct.INI_DELETE_SECTION, self.filename, self.section, '')
        for (i, item) in enumerate(self.items):
            ct.ini_write(self.filename, self.section, str(i), item)

    def add(self, item):

        if not item: return
        if item in self.items:
            self.items.remove(item)
        self.items.insert(0, item)

        if len(self.items) > self.max_size:
            self.items = self.items[:self.max_size]

    def clear(self):
    
        self.items = []


file_history = FileHistory()
file_history.load()


def center_ct():
    """get coordinates (x, y) of center CudaText"""
    x1, y1, x2, y2 = ct.app_proc(ct.PROC_COORD_WINDOW_GET, "")
    x = (x1+x2)//2
    y = (y1+y2)//2
    return (x, y)


class DifferDialog:
    def __init__(self):
        self.f1 = ''
        self.f2 = ''

    def run(self):
        global file_history
        self.ready = False
        open_files = []

        for h in ct.ed_handles():
            f = ct.Editor(h).get_filename()
            if os.path.isfile(f):
                open_files.append(f)

        items = "\t".join(open_files+file_history.items)

        self.f1 = ct.ed.get_filename()
        self.f2 = ''

        if ct.app_proc(ct.PROC_GET_GROUPING, '') == ct.GROUPS_ONE:

            # if 2 files opened in group-1, suggest these 2 files
            hh = ct.ed_handles()
            if len(hh)==2:
                name1 = ct.Editor(hh[0]).get_filename()
                name2 = ct.Editor(hh[1]).get_filename()
                if name1 and name2:
                    self.f1 = name1
                    self.f2 = name2

        else:
            e1 = ct.ed_group(0)
            e2 = ct.ed_group(1)
            if e1 and e2:
                self.f1 = e1.get_filename()
                self.f2 = e2.get_filename()

        dlg = self.dialog(items)
        ct.dlg_proc(dlg, ct.DLG_SHOW_MODAL)
        ct.dlg_proc(dlg, ct.DLG_FREE)
        if self.ready:
            return (self.f1, self.f2)

    def dialog(self, items):

        self.h = ct.dlg_proc(0, ct.DLG_CREATE)
        ct.dlg_proc(self.h, ct.DLG_PROP_SET,
                    prop={'cap': 'Differ: Choose files...',
                          'x': center_ct()[0]-275,
                          'y': center_ct()[1]-90,
                          'w': 550,
                          'h': 180,
                          'resize': False,
                          "keypreview": True,
                          'on_key_down': self.press_enter
                          }
                    )

        g1 = ct.dlg_proc(self.h, ct.DLG_CTL_ADD, 'group')
        ct.dlg_proc(self.h, ct.DLG_CTL_PROP_SET, index=g1,
                    prop={
                          'name': 'g1',
                          'cap': 'First file:',
                          'h': 60,
                          'a_l': ('', '['),
                          'a_r': ('', ']'),
                          'a_t': ('', '['),
                          'sp_a': 5
                          }
                    )

        n = ct.dlg_proc(self.h, ct.DLG_CTL_ADD, 'button')
        ct.dlg_proc(self.h, ct.DLG_CTL_PROP_SET, index=n,
                    prop={
                          'name': 'browse_1',
                          'cap': 'Browse...',
                          'w': 80,
                          'a_l': None,
                          'a_t': ('', '['),
                          'a_r': ('', ']'),
                          'sp_a': 5,
                          'p': 'g1',
                          'tab_order': 1,
                          'on_change': self.open_1_file
                          }
                    )

        n = ct.dlg_proc(self.h, ct.DLG_CTL_ADD, 'combo')
        ct.dlg_proc(self.h, ct.DLG_CTL_PROP_SET, index=n,
                    prop={'name': 'f1_combo',
                          "items": items,
                          'val': self.f1,
                          'a_l': ('', '['),
                          'a_r': ('browse_1', '['),
                          'a_t': ('', '['),
                          'sp_a': 5,
                          'p': 'g1',
                          'tab_order': 0
                          }
                    )

        g1 = ct.dlg_proc(self.h, ct.DLG_CTL_ADD, 'group')
        ct.dlg_proc(self.h, ct.DLG_CTL_PROP_SET, index=g1,
                    prop={
                          'name': 'g2',
                          'cap': 'Second file:',
                          'h': 60,
                          'a_l': ('', '['),
                          'a_t': ('g1', ']'),
                          'a_r': ('', ']'),
                          'sp_a': 5
                          }
                    )

        n = ct.dlg_proc(self.h, ct.DLG_CTL_ADD, 'button')
        ct.dlg_proc(self.h, ct.DLG_CTL_PROP_SET, index=n,
                    prop={
                          'name': 'browse_2',
                          'cap': 'Browse...',
                          'w': 80,
                          'a_l': None,
                          'a_t': ('', '['),
                          'a_r': ('', ']'),
                          'sp_a': 5,
                          'p': 'g2',
                          'tab_order': 1,
                          'on_change': self.open_2_file
                          }
                    )

        n = ct.dlg_proc(self.h, ct.DLG_CTL_ADD, 'combo')
        ct.dlg_proc(self.h, ct.DLG_CTL_PROP_SET, index=n,
                    prop={'name': 'f2_combo',
                          "items": items,
                          'val': self.f2,
                          'a_l': ('', '['),
                          'a_r': ('browse_2', '['),
                          'a_t': ('', '['),
                          'sp_a': 5,
                          'p': 'g2',
                          'tab_order': 0,
                          }
                    )

        n = ct.dlg_proc(self.h, ct.DLG_CTL_ADD, 'button')
        ct.dlg_proc(self.h, ct.DLG_CTL_PROP_SET, index=n,
                    prop={
                          'name': 'cancel',
                          'cap': 'Cancel',
                          'w': 80,
                          'a_t': None,
                          'a_b': ('', ']'),
                          'a_l': None,
                          'a_r': ('g1', ']'),
                          'sp_a': 5,
                          'tab_order': 3,
                          'on_change': self.press_exit
                          }
                    )

        n = ct.dlg_proc(self.h, ct.DLG_CTL_ADD, 'button')
        ct.dlg_proc(self.h, ct.DLG_CTL_PROP_SET, index=n,
                    prop={
                          'name': 'ok',
                          'cap': 'OK',
                          'w': 80,
                          'a_t': None,
                          'a_b': ('', ']'),
                          'a_l': None,
                          'a_r': ('cancel', '['),
                          'sp_a': 5,
                          'tab_order': 2,
                          'on_change': self.press_ok
                          }
                    )
        #print(ct.dlg_proc(self.h, ct.DLG_CTL_PROP_GET, name='browse_1'))
        #print(ct.dlg_proc(self.h, ct.DLG_CTL_PROP_GET, name='f1_combo'))
        #print(ct.dlg_proc(self.h, ct.DLG_CTL_PROP_GET, name='browse_2'))
        #print(ct.dlg_proc(self.h, ct.DLG_CTL_PROP_GET, name='f2_combo'))

        return self.h

    def open_1_file(self, id_dlg, id_ctl, data='', info=''):
        f = ct.dlg_file(True, '', '', '')
        ct.dlg_proc(self.h, ct.DLG_CTL_PROP_SET,
                    name='f1_combo',
                    prop={'val': f}
                    )

    def open_2_file(self, id_dlg, id_ctl, data='', info=''):
        f = ct.dlg_file(True, '', '', '')
        ct.dlg_proc(self.h, ct.DLG_CTL_PROP_SET,
                    name='f2_combo',
                    prop={'val': f}
                    )

    def press_ok(self, id_dlg, id_ctl, data='', info=''):
        global file_history

        def set_cap(name, cap):
            ct.dlg_proc(self.h, ct.DLG_CTL_PROP_SET,
                        name=name,
                        prop={'cap': cap}
                        )

        f1_prop = ct.dlg_proc(self.h, ct.DLG_CTL_PROP_GET, name='f1_combo')
        f1 = f1_prop.get('val')
        if not os.path.isfile(f1):
            set_cap('g1', 'First file: (Please set correct path)')
        else:
            set_cap('g1', 'First file:')

        f2_prop = ct.dlg_proc(self.h, ct.DLG_CTL_PROP_GET, name='f2_combo')
        f2 = f2_prop.get('val')
        if not os.path.isfile(f2):
            set_cap('g2', 'Second file: (Please set correct path)')
        else:
            set_cap('g2', 'Second file:')

        if os.path.isfile(f1) and os.path.isfile(f2):
            self.ready = True
            self.f1, self.f2 = os.path.abspath(f1), os.path.abspath(f2)

            file_history.add(self.f1)
            file_history.add(self.f2)
            file_history.save()

            ct.dlg_proc(id_dlg, ct.DLG_HIDE)

    def press_exit(self, id_dlg, id_ctl, data='', info=''):
        ct.dlg_proc(id_dlg, ct.DLG_HIDE)

    def press_enter(self, id_dlg, id_ctl, data='', info=''):
        if id_ctl != 13:  # enter = 13
            return
        if data != '':
            return
        self.press_ok(id_dlg, id_ctl, data='', info='')
