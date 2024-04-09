import glob
import os
import platform
import shutil
import struct
import sys
from datetime import datetime
from distutils.core import setup

import py2exe

import sc4mpclient


VERSION = sc4mpclient.SC4MP_VERSION
DIST = "dist" + str(8 * struct.calcsize("P"))


def main():

	# MAKE DISTRIBUTION DIRECTORY IF IT DOES NOT YET EXIST
	if not os.path.exists(DIST):
		os.makedirs(DIST)

	# PURGE THE DISTRIBUTION DIRECTORY
	for item in os.listdir(DIST):
		item = os.path.join(DIST, item)
		if (os.path.isfile(item)):
			os.remove(item)
		else:
			shutil.rmtree(item)

	# USE PY2EXE
	sys.argv.append('py2exe')

	# RUN SETUP
	setup(
		windows=[{
			"script": "sc4mpclient.py",
			"icon_resources": [(1, "resources/icon.ico")],
		}],
		options={
			"py2exe": {
				"packages": [],
				"bundle_files": 1,
                "dist_dir": DIST,
				"optimize": 2,
				"compressed": True,
				"excludes":[],
				"verbose": 4
			}
		},
		zipfile=None,
		data_files=find_data_files('resources','resources',['*'])
	)

	# COPY LICENSE AND README TO DISTRIBUTION DIRECTORY
	print(f'Copying extra files to "{DIST}"...')
	shutil.copy("License.txt", DIST)
	shutil.copy("Readme.html", DIST)

	# CREATE A ZIP ARCHIVE OF THE DISTRIBUTION IF REQUESTED
	input("Press <Enter> to create a zip archive of the distribution...")
	destination = os.path.join(os.path.join("builds", "sc4mp-client-" + platform.system().lower() + "-" + str(8 * struct.calcsize("P")) + "-v" + VERSION + "." + datetime.now().strftime("%Y%m%d%H%M%S")))
	print('Creating zip archive of "' + DIST + '" at "' + destination + '"')
	shutil.make_archive(destination, "zip", DIST)


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


if __name__ == "__main__":
    main()