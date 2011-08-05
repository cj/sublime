import sublime, sublime_plugin
from kill_ring import kill_ring

# Normal: Motions apply to all the characters they select
MOTION_MODE_NORMAL = 0
# Used in visual line mode: Motions are extended to BOL and EOL.
MOTION_MODE_LINE = 2
# Used by some actions, just as 'd'. If a motion crosses line boundaries,
# it'll be extended to BOL and EOL
MOTION_MODE_AUTO_LINE = 1


# Represents the current input state. The primary commands that interact with
# this are:
# * set_action
# * set_motion
# * push_repeat_digit

class InputState:
    prefix_repeat_digits = []
    action_command = None
    action_command_args = None
    action_description = None
    motion_repeat_digits = []
    motion_command = None
    motion_command_args = None
    motion_mode = MOTION_MODE_NORMAL
    motion_inclusive = False

g_input_state = InputState()

# Updates the status bar to reflect the current mode and input state
def update_status_line(view):
    cmd_mode = view.settings().get('command_mode')

    if cmd_mode and g_input_state.motion_mode == MOTION_MODE_LINE:
        view.set_status('mode', 'VISUAL LINE MODE')
    elif cmd_mode and view.has_non_empty_selection_region():
        view.set_status('mode', 'VISUAL MODE')
    elif cmd_mode:
        repeat = (digits_to_number(g_input_state.prefix_repeat_digits)
            * digits_to_number(g_input_state.motion_repeat_digits))
        if g_input_state.action_command != None or repeat != 1:
            desc = g_input_state.action_command
            if g_input_state.action_description:
                desc = g_input_state.action_description

            if repeat != 1 and desc:
                desc = desc + " * " + str(repeat)
            elif repeat != 1:
                desc = "* " + str(repeat)

            view.set_status('mode', 'COMMAND MODE - ' + desc)
        else:
            view.set_status('mode', 'COMMAND MODE')
    else:
        view.set_status('mode', 'INSERT MODE')

def set_motion_mode(view, mode):
    g_input_state.motion_mode = mode
    update_status_line(view)

def reset_input_state(view, reset_motion_mode = True):
    global g_input_state
    g_input_state.prefix_repeat_digits = []
    g_input_state.action_command = None
    g_input_state.action_command_args = None
    g_input_state.action_description = None
    g_input_state.motion_repeat_digits = []
    g_input_state.motion_command = None
    g_input_state.motion_command_args = None
    g_input_state.motion_inclusive = False
    if reset_motion_mode:
        set_motion_mode(view, MOTION_MODE_NORMAL)

def string_to_motion_mode(mode):
    if mode == 'normal':
        return MOTION_MODE_NORMAL
    elif mode == 'line':
        return MOTION_MODE_LINE
    elif mode == 'auto_line':
        return MOTION_MODE_AUTO_LINE
    else:
        return -1

# Called when the plugin is unloaded (e.g., perhaps it just got added to
# ignored_packages). Ensure files aren't left in command mode.
def unload_handler():
    for w in sublime.windows():
        for v in w.views():
            v.settings().set('command_mode', False)
            v.settings().set('inverse_caret_state', False)
            v.erase_status('mode')

# Ensures the input state is reset when the view changes, or the user selects
# with the mouse or non-vintage key bindings
class InputStateTracker(sublime_plugin.EventListener):
    def __init__(self):
        for w in sublime.windows():
            for v in w.views():
                v.settings().set('command_mode', True)
                v.settings().set('inverse_caret_state', True)
                update_status_line(v)

    def on_activated(self, view):
        reset_input_state(view)

    def on_deactivated(self, view):
        reset_input_state(view)

    def on_selection_modified(self, view):
        reset_input_state(view, False)
        update_status_line(view)

    def on_load(self, view):
        view.run_command('exit_insert_mode')

    def on_new(self, view):
        self.on_load(view)

    def on_clone(self, view):
        self.on_load(view)

    def on_query_context(self, view, key, operator, operand, match_all):
        if key == "vi_action" and g_input_state.action_command:
            if operator == sublime.OP_EQUAL:
                return operand == g_input_state.action_command
            if operator == sublime.OP_NOT_EQUAL:
                return operand != g_input_state.action_command
        elif key == "vi_has_action":
            v = g_input_state.action_command != None
            if operator == sublime.OP_EQUAL: return v == operand
            if operator == sublime.OP_NOT_EQUAL: return v != operand
        elif key == "vi_motion_mode":
            m = string_to_motion_mode(operand)
            if operator == sublime.OP_EQUAL:
                return m == g_input_state.motion_mode
            if operator == sublime.OP_NOT_EQUAL:
                return m != g_input_state.motion_mode
        elif key == "vi_has_repeat_digit":
            if g_input_state.motion_command:
                v = len(g_input_state.motion_repeat_digits) > 0
            else:
                v = len(g_input_state.prefix_repeat_digits) > 0
            if operator == sublime.OP_EQUAL: return v == operand
            if operator == sublime.OP_NOT_EQUAL: return v != operand

        return None

# Called when g_input_state represents a fully formed command. Generates a
# call to vi_eval, which is what will be left on the undo/redo stack.
def eval_input(view):
    global g_input_state

    cmd_args = {
            'prefix_repeat': digits_to_number(g_input_state.prefix_repeat_digits),
            'action_command': g_input_state.action_command,
            'action_args': g_input_state.action_command_args,
            'motion_repeat': digits_to_number(g_input_state.motion_repeat_digits),
            'motion_command': g_input_state.motion_command,
            'motion_args': g_input_state.motion_command_args,
            'motion_mode': g_input_state.motion_mode,
            'motion_inclusive': g_input_state.motion_inclusive }

    reset_motion_mode = (g_input_state.action_command != None)

    reset_input_state(view, reset_motion_mode)

    view.run_command('vi_eval', cmd_args)

# Adds a repeat digit to the input state.
# Repeat digits may come before the action, after the action, or both. For
# example:
#   4dw
#   d4w
#   2d2w
# These commands will all delete 4 words.
class PushRepeatDigit(sublime_plugin.TextCommand):
    def run(self, edit, digit):
        global g_input_state
        if g_input_state.action_command:
            g_input_state.motion_repeat_digits.append(digit)
        else:
            g_input_state.prefix_repeat_digits.append(digit)
        update_status_line(self.view)

# Set the current action in the input state. Note that this won't create an
# entry on the undo stack: only eval_input does this.
class SetAction(sublime_plugin.TextCommand):
    # Custom version of run_, so an edit object isn't created. This allows
    # eval_input() to add the desired command to the undo stack
    def run_(self, args):
        if 'event' in args:
            del args['event']

        return self.run(**args)

    def run(self, action, action_args = {}, motion_mode = None, description = None):
        global g_input_state
        g_input_state.action_command = action
        g_input_state.action_command_args = action_args
        g_input_state.action_description = description

        if motion_mode != None:
            m = string_to_motion_mode(motion_mode)
            if m != -1:
                if g_input_state.motion_mode == MOTION_MODE_LINE and m == MOTION_MODE_AUTO_LINE:
                    # e.g., 'Vjd', MOTION_MODE_LINE should be maintained
                    pass
                else:
                    set_motion_mode(self.view, m)
            else:
                print "invalid motion mode:", motion_mode

        if self.view.has_non_empty_selection_region():
            # Currently in visual mode, so no following motion is expected:
            # eval the current input
            eval_input(self.view)
        else:
            update_status_line(self.view)

def digits_to_number(digits):
    if len(digits) == 0:
        return 1

    number = 0
    place = 1
    for d in reversed(digits):
        number += place * int(d)
        place *= 10
    return number

# Set the current motion in the input state. Note that this won't create an
# entry on the undo stack: only eval_input does this.
class SetMotion(sublime_plugin.TextCommand):
    # Custom version of run_, so an edit object isn't created. This allows
    # eval_input() to add the desired command to the undo stack
    def run_(self, args):
        return self.run(**args)

    def run(self, motion, motion_args = {}, inclusive = False, character = None, mode = None):
        global g_input_state

        # Pass the character, if any, onto the motion command.
        # This is required for 'f', 't', etc
        if character != None:
            motion_args['character'] = character

        g_input_state.motion_command = motion
        g_input_state.motion_command_args = motion_args
        g_input_state.motion_inclusive = inclusive

        if mode != None:
            m = string_to_motion_mode(mode)
            if m != -1:
                set_motion_mode(self.view, m)
            else:
                print "invalid motion mode:", mode

        eval_input(self.view)

