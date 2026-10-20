"""Small helpers for files, paths, windows and processes."""

from __future__ import annotations

import ctypes
import json
import os
import random
import re
import shutil
import string
import struct
import subprocess
import time
from pathlib import Path

from core.util import format_filesize, is_windows
from client import state
from client.constants import SC4MP_RESOURCES_PATH
from client.errors import ClientException


# TODO add MacOS compatability / deprecate in favor of `process_count`?
def process_exists(process_name):

    if is_windows():
        call = 'TASKLIST', '/FI', 'imagename eq %s' % process_name
        output = subprocess.check_output(call, shell=True).decode()
        last_line = output.strip().split('\r\n')[-1]
        return last_line.lower().startswith(process_name.lower())
    else:
        return None


def get_sc4mp_path(filename: str) -> Path:
    """Returns the path to a given file in the SC4MP "resources" subdirectory"""
    return Path(SC4MP_RESOURCES_PATH) / filename


def random_string(length):
    """Returns a random string of ascii letters of the specified length."""
    characters = string.ascii_letters + string.digits
    return ''.join(
        random.SystemRandom().choice(characters) for i in range(length)
    )


def purge_directory(directory: Path, recursive=True) -> None:
    """Deletes all files and subdirectories of a directory"""
    for path in directory.iterdir():
        # retry, since another process (e.g. OneDrive or antivirus) may only be
        # using the file briefly
        for attempt in range(5):
            try:
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    if recursive:
                        shutil.rmtree(path)
                break
            except PermissionError as e:
                if attempt == 4:
                    raise ClientException(
                        f'Failed to delete "{path}" because the file is being '
                        'used by another process.'
                    ) from e  # \n\n' + str(e)
                time.sleep(.5)


def directory_size(directory: Path) -> int:
    """Returns the size of a directory recursively."""

    size = 0

    with os.scandir(directory) as items:
        for item in items:
            if item.is_file():
                size += item.stat().st_size
            elif item.is_dir():
                size += directory_size(item.path)

    return size


def load_json(filename):
    """Returns data from a json file as a dictionary."""
    try:
        with open(filename, 'r') as file:
            data = json.load(file)
            if data is None:
                return dict()
            else:
                return data
    except FileNotFoundError:
        return dict()


def update_json(filename, data):
    """Writes data as a dictionary to a json file."""
    # Write to a temporary file first so a crash or error mid-write can't
    # truncate the original
    temp_filename = f"{filename}.tmp"
    with open(temp_filename, 'w') as file:
        json.dump(data, file, indent=4)
        file.flush()
        os.fsync(file.fileno())
    try:
        os.replace(temp_filename, filename)
    except PermissionError:
        # On Windows, the replace fails while another process (antivirus,
        # OneDrive, etc.) has the file open, so fall back to writing in place
        with open(filename, 'w') as file:
            json.dump(data, file, indent=4)
        os.unlink(temp_filename)


def center_window(window):
    """Centers a tkinter window."""
    win = window
    win.update_idletasks()
    width = win.winfo_width()
    frm_width = win.winfo_rootx() - win.winfo_x()
    win_width = width + 2 * frm_width
    height = win.winfo_height()
    titlebar_height = win.winfo_rooty() - win.winfo_y()
    win_height = height + titlebar_height + frm_width
    x = win.winfo_screenwidth() // 2 - win_width // 2
    y = win.winfo_screenheight() // 2 - win_height // 2
    win.geometry(f'{width}x{height}+{x}+{y}')
    win.deiconify()


def prep_server(path: Path) -> None:
    """Runs the server executable in prep mode. Takes the server path as an argument."""
    subprocess.Popen(f"sc4mpserver.exe -prep --server-path {path}")


def start_server(path: Path) -> None:
    """Runs the server executable. Takes the server path as an argument."""
    subprocess.Popen(
        f"sc4mpserver.exe --server-path {path}",
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )


def get_fullpaths_recursively(dir: Path) -> list[Path]:
    """Returns full paths of all files in a directory recursively."""
    return [path for path in dir.rglob("*") if path.is_file()]


def get_relpaths_recursively(dir: Path) -> list[Path]:
    """Returns relative paths of all files in a directory recursively."""
    return [path.relative_to(dir) for path in dir.rglob("*") if path.is_file()]


def get_arg_value(arg, args):
    """Returns the following token in commandline arguments."""
    return args[args.index(arg) + 1]


def format_download_size(size):
    if size == 0:
        return "..."
    else:
        return format_filesize(size)


def get_bitmap_dimensions(filename):

    with open(filename, "rb") as file:
        data = bytearray(file.read())

    width = struct.unpack_from('<i', data, 18)
    height = struct.unpack_from('<i', data, 22)

    return width[0], height[0]


def arp():
    if is_windows():
        call = 'arp', '-a'
        output = subprocess.check_output(call, shell=True).decode()
        return [line for line in re.findall(r'([-.0-9]+)\s+([-0-9a-f]{17})\s+(\w+)', output)]
    else:  # TODO make this work on other platforms besides Windows
        return []


def format_url(url: str) -> str:
    if not (url.startswith("http://") or url.startswith("https://")):
        return f"http://{url}"
    else:
        return url


def copy_to_clipboard(text: str):

    state.sc4mp_ui.clipboard_clear()
    state.sc4mp_ui.clipboard_append(text)


def get_image_pids(image_name) -> list[int] | None:
    """
    Find the PIDs of processes with the given image name on Windows.

    Args:
        image_name (str): The name of the process image (e.g., "notepad.exe").

    Returns:
        list: A list of PIDs for processes matching the given image name.
    """

    if is_windows():

        pids = []

        try:

            # Use tasklist to get the list of processes
            result = subprocess.run(
                ["tasklist"],
                capture_output=True,
                text=True,
                check=True,
                shell=True
            )
            lines = result.stdout.splitlines()

            # Regex pattern to match process name followed by its PID
            pattern = re.compile(
                rf"^{re.escape(image_name)}\s+(\d+)", re.IGNORECASE
            )

            for line in lines:
                match = pattern.match(line)
                if match:
                    try:
                        pids.append(int(match.group(1)))  # Extract PID
                    except ValueError:
                        pass

            if pids:
                return pids
            else:
                return None

        except subprocess.CalledProcessError as e:
            print(f"An error occurred while getting image PIDs.\n\n{e}")
            return None

    else:

        return None


def window_open(image_name):
    """
    Check if a process with the given image name has an open, visible window.

    Args:
        image_name (str): The name of the process image (e.g., "notepad.exe").

    Returns:
        bool: True if at least one instance of the process has a visible window, False otherwise.
    """

    pids = get_image_pids(image_name)
    # print(f"PIDs for {image_name}: {pids}")  # Debugging

    if not pids:
        return False  # No matching processes found

    EnumWindows = ctypes.windll.user32.EnumWindows
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible
    GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId

    # Properly define the callback function with ctypes
    def callback(hwnd, lParam):
        """Callback function to check if a window belongs to the given PID and is visible."""
        window_pid = ctypes.c_ulong()
        GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))

        if window_pid.value in pids and IsWindowVisible(hwnd):
            ctypes.cast(lParam, ctypes.POINTER(ctypes.c_bool)).contents.value = True
            return False  # Stop enumeration

        return True  # Continue searching

    # Create a ctypes boolean variable to store result
    found = ctypes.c_bool(False)

    # Convert callback to proper function pointer type
    CALLBACK_TYPE = ctypes.WINFUNCTYPE(
        ctypes.c_bool, ctypes.c_int, ctypes.c_void_p
    )
    EnumWindows(CALLBACK_TYPE(callback), ctypes.byref(found))

    return found.value
