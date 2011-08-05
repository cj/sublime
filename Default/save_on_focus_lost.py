import sublime, sublime_plugin

class SaveOnFocusLost(sublime_plugin.EventListener):
    def on_deactivated(self, view):
        if (view.file_name() and view.is_dirty() and
                view.settings().get('save_on_focus_lost') == True):
            view.run_command('save');
