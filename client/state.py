"""Shared mutable state of the launcher.

These values are reassigned while the launcher runs (by main(), the config,
the game launcher, the UI, ...). Always use them as `state.<name>`: a
`from client.state import name` would only copy the value once, and later
changes would not be seen.
"""

# Command-line options, set by main()
sc4mp_force_update = None
sc4mp_skip_update = None
sc4mp_exit_after = None
sc4mp_host = None
sc4mp_port = None
sc4mp_password = None

# The main Tk window. `True`/`False` before it is created (whether the UI is
# enabled), and `None` in command-line mode.
sc4mp_ui = None

# The user's settings (a core.config.Config), set by load_config()
sc4mp_config = None

# Copies of some config values, kept for older code that still uses them.
# Updated by update_config_constants() every time the config is saved.
SC4MP_LAUNCHPATH = None
SC4MP_LAUNCHRESW = None
SC4MP_LAUNCHRESH = None
SC4MP_CUSTOMPATH = None

# Database of known servers (a DatabaseManager), set by load_database()
sc4mp_servers_database = None

# The server being played on, and the thread that runs SimCity 4
sc4mp_current_server = None
sc4mp_game_launcher = None

# Lets the game monitor window close even if SimCity 4 is still running
sc4mp_allow_game_monitor_exit_if_error = None
sc4mp_game_exit_ovveride = None

# Position of the game monitor window, remembered while the launcher runs
sc4mp_game_monitor_x = 10
sc4mp_game_monitor_y = 40

# `True` if this version is a pre-release (from the GitHub release info)
sc4mp_beta = None

# Last tab opened in the server details window
sc4mp_server_details_ui_last_tab_index = 0
