import os
import platform
import shutil
import struct
from datetime import datetime

import PyInstaller.__main__ as pyinstaller
from pyinstaller_versionfile import create_versionfile

import sc4mpclient


TITLE = "SC4MP Launcher"
VERSION = sc4mpclient.SC4MP_VERSION
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
		company_name="SimCity 4 Multiplayer Project",
		file_description="Multiplayer launcher for SimCity 4",
		internal_name=TITLE,
		legal_copyright="MIT-0",
		original_filename="sc4mpclient.exe",
		product_name=TITLE,
	)

	# Run setup
	print("Running setup...")
	pyinstaller.run([
		f"sc4mpclient.py",
		f"--specpath",
		f"{os.path.join('temp', 'spec')}",
        f"--distpath",
		f"{DIST}",
        f"--workpath",
		f"{os.path.join('temp', 'build')}",
        f"--onefile",
		f"--noupx",
        f"--windowed",
        f"-i",
		f"{os.path.abspath(os.path.join('resources', 'icon.ico'))}",
		f"--version-file",
		f"{os.path.abspath('version.rc')}"
	])

	# Copy extra files to distribution directory
	print(f'Copying extra files to "{DIST}"...')
	shutil.copytree("resources", os.path.join(DIST, "resources"))
	shutil.copy("License.txt", DIST)
	shutil.copy("Readme.html", DIST)

	# Create a zip archive of the distribution
	#input("Press <Enter> to create a zip archive of the distribution...")
	destination = os.path.join(os.path.join("builds", "sc4mp-client-" + platform.system().lower() + "-" + str(8 * struct.calcsize("P")) + "-v" + VERSION + "." + datetime.now().strftime("%Y%m%d%H%M%S")))
	print('Creating zip archive of "' + DIST + '" at "' + destination + '"')
	shutil.make_archive(destination, "zip", DIST)


if __name__ == "__main__":
    main()