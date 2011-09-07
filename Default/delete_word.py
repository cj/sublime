import sublime, sublime_plugin

def clamp(xmin, x, xmax):
    if x < xmin:
        return xmin
    if x > xmax:
        return xmax
    return x;

def classify(char, charsets):
    if len(char) == 0:
        return -2

    for i in xrange(0, len(charsets)):
        if char in charsets[i]:
            return i
    return -1

class DeleteWordCommand(sublime_plugin.TextCommand):

    def expand_word(self, view, pos, forward):
        if forward:
            delta = 1
            end_position = view.line(pos).b
        else:
            delta = -1
            end_position = view.line(pos).a

        txt = view.substr(sublime.Region(pos, end_position))
        if not forward:
            txt = txt[::-1]

        if len(txt) == 0:
            return sublime.Region(pos, pos + delta)

        classes = [" \t", view.settings().get("word_separators"), "\n"]

        count = 1

        cls = classify(txt[0], classes)

        did_eat_extra_space = False
        if cls == 0 and len(txt) > 1:
            next_cls = classify(txt[1], classes)
            if next_cls != 0:
                # First character is a space, and the following character is not.
                # Eat the space and the following word, not just the space
                cls = next_cls
                count += 1
                did_eat_extra_space = True

        for i in xrange(count, len(txt)):
            if classify(txt[i], classes) == cls:
                count += 1
            else:
                break

        return sublime.Region(pos, pos + delta * count)

    def run(self, edit, forward = True):
        new_sels = []
        for s in reversed(self.view.sel()):
            if s.empty():
                new_sels.append(self.expand_word(self.view, s.b, forward))

        sz = self.view.size()
        for s in new_sels:
            self.view.sel().add(sublime.Region(clamp(0, s.a, sz),
                clamp(0, s.b, sz)))

        self.view.run_command("add_to_kill_ring", {"forward": forward})

        if forward:
            self.view.run_command('right_delete')
        else:
            self.view.run_command('left_delete')
