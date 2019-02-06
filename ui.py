import os
import cudatext as ct


HISTORY_SIZE = 24


def center_ct():
    """get coordinates (x, y) of center CudaText"""
    x1, y1, x2, y2 = ct.app_proc(ct.PROC_COORD_WINDOW_GET, "")
    x = (x1+x2)//2
    y = (y1+y2)//2
    return (x, y)


class DifferDialog:
    def __init__(self):
        self.f1 = None
        self.f2 = None
        self.history_opened = []

    def run(self):
        self.ready = False
        open_files = set()
        for h in ct.ed_handles():
            e = ct.Editor(h)
            f = e.get_filename()
            if os.path.isfile(f):
                open_files.add(os.path.abspath(f))
        items = "\t".join({*open_files, *self.history_opened})

        f1 = ct.ed.get_filename()
        self.f1 = f1 if os.path.exists(f1) else None

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
                          'p': 'g1'
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
        # print(ct.dlg_proc(self.h, ct.DLG_CTL_PROP_GET, name='ok'))
        # print(ct.dlg_proc(self.h, ct.DLG_CTL_PROP_GET, name='cancel'))
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
            if self.f1 not in self.history_opened:
                self.history_opened.append(self.f1)
            if self.f2 not in self.history_opened:
                self.history_opened.append(self.f2)
            if len(self.history_opened) > HISTORY_SIZE:
                self.history_opened = self.history_opened[-HISTORY_SIZE:]
            ct.dlg_proc(id_dlg, ct.DLG_HIDE)

    def press_exit(self, id_dlg, id_ctl, data='', info=''):
        ct.dlg_proc(id_dlg, ct.DLG_HIDE)

    def press_enter(self, id_dlg, id_ctl, data='', info=''):
        if id_ctl != 13:  # enter = 13
            return
        if data != '':
            return
        self.press_ok(id_dlg, id_ctl, data='', info='')
