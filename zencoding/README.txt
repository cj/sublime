= HELP =

    == Overview ==

    See the `Sublime 2 Zen Coding announcement` post:
        
        http://www.sublimetext.com/forum/viewtopic.php?f=2&t=580&p=10654#p10654

    == Installation ==

    See in the announcement post and also: 

    See `Installation guide for Zencoding into SublimeText 2` forum thread:

        http://www.sublimetext.com/forum/viewtopic.php?f=5&t=2366

= SETTINGS =

    There's two options for declaring customisations to the zen_settings. You
    can either use a `my_zen_settings.py` with a global level dict
    `my_zen_settings` or you can use `zen-settings.sublime-settings` and declare
    the settings in JSON.

    If both are declared the JSON will `win`.

    == my_zen_settings.py ==

        This can be in either of two places, the first of which found will be
        used.

            * ~/my_zen_settings.py
            * $PACKAGES_PATH/my_zen_setting

    == zen-settings.sublime-settings ==

        Create a $PACKAGES_PATH/ZenCoding/zen-settings.sublime-settings
        and create a settings dict:

        {
            "debug" : false,

            "completions_blacklist": [
                // "css_selectors",
                // "css_property_values",
                // "html_elements_attributes",
                // "html_attributes_values",
                // "css_properties"
            ],

            "my_zen_settings" : {
                "html": {
                    "abbreviations": {
                        "jq": "<script src='jquery.js' type='javascript'>",
                        "demo": "<div id=\"demo\"></div>"
                    }
               }
            }
        }

    == Dict Format ==

    See https://github.com/sergeche/zen-coding/blob/master/python/zencoding/zen_settings.py
    to see what settings you can override/ extend.

    {
        'css': {
            'filters': 'html,css,fc'
        }
    }