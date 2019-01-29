import os
import cudatext as ct


def center_ct():
    """get coordinates (x, y) of center CudaText"""
    xy = ct.app_proc(ct.PROC_COORD_WINDOW_GET, "")
    x = int((xy[2]-xy[0])/2+xy[0])
    y = int((xy[3]-xy[1])/2+xy[1])
    return (x, y)


class DifferDialog:
    def __init__(self):
        self._f1 = None
        self._f2 = None
        self.files = []
        for h in ct.ed_handles():
            e = ct.Editor(h)
            f = e.get_filename().lower()
            if os.path.isfile(f):
                self.files.append(f)

    def run(self):
        dlg = self.dialog()
        ct.dlg_proc(dlg, ct.DLG_SHOW_MODAL)
        ct.dlg_proc(dlg, ct.DLG_FREE)
        return (self._f1, self._f2)

    def dialog(self):
        items = "\t".join(self.files)

        self.h = ct.dlg_proc(0, ct.DLG_CREATE)
        ct.dlg_proc(self.h, ct.DLG_PROP_SET,
                    prop={'cap': 'Differ: Choose files...',
                          'x': center_ct()[0]-272,
                          'y': center_ct()[1]-100,
                          'w': 545,
                          'h': 145,
                          'resize': False,
                          'w_min': 100,
                          'h_min': 100,
                          'topmost': True
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
                          'val': '',
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
                          'val': '',
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
            self._f1, self._f2 = f1, f2
            ct.dlg_proc(id_dlg, ct.DLG_HIDE)
            return (f1, f2)

    def press_exit(self, id_dlg, id_ctl, data='', info=''):
        ct.dlg_proc(id_dlg, ct.DLG_HIDE)

    def files(self):
        if self._f1 and self._f2:
            return (self._f1, self._f2)
        else:
            return None