# Run a single, combined action and motion. Examples are 'D' (delete to EOL)
# and 'C' (change to EOL).
class SetActionMotion(sublime_plugin.TextCommand):
    # Custom version of run_, so an edit object isn't created. This allows
    # eval_input() to add the desired command to the undo stack
    def run_(self, args):
        return self.run(**args)

    def run(self, motion, action, motion_args = {}, motion_inclusive = False, action_args = {}):
        global g_input_state

        g_input_state.motion_command = motion
        g_input_state.motion_command_args = motion_args
        g_input_state.motion_inclusive = motion_inclusive
        g_input_state.action_command = action
        g_input_state.action_command_args = action_args

        eval_input(self.view)

# Update the current motion mode. e.g., 'dvj'
class SetMotionMode(sublime_plugin.TextCommand):
    def run_(self, args):
        if 'event' in args:
            del args['event']

        return self.run(**args)

    def run(self, mode):
        global g_input_state
        m = string_to_motion_mode(mode)

        if m != -1:
            set_motion_mode(self.view, m)
        else:
            print "invalid motion mode"

def clip_point_to_line(view, f, pt):
    l = view.line(pt)
    if l.a == l.b:
        return l.a

    new_pt = f(pt)
    if new_pt < l.a:
        return l.a
    elif new_pt >= l.b - 1:
        return l.b - 1
    else:
        return new_pt

def transform_selection(view, f, extend = False, clip_to_line = False):
    new_sel = []
    sel = view.sel()

    for r in sel:
        if clip_to_line:
            new_pt = clip_point_to_line(view, f, r.b)
        else:
            new_pt = f(r.b)

        if extend:
            new_sel.append(sublime.Region(r.a, new_pt))
        else:
            new_sel.append(sublime.Region(new_pt))

    sel.clear()
    for r in new_sel:
        sel.add(r)

def transform_selection_regions(view, f):
    new_sel = []
    sel = view.sel()

    for r in sel:
        nr = f(r)
        if nr != None:
            new_sel.append(nr)

    sel.clear()
    for r in new_sel:
        sel.add(r)

def expand_to_line(view):
    new_sel = []
    for s in view.sel():
        if s.a == s.b:
            new_sel.append(view.line(s.a))
        elif s.a < s.b:
            a = view.line(s.a).a
            b = view.line(s.b).b
            new_sel.append(sublime.Region(a, b))
        else:
            a = view.line(s.a).b
            b = view.line(s.b).a
            new_sel.append(sublime.Region(a, b))

    view.sel().clear()
    for s in new_sel:
        view.sel().add(s)

def expand_to_full_line(view):
    new_sel = []
    for s in view.sel():
        if s.a == s.b:
            new_sel.append(view.full_line(s.a))
        elif s.a < s.b:
            a = view.full_line(s.a).a
            b = view.full_line(s.b).b
            new_sel.append(sublime.Region(a, b))
        else:
            a = view.full_line(s.a).b
            b = view.full_line(s.b).a
            new_sel.append(sublime.Region(a, b))

    view.sel().clear()
    for s in new_sel:
        view.sel().add(s)

def expand_line_spanning_selections_to_line(view):
    new_sel = []
    for s in view.sel():
        if s.a == s.b:
            new_sel.append(s)
            continue

        la = view.full_line(s.a)
        lb = view.full_line(s.b)

        if la == lb:
            new_sel.append(s)
        elif s.a < s.b:
            a = la.a
            b = lb.b
            new_sel.append(sublime.Region(a, b))
        else:
            a = la.b
            b = lb.a
            new_sel.append(sublime.Region(a, b))

    view.sel().clear()
    for s in new_sel:
        view.sel().add(s)

def clip_empty_selection_to_line_contents(view):
    new_sel = []
    for s in view.sel():
        if s.empty():
            l = view.line(s.b)
            if s.b == l.b and not l.empty():
                s = sublime.Region(l.b - 1)

        new_sel.append(s)

    view.sel().clear()
    for s in new_sel:
        view.sel().add(s)

def shrink_inclusive(r):
    if r.a < r.b:
        return sublime.Region(r.b - 1)
    else:
        return sublime.Region(r.b)

def shrink_exclusive(r):
    return sublime.Region(r.b)

# This is the core: it takes a motion command, action command, and repeat
# counts, and runs them all.
#
# Note that this doesn't touch g_input_state, and doesn't maintain any state
# other than what's passed on its arguments. This allows it to operate correctly
# in macros, and when running via repeat.
class ViEval(sublime_plugin.TextCommand):
    def run(self, edit, prefix_repeat, action_command, action_args,
            motion_repeat, motion_command, motion_args, motion_mode,
            motion_inclusive):
        # Arguments are always passed as floats (thanks to JSON encoding),
        # convert them back to integers
        prefix_repeat = int(prefix_repeat)
        motion_repeat = int(motion_repeat)
        motion_mode = int(motion_mode)

        # Combine the prefix_repeat and motion_repeat into motion_repeat, to
        # allow commands like 2yy to work by first doing the motion twice,
        # then operating once
        if motion_command and prefix_repeat > 1:
            motion_repeat *= prefix_repeat
            prefix_repeat = 1

        # Check if the motion command would like to handle the repeat itself
        if motion_args and 'repeat' in motion_args:
            motion_args['repeat'] = motion_repeat * prefix_repeat
            motion_repeat = 1
            prefix_repeat = 1

        visual_mode = ((self.view.has_non_empty_selection_region() and not action_command) or
            (motion_mode == MOTION_MODE_LINE and not action_command) or
            (action_command and action_command == "visual"))

        for i in xrange(prefix_repeat):
            # Run the motion command, extending the selection to the range of
            # characters covered by the motion
            if motion_command:
                direction = 0
                if motion_args and 'forward' in motion_args:
                    forward = motion_args['forward']
                    if forward:
                        direction = 1
                    else:
                        direction = -1

                for j in xrange(motion_repeat):
                    if motion_mode == MOTION_MODE_LINE:
                        # Don't do either of the below things: this is
                        # important so that Vk on an empty line would select
                        # the following line.
                        pass
                    elif direction == 1 and motion_inclusive:
                        # Expand empty selections include the character
                        # they're on, and to start from the RHS of the
                        # character
                        transform_selection_regions(self.view,
                            lambda r: sublime.Region(r.b, r.b + 1) if r.empty() else r)
                    elif direction == -1:
                        # Expand empty selections include the character
                        # they're on, and to start from the LHS of the
                        # character
                        transform_selection_regions(self.view,
                            lambda r: sublime.Region(r.b + 1, r.b) if r.empty() else r)

                    self.view.run_command(motion_command, motion_args)

            if motion_mode == MOTION_MODE_LINE:
                expand_to_line(self.view)
            elif motion_mode == MOTION_MODE_AUTO_LINE:
                expand_line_spanning_selections_to_line(self.view)

            if action_command:
                # ensure the trailing newline is included, so that commands
                # like Vyp will duplicate the line
                if motion_mode == MOTION_MODE_LINE:
                    expand_to_full_line(self.view)

                # Apply the action to the selection
                self.view.run_command(action_command, action_args)

        if not visual_mode:
            # Shrink the selection down to a point
            if motion_inclusive:
                transform_selection_regions(self.view, shrink_inclusive)
            else:
                transform_selection_regions(self.view, shrink_exclusive)

        # Clip the selections to the line contents
        if self.view.settings().get('command_mode'):
            clip_empty_selection_to_line_contents(self.view)

        # Ensure the selection is visible
        self.view.show(self.view.sel())


class EnterInsertMode(sublime_plugin.TextCommand):
    # Ensure no undo group is created: the only entry on the undo stack should
    # be the insert_command, if any
    def run_(self, args):
        if args:
            return self.run(**args)
        else:
            return self.run()

    def run(self, insert_command = None, insert_args = None):
        # mark_undo_groups_for_gluing allows all commands run while in insert
        # mode to comprise a single undo group, which is important for '.' to
        # work as desired.
        self.view.run_command('mark_undo_groups_for_gluing')
        if insert_command:
            self.view.run_command(insert_command, insert_args)

        self.view.settings().set('command_mode', False)
        self.view.settings().set('inverse_caret_state', False)
        update_status_line(self.view)

