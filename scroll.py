import cudatext as ct
import cudatext_cmd as ct_cmd


def show_caret(e):
    e.cmd(ct_cmd.cCommand_GotoScreenTop)


class ScrollSplittedTab:
    keep_caret_visible = False

    def __init__(self, name):
        self.name = name
        self.tab_id = set()

    def toggle(self, on=True):
        act = ct.PROC_EVENTS_SUB if on and ct.ed.get_prop(ct.PROP_TAB_ID) in self.tab_id else ct.PROC_EVENTS_UNSUB
        ct.app_proc(act, self.name+';on_scroll;;')

    def on_scroll(self, ed_self):
        if ed_self.get_prop(ct.PROP_SPLIT)[0] == '-':
            return

        pos_v = ed_self.get_prop(ct.PROP_SCROLL_VERT_INFO)['smooth_pos']
        pos_h = ed_self.get_prop(ct.PROP_SCROLL_HORZ_INFO)['smooth_pos']

        hndl_self = ed_self.get_prop(ct.PROP_HANDLE_SELF)
        hndl_primary = ed_self.get_prop(ct.PROP_HANDLE_PRIMARY)
        hndl_secondary = ed_self.get_prop(ct.PROP_HANDLE_SECONDARY)
        if hndl_self == hndl_primary:
            hndl_opposit = hndl_secondary
        else:
            hndl_opposit = hndl_primary
        e = ct.Editor(hndl_opposit)

        e.set_prop(ct.PROP_SCROLL_VERT_INFO, {'smooth_pos': pos_v})
        e.set_prop(ct.PROP_SCROLL_HORZ_INFO, {'smooth_pos': pos_h})

        e.cmd(ct_cmd.cmd_RepaintEditor)
