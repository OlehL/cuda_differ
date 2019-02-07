import cudatext as ct
import cudatext_cmd as ct_cmd


class ScrollSplittedTab:

    def __init__(self, name):
        self.name = name
        self.tab_id = set()

    def toggle(self, on=True):
        if on:
            ev = 'on_tab_change'
            if ct.ed.get_prop(ct.PROP_TAB_ID) in self.tab_id:
                ev = 'on_scroll,on_tab_change'
        else:
            ev = ''
        ct.app_proc(ct.PROC_SET_EVENTS, self.name+';'+ev+';;')

    def on_scroll(self, ed_self):
        if ed_self.get_prop(ct.PROP_SPLIT)[0] == '-':
            return
        pos_v = ed_self.get_prop(ct.PROP_SCROLL_VERT)
        pos_h = ed_self.get_prop(ct.PROP_SCROLL_HORZ)
        hndl_self = ed_self.get_prop(ct.PROP_HANDLE_SELF)
        hndl_primary = ed_self.get_prop(ct.PROP_HANDLE_PRIMARY)
        hndl_secondary = ed_self.get_prop(ct.PROP_HANDLE_SECONDARY)
        if hndl_self == hndl_primary:
            hndl_opposit = hndl_secondary
        else:
            hndl_opposit = hndl_primary
        e = ct.Editor(hndl_opposit)
        e.set_prop(ct.PROP_SCROLL_VERT, pos_v)
        e.set_prop(ct.PROP_SCROLL_HORZ, pos_h)
        e.cmd(ct_cmd.cmd_RepaintEditor)
