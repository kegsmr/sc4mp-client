from distutils.core import setup
import py2exe
import sys
import os
import glob

sys.argv.append('py2exe')

def find_data_files(source,target,patterns):
    """Locates the specified data-files and returns the matches
    in a data_files compatible format.

    source is the root of the source data tree.
        Use '' or '.' for current directory.
    target is the root of the target data tree.
        Use '' or '.' for the distribution directory.
    patterns is a sequence of glob-patterns for the
        files you want to copy.
    """
    if glob.has_magic(source) or glob.has_magic(target):
        raise ValueError("Magic not allowed in src, target")
    ret = {}
    for pattern in patterns:
        pattern = os.path.join(source,pattern)
        for filename in glob.glob(pattern):
            if os.path.isfile(filename):
                targetpath = os.path.join(target,os.path.relpath(filename,source))
                path = os.path.dirname(targetpath)
                ret.setdefault(path,[]).append(filename)
    return sorted(ret.items())

setup(
	windows=[{
		"script": "sc4mpclient.py",
		"icon_resources": [(1, "resources/icon.ico")],
		"name": "SC4MP Launcher",
		"author": "Simcity 4 Multiplayer Project",
        "description": "Multiplayer launcher for Simcity 4",
		"version": "v1.0.0"
	}],
	options={
		"py2exe": {
			"packages": [],
            "bundle_files": 1,
			"optimize": 2,
			"compressed": True,
            "excludes":[]
		}
	},
    zipfile=None,
	data_files=find_data_files('resources','resources',['*'])
)