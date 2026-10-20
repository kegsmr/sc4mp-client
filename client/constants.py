"""Constants used across the launcher: version, URLs, paths and config
defaults."""

from __future__ import annotations

import platform
from pathlib import Path

from core.util import format_title, get_server_list, is_windows


SC4MP_VERSION = "0.9.0"

SC4MP_SERVERS = get_server_list()

SC4MP_GITHUB_REPO = "kegsmr/sc4mp-client"

SC4MP_URL = "https://www.sc4mp.org/"
SC4MP_CONTRIBUTORS_URL = f"https://github.com/{SC4MP_GITHUB_REPO}/contributors/"
SC4MP_ISSUES_URL = f"https://github.com/{SC4MP_GITHUB_REPO}/issues/"
SC4MP_RELEASES_URL = f"https://github.com/{SC4MP_GITHUB_REPO}/releases/"

SC4MP_AUTHOR_NAME = "SimCity 4 Multiplayer Project"
SC4MP_WEBSITE_NAME = "www.sc4mp.org"
SC4MP_LICENSE_NAME = "MIT-0"

SC4MP_CONFIG_PATH = "config.ini"
SC4MP_LOG_PATH = "sc4mpclient.log"
SC4MP_README_PATH = "readme.html"
SC4MP_RESOURCES_PATH = "resources"

SC4MP_TITLE = format_title("SC4MP Launcher", version=SC4MP_VERSION)
SC4MP_ICON: Path = Path(SC4MP_RESOURCES_PATH) / "icon.png"

SC4MP_HOST = "localhost"  # SC4MP_SERVERS[0][0]
SC4MP_PORT = 7240  # SC4MP_SERVERS[0][1]

SC4MP_BUFFER_SIZE = 4096

SC4MP_DELAY = .1

# Windows 7 can't display "🡒"
if is_windows() and platform.release() == "7":
    SC4MP_ARROW = "→"
else:
    SC4MP_ARROW = "🡒"

SC4MP_LAUNCHERMAP_ENABLED = False  # TODO replace with config setting eventually

SC4MP_CONFIG_DEFAULTS = [
    ("GENERAL", [

        ("default_host", SC4MP_HOST),
        ("default_port", SC4MP_PORT),

        ("auto_update", True),
        ("release_notes_version", SC4MP_VERSION),
        ("show_release_notes", True),

        ("use_server_browser", True),
        ("server_browser_filter", ""),
        ("scan_lan", True),
        ("stat_mayors_online_cutoff", 60),
        ("show_actual_download", True),
        ("show_rank_bars", True),
        ("show_offline_servers", True),
        ("use_fullscreen_background", True),
        ("use_launcher_map", True),
        ("use_game_overlay", 1),
        ("allow_game_monitor_exit", True),

        ("save_server_passwords", True),
        ("ignore_third_party_server_warnings", False),
        ("ignore_token_errors", False),
        ("ignore_risky_file_warnings", False),

        ("custom_plugins", False),
        ("custom_plugins_path", Path("~/Documents/SimCity 4/Plugins")
         .expanduser()),

        ("sync_simcity_4_cfg", True),

    ]),
    ("STORAGE", [

        ("storage_path", Path("_SC4MP").absolute()),
        ("cache_size", 8000)

    ]),
    ("SC4", [

        ("game_path", ""),
        ("use_steam_browser_protocol", 0),

        ("resw", 0),  # 1200
        ("resh", 0),  # 800
        ("fullscreen", True),  # False

        ("cpu_count", 1),
        ("cpu_priority", "high"),

        ("additional_properties", "")

    ]),
    ("DEBUG", [

        ("random_server_stats", False),
        ("ignore_incompatable_versions", False),

    ])
]

SC4MP_RISKY_FILE_EXTENSIONS = [
    ".bat", ".bin", ".cmd", ".com", ".cpl", ".dll", ".exe", ".gadget", ".inf1",
    ".ins", ".inx", ".isu", ".jar", ".job", ".jse", ".lnk", ".msc", ".msi",
    ".msp", ".mst", ".paf", ".pif", ".py", ".ps1", ".reg", ".rgs", ".scr",
    ".sct", ".sh", ".shb", ".shs", ".u3p", ".vb", ".vbe", ".vbs", ".vbscript",
    ".ws", ".wsf", ".wsh",
]

SC4MP_URL_PREFIX = "sc4mp://"

SC4MP_SERVERS_DOMAIN = "servers.sc4mp.org"
SC4MP_INVITES_DOMAIN = "invite.sc4mp.org"
