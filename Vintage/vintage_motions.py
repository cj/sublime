import sublime, sublime_plugin
from vintage import transform_selection

class ViMoveByCharactersInLine(sublime_plugin.TextCommand):
    def run(self, edit, forward = True, extend = False, visual = False):
        delta = 1 if forward else -1

        transform_selection(self.view, lambda pt: pt + delta, extend=extend,
            clip_to_line=(not visual))

class ViMoveByCharacters(sublime_plugin.TextCommand):
    def advance(self, delta, visual, pt):
        pt += delta
        if not visual and self.view.substr(pt) == '\n':
            pt += delta

        return pt

    def run(self, edit, forward = True, extend = False, visual = False):
        delta = 1 if forward else -1
        transform_selection(self.view, lambda pt: self.advance(delta, visual, pt),
            extend=extend)

class ViMoveToHardEol(sublime_plugin.TextCommand):
    def run(self, edit, repeat = 1, extend = False):
        repeat = int(repeat)
        if repeat > 1:
            for i in xrange(repeat - 1):
                self.view.run_command('move',
                    {'by': 'lines', 'extend': extend, 'forward': True})

        transform_selection(self.view, lambda pt: self.view.line(pt).b,
            extend=extend, clip_to_line=False)

class ViMoveToFirstNonWhiteSpaceCharacter(sublime_plugin.TextCommand):
    def first_character(self, pt):
        l = self.view.line(pt)
        lstr = self.view.substr(l)

        offset = 0
        for c in lstr:
            if c == ' ' or c == '\t':
                offset += 1
            else:
                break

        return l.a + offset

    def run(self, edit, extend = False):
        transform_selection(self.view, lambda pt: self.first_character(pt),
            extend=extend)


g_last_move_command = None

class ViMoveToCharacter(sublime_plugin.TextCommand):
    def find_next(self, forward, char, before, pt):
        lr = self.view.line(pt)

        extra = 0 if before else 1

        if forward:
            line = self.view.substr(sublime.Region(pt, lr.b))
            idx = line.find(char, 1)
            if idx >= 0:
                return pt + idx + 1 * extra
        else:
            line = self.view.substr(sublime.Region(lr.a, pt))[::-1]
            idx = line.find(char, 0)
            if idx >= 0:
                return pt - idx - 1 * extra

        return pt

    def run(self, edit, character, extend = False, forward = True, before = False, record = True):
        if record:
            global g_last_move_command
            g_last_move_command = {'character': character, 'extend': extend,
                'forward':forward, 'before':before}

        transform_selection(self.view,
            lambda pt: self.find_next(forward, character, before, pt),
            extend=extend)

# Helper class used to implement ';'' and ',', which repeat the last f, F, t
# or T command (reversed in the case of ',')
class SetRepeatMoveToCharacterMotion(sublime_plugin.TextCommand):
    def run_(self, args):
        if args:
            return self.run(**args)
        else:
            return self.run()

    def run(self, reverse = False):
        if g_last_move_command:
            cmd = g_last_move_command.copy()
            cmd['record'] = False
            if reverse:
                cmd['forward'] = not cmd['forward']

            self.view.run_command('set_motion', {
                'motion': 'vi_move_to_character',
                'motion_args': cmd,
                'inclusive': True })

class ViMoveToBrackets(sublime_plugin.TextCommand):
    def move_by_percent(self, percent):
        destination = int(self.view.size() * (percent / 100.0))
        transform_selection(self.view, lambda pt: destination)

    def run(self, edit, repeat=1):
        repeat = int(repeat)
        if repeat == 1:
            bracket_chars = ")]}"
            def adj(pt):
                if (self.view.substr(pt) in bracket_chars):
                    return pt + 1
                else:
                    return pt
            transform_selection(self.view, adj)
            self.view.run_command("move_to", {"to": "brackets", "extend": True, "force_outer": True})
        else:
            self.move_by_percent(repeat)

class ViGotoLine(sublime_plugin.TextCommand):
    def run(self, edit, repeat = 1, extend = False):
        repeat = int(repeat)
        if repeat == 1:
            self.view.run_command('move_to', {'to': 'eof', 'extend':extend})
        else:
            target_pt = self.view.text_point(repeat - 1, 0)
            transform_selection(self.view, lambda pt: target_pt,
                extend=extend)

class MoveCaretToScreenCenter(sublime_plugin.TextCommand):
    def run(self, edit, extend = True):
        screenful = self.view.visible_region()
        middle = (screenful.begin() + screenful.end()) / 2

        transform_selection(self.view, lambda pt: middle, extend=extend)

class MoveCaretToScreenTop(sublime_plugin.TextCommand):
    def run(self, edit, extend = True):
        screenful = self.view.visible_region()
        transform_selection(self.view, lambda pt: screenful.begin(), extend=extend)

class MoveCaretToScreenBottom(sublime_plugin.TextCommand):
    def run(self, edit, extend = True):
        screenful = self.view.visible_region()
        transform_selection(self.view, lambda pt: screenful.end(), extend=extend)
