import os
import platform
import shutil
import struct
from datetime import datetime

import PyInstaller.__main__ as pyinstaller
from pyinstaller_versionfile import create_versionfile

import sc4mpclient


TITLE = "SC4MP Launcher"
NAME = "sc4mpclient.exe"
VERSION = sc4mpclient.SC4MP_VERSION
PUBLISHER = "SimCity 4 Multiplayer Project"
DESCRIPTION = "Multiplayer launcher for SimCity 4"
LICENSE = "MIT-0"
DIST = "dist" + str(8 * struct.calcsize("P"))


def main():

	# Make distribution directory if it does not yet exist
	print(f"Preparing distribution directory at \"{DIST}\"")
	if not os.path.exists(DIST):
		os.makedirs(DIST)

	# Purge the distribution directory
	for item in os.listdir(DIST):
		item = os.path.join(DIST, item)
		if (os.path.isfile(item)):
			os.remove(item)
		else:
			shutil.rmtree(item)

	# Create version file
	print(f"Creating version file...")
	create_versionfile(
		output_file="version.rc",
		version=VERSION,
		company_name=PUBLISHER,
		file_description=TITLE,
		internal_name=TITLE,
		legal_copyright=LICENSE,
		original_filename=NAME,
		product_name=TITLE,
	)

	# Run setup
	print("Running setup...")
	pyinstaller.run([
		f"sc4mpclient.py",
		f"--specpath",
		f"{os.path.join('temp', 'spec')}",
        f"--distpath",
		f"dist",
        f"--workpath",
		f"{os.path.join('temp', 'build')}",
        f"--onedir",
		f"--contents-directory",
		f"resources",
		f"--noconfirm",
		f"--noupx",
        f"--windowed",
        f"-i",
		f"{os.path.abspath(os.path.join('resources', 'icon.ico'))}",
		f"--version-file",
		f"{os.path.abspath('version.rc')}",
		#f"--splash",
		#f"{os.path.abspath(os.path.join('resources', 'splash.png'))}"
	])

	# Copy binary files to distribution directory
	shutil.copytree(os.path.join("dist", "sc4mpclient"), DIST, dirs_exist_ok=True)

	# Copy extra files to distribution directory
	print(f'Copying extra files to "{DIST}"...')
	shutil.copytree("resources", os.path.join(DIST, "resources"), dirs_exist_ok=True)
	shutil.copy("License.txt", DIST)
	shutil.copy("Readme.html", DIST)

	# Create a zip archive of the distribution
	destination = os.path.join(os.path.join("builds", "sc4mp-client-" + platform.system().lower() + "-" + str(8 * struct.calcsize("P")) + "-v" + VERSION + "." + datetime.now().strftime("%Y%m%d%H%M%S")))
	print('Creating zip archive of "' + DIST + '" at "' + destination + '"')
	shutil.make_archive(destination, "zip", DIST)


if __name__ == "__main__":
    main()