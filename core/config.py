"""The Config class, which reads and writes a user's .ini config file."""

import configparser


class Config:
    """Encapsules a dictionary of the config values set by the user."""

    def __init__(self, path, defaults, error_callback=None,
                 update_constants_callback=None):
        """TODO"""

        # Parameters
        self.PATH = path
        self.DEFAULTS = defaults
        self.show_error = error_callback
        self.update_config_constants = update_constants_callback

        # Create dictionary with default config settings
        self.data = {}
        for section_name, section_items in self.DEFAULTS:
            self.data.setdefault(section_name, {})
            for item_name, item_value in section_items:
                self.data[section_name].setdefault(item_name, item_value)

        # Try to read settings from the config file and update the
        # dictionary accordingly
        parser = configparser.RawConfigParser()
        try:
            parser.read(self.PATH)
            for section_name, section in self.data.items():
                try:
                    for item_name in section:
                        try:
                            from_file = parser.get(section_name, item_name)
                            values = self.data[section_name]
                            if from_file in ("true", "True", "TRUE"):
                                values[item_name] = True
                            elif from_file in ("false", "False", "FALSE"):
                                values[item_name] = False
                            elif from_file in ("none", "None", "NONE"):
                                values[item_name] = None
                            else:
                                # Convert to the same type as the default
                                t = type(values[item_name])
                                values[item_name] = t(from_file)
                        except (configparser.NoSectionError,
                                configparser.NoOptionError):
                            print(
                                f"[WARNING] Option \"{item_name}\" missing "
                                f"from section \"{section_name}\" of the "
                                f"config file at \"{self.PATH}\". "
                                f"Using default value."
                            )
                        except Exception:
                            self.show_error(
                                "An error occurred while reading a config "
                                "item.",
                                no_ui=True
                            )
                except Exception:
                    self.show_error(
                        "An error occurred while reading a config section.",
                        no_ui=True
                    )
        except Exception:
            self.show_error(
                "An error occurred while reading the config.", no_ui=True
            )

        # Update config file
        self.update()

    def __getitem__(self, key):
        """TODO"""
        return self.data.__getitem__(key)

    def __setitem__(self, key, value):
        """TODO"""
        return self.data.__setitem__(key, value)

    def update(self):
        """Writes config values set by the user to the config file."""
        parser = configparser.RawConfigParser()
        for section_name, section in self.data.items():
            parser.add_section(section_name)
            for item_name, item_value in section.items():
                parser.set(section_name, item_name, item_value)
        with open(self.PATH, 'wt') as file:
            parser.write(file)
        # The callback is optional, so any error from it is ignored
        try:
            self.update_config_constants(self)
        except BaseException:
            pass