class ExitInsertMode(sublime_plugin.TextCommand):
    def run_(self, args):
        edit = self.view.begin_edit(self.name(), args)
        try:
            self.run(edit)
        finally:
            self.view.end_edit(edit)

        # Call after end_edit(), to ensure the final entry in the glued undo
        # group is 'exit_insert_mode'.
        self.view.run_command('glue_marked_undo_groups')

    def run(self, edit):
        self.view.settings().set('command_mode', True)
        self.view.settings().set('inverse_caret_state', True)

        if not self.view.has_non_empty_selection_region():
            self.view.run_command('vi_move_by_characters_in_line', {'forward': False})

        update_status_line(self.view)

# Dummy command: visual mode is entered into by running this dummy action on a
# motion, thus creating a selection: visual mode is implicit in Vintage, if
# there's a non-empty selection then the buffer is considered to be in visual
# mode
class Visual(sublime_plugin.TextCommand):
    def run(self, edit):
        pass

class ExitVisualLineMode(sublime_plugin.TextCommand):
    def run(self, edit):
        set_motion_mode(self.view, MOTION_MODE_NORMAL)

class EnterVisualLineMode(sublime_plugin.TextCommand):
    def run(self, edit):
        set_motion_mode(self.view, MOTION_MODE_LINE)
        self.view.run_command('expand_selection', {'to': 'line_without_eol'})

class ExitVisualMode(sublime_plugin.TextCommand):
    def run(self, edit):
        if g_input_state.motion_mode != MOTION_MODE_NORMAL:
            set_motion_mode(self.view, MOTION_MODE_NORMAL)
        else:
            self.view.run_command('shrink_selections')

class ShrinkSelections(sublime_plugin.TextCommand):
    def shrink(self, r):
        if r.empty():
            return r
        elif r.a < r.b:
            return sublime.Region(r.b - 1)
        else:
            return sublime.Region(r.b)

    def run(self, edit):
        transform_selection_regions(self.view, self.shrink)

# Sequence is used as part of glue_marked_undo_groups: the marked undo groups
# are rewritten into a single sequence command, that accepts all the previous
# commands
class Sequence(sublime_plugin.TextCommand):
    def run(self, edit, commands):
        for cmd, args in commands:
            self.view.run_command(cmd, args)

class ViDelete(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.run_command('add_to_kill_ring', {'forward': False})
        self.view.run_command('left_delete')

class ViRightDelete(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.run_command('add_to_kill_ring', {'forward': True})
        self.view.run_command('right_delete')
        clip_empty_selection_to_line_contents(self.view)

class ViCopy(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.run_command('add_to_kill_ring', {'forward': True})
        transform_selection_regions(self.view, lambda r: sublime.Region(r.a))

class ViPasteRight(sublime_plugin.TextCommand):
    def advance(self, pt):
        if self.view.substr(pt) == '\n':
            return pt
        else:
            return pt + 1

    def run(self, edit):
        transform_selection(self.view, lambda pt: self.advance(pt))
        self.view.run_command('paste_from_kill_ring', {'forward': True})

class ViPasteLeft(sublime_plugin.TextCommand):
    def run(self, edit):
        self.view.run_command('paste_from_kill_ring', {'forward': False})

class PasteFromKillRingCommand(sublime_plugin.TextCommand):
    def run(self, edit, forward = True):
        kill_ring.seal()
        text = kill_ring.top()

        regions = [r for r in self.view.sel()]
        new_sel = []

        offset = 0

        for s in regions:
            s = sublime.Region(s.a + offset, s.b + offset)

            if len(text) > 0 and text[-1] == '\n':
                # paste line-wise
                if forward:
                    start = self.view.full_line(s.end()).b
                else:
                    start = self.view.line(s.begin()).a

                num = self.view.insert(edit, start, text)
                new_sel.append(start)
            else:
                # paste character-wise
                num = self.view.insert(edit, s.begin(), text)
                self.view.erase(edit, sublime.Region(s.begin() + num,
                    s.end() + num))
                num -= s.size()
                new_sel.append(s.begin())

            offset += num

        self.view.sel().clear()
        for s in new_sel:
            self.view.sel().add(s)

    def is_enabled(self):
        return len(kill_ring) > 0

class ReplaceCharacter(sublime_plugin.TextCommand):
    def run(self, edit, character):
        for s in self.view.sel():
            if s.empty():
                s = sublime.Region(s.b, s.b + 1)

            # TODO: Should leave the selection to the left of the character if it was empty
            self.view.replace(edit, s, character * len(s))
