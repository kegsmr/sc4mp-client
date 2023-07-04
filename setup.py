import glob
import os
import platform
import shutil
import sys
from datetime import datetime
from distutils.core import setup

import py2exe

VERSION = (0,1,0)

for item in os.listdir("dist"):
    item = os.path.join("dist", item)
    if (os.path.isfile(item)):
        os.remove(item)
    else:
        shutil.rmtree(item)

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
	}],
	options={
		"py2exe": {
			"packages": [],
            "bundle_files": 1,
			"optimize": 2,
			"compressed": True,
            "excludes":[],
            "verbose": 4
		}
	},
    zipfile=None,
	data_files=find_data_files('resources','resources',['*'])
)

print('Copying extra files to "dist"...')
shutil.copy("README.md", "dist")
shutil.copy("License.txt", "dist")
shutil.copy("Readme.html", "dist")

'''try: #TODO re-enable at some point
    print('Copying server distribution to "dist"...')
    shutil.copy("D:\\Users\\Kegan\\Desktop\\Projects\\mod\\sc4\\SC4MP\\sc4mp-server\\dist\\sc4mpserver.exe", "dist")
    shutil.copytree("D:\\Users\\Kegan\\Desktop\\Projects\\mod\\sc4\\SC4MP\\sc4mp-server\\dist\\resources", "dist\\resources", dirs_exist_ok=True)
except:
    print('Failed!')'''

target = "dist"
destination = os.path.join(os.path.join("builds", "sc4mp-client-" + platform.system().lower() + "-v" + str(VERSION[0]) + "." + str(VERSION[1]) + "." + str(VERSION[2]) + "." + datetime.now().strftime("%Y%m%d%H%M%S")))
print('Creating zip archive of "' + target + '" at "' + destination + '"')
shutil.make_archive(destination, "zip", target)