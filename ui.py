import os
import cudatext as ct


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

        if ct.app_proc(ct.PROC_GET_GROUPING, '') is not ct.GROUPS_ONE:
            f1 = ct.ed_group(0).get_filename()
            f2 = ct.ed_group(1).get_filename()
            self.f1 = f1 if os.path.exists(f1) else None
            self.f2 = f2 if os.path.exists(f2) else None

        dlg = self.dialog(items)
        ct.dlg_proc(dlg, ct.DLG_SHOW_MODAL)
        ct.dlg_proc(dlg, ct.DLG_FREE)
        if self.ready:
            return (self.f1, self.f2)

    def dialog(self, items):

        self.h = ct.dlg_proc(0, ct.DLG_CREATE)
        ct.dlg_proc(self.h, ct.DLG_PROP_SET,
                    prop={'cap': 'Differ: Choose files...',
                          'x': center_ct()[0]-272,
                          'y': center_ct()[1]-100,
                          'w': 545,
                          'h': 145,
                          'resize': False,
                          }
                    )

        n = ct.dlg_proc(self.h, ct.DLG_CTL_ADD, 'label')
        ct.dlg_proc(self.h, ct.DLG_CTL_PROP_SET, index=n,
                    prop={'name': 'f1_label',
                          'cap': 'First file:',
                          'x': 8,
                          'y': 8,
                          'w': 200,
                          'tag': 'some_tag'
                          }
                    )

        n = ct.dlg_proc(self.h, ct.DLG_CTL_ADD, 'combo')
        ct.dlg_proc(self.h, ct.DLG_CTL_PROP_SET, index=n,
                    prop={'name': 'f1_combo',
                          "items": items,
                          'val': self.f1,
                          'x': 8,
                          'y': 24,
                          'w': 447
                          }
                    )

        n = ct.dlg_proc(self.h, ct.DLG_CTL_ADD, 'button')
        ct.dlg_proc(self.h, ct.DLG_CTL_PROP_SET, index=n,
                    prop={
                          'name': 'browse_1',
                          'cap': 'Browse...',
                          'x': 460,
                          'y': 24,
                          'w': 80,
                          'on_change': self.open_1_file
                          }
                    )

        n = ct.dlg_proc(self.h, ct.DLG_CTL_ADD, 'label')
        ct.dlg_proc(self.h, ct.DLG_CTL_PROP_SET, index=n,
                    prop={'name': 'f2_label',
                          'cap': 'Second file:',
                          'x': 8,
                          'y': 56,
                          'w': 200,
                          'tag': 'some_tag'
                          }
                    )

        n = ct.dlg_proc(self.h, ct.DLG_CTL_ADD, 'combo')
        ct.dlg_proc(self.h, ct.DLG_CTL_PROP_SET, index=n,
                    prop={'name': 'f2_combo',
                          "items": items,
                          'val': self.f2,
                          'x': 8,
                          'y': 72,
                          'w': 447
                          }
                    )

        n = ct.dlg_proc(self.h, ct.DLG_CTL_ADD, 'button')
        ct.dlg_proc(self.h, ct.DLG_CTL_PROP_SET, index=n,
                    prop={
                          'name': 'browse_2',
                          'cap': 'Browse...',
                          'x': 460,
                          'y': 72,
                          'w': 80,
                          'on_change': self.open_2_file
                          }
                    )

        n = ct.dlg_proc(self.h, ct.DLG_CTL_ADD, 'button')
        ct.dlg_proc(self.h, ct.DLG_CTL_PROP_SET, index=n,
                    prop={
                          'name': 'ok',
                          'cap': 'OK',
                          'x': 375,
                          'y': 118,
                          'w': 80,
                          'on_change': self.press_ok
                          }
                    )

        n = ct.dlg_proc(self.h, ct.DLG_CTL_ADD, 'button')
        ct.dlg_proc(self.h, ct.DLG_CTL_PROP_SET, index=n,
                    prop={
                          'name': 'cancel',
                          'cap': 'Cancel',
                          'x': 460,
                          'y': 118,
                          'w': 80,
                          'on_change': self.press_exit
                          }
                    )

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
            set_cap('f1_label', 'First file: (Place set correct path)')
        else:
            set_cap('f1_label', 'First file:')

        f2_prop = ct.dlg_proc(self.h, ct.DLG_CTL_PROP_GET, name='f2_combo')
        f2 = f2_prop.get('val')
        if not os.path.isfile(f2):
            set_cap('f2_label', 'Second file: (Place set correct path)')
        else:
            set_cap('f2_label', 'Second file:')

        if os.path.isfile(f1) and os.path.isfile(f2):
            self.ready = True
            self.f1, self.f2 = os.path.abspath(f1), os.path.abspath(f2)
            if self.f1 not in self.history_opened:
                self.history_opened.append(self.f1)
            if self.f2 not in self.history_opened:
                self.history_opened.append(self.f2)
            if len(self.history_opened) > 24:
                self.history_opened = self.history_opened[-24:]
            ct.dlg_proc(id_dlg, ct.DLG_HIDE)

    def press_exit(self, id_dlg, id_ctl, data='', info=''):
        ct.dlg_proc(id_dlg, ct.DLG_HIDE)
