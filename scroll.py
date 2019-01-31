import cudatext as ct
import cudatext_cmd as ct_cmd


class Scroll2Tab:

    def __init__(self, name, tab_ids=[]):
        self.name = name
        self.tab_ids = tab_ids

    def toggle(self, on=True):
        ev = 'on_tab_change'
        grp = [ct.GROUPS_2HORZ, ct.GROUPS_2VERT]
        if on and ct.app_proc(ct.PROC_GET_GROUPING, '') in grp:
            if ct.ed.get_prop(ct.PROP_TAB_ID) in self.tab_ids:
                ev = 'on_scroll,on_state,on_tab_change'
        ct.app_proc(ct.PROC_SET_EVENTS, self.name+';'+ev+';;')

    def on_scroll(self, ed_self):
        pos_v = ed_self.get_prop(ct.PROP_SCROLL_VERT)
        pos_h = ed_self.get_prop(ct.PROP_SCROLL_HORZ)
        grp = ed_self.get_prop(ct.PROP_INDEX_GROUP)
        e = ct.ed_group(1 if grp == 0 else 0)
        if e is not None:
            e.set_prop(ct.PROP_SCROLL_VERT, pos_v)
            e.set_prop(ct.PROP_SCROLL_HORZ, pos_h)
            e.cmd(ct_cmd.cmd_RepaintEditor)

    def on_state(self, ed_self, state):
        if state == ct.APPSTATE_GROUPS:
            self.toggle()
        if state == ct.EDSTATE_TAB_TITLE:
            self.toggle()

    def on_tab_change(self, ed_self):
        self.toggle()
