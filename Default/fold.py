import sublime, sublime_plugin

class FoldCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        new_sel = []
        for s in self.view.sel():
            r = s
            empty_region = r.empty()
            if empty_region:
                r = sublime.Region(r.a - 1, r.a + 1)

            unfolded = self.view.unfold(r)
            if len(unfolded) == 0:
                self.view.fold(s)
            elif empty_region:
                for r in unfolded:
                    new_sel.append(r)

        if len(new_sel) > 0:
            self.view.sel().clear()
            for r in new_sel:
                self.view.sel().add(r)

class UnfoldAllCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.unfold(sublime.Region(0, self.view.size()))
