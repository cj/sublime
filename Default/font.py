import sublime, sublime_plugin

class IncreaseFontSizeCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        s = sublime.load_settings("Base File.sublime-settings")
        current = s.get("font_size", 10)
        current += 1
        if current > 18:
            current = 18
        s.set("font_size", current)

        sublime.save_settings("Base File.sublime-settings")

class DecreaseFontSizeCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        s = sublime.load_settings("Base File.sublime-settings")
        current = s.get("font_size", 10)
        current -= 1
        if current < 8:
            current = 8
        s.set("font_size", current)

        sublime.save_settings("Base File.sublime-settings")

class ResetFontSizeCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        s = sublime.load_settings("Base File.sublime-settings")
        s.erase("font_size")

        sublime.save_settings("Base File.sublime-settings")
