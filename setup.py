import os
import platform
import shutil
import struct
from datetime import datetime

import PyInstaller.__main__ as pyinstaller

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

	# RUN SETUP
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
		#f"--debug",
		#f"all"
	])

	# COPY LICENSE AND README TO DISTRIBUTION DIRECTORY
	print(f'Copying extra files to "{DIST}"...')
	shutil.copytree("resources", os.path.join(DIST, "resources"))
	shutil.copy("License.txt", DIST)
	shutil.copy("Readme.html", DIST)

	# CREATE A ZIP ARCHIVE OF THE DISTRIBUTION IF REQUESTED
	input("Press <Enter> to create a zip archive of the distribution...")
	destination = os.path.join(os.path.join("builds", "sc4mp-client-" + platform.system().lower() + "-" + str(8 * struct.calcsize("P")) + "-v" + VERSION + "." + datetime.now().strftime("%Y%m%d%H%M%S")))
	print('Creating zip archive of "' + DIST + '" at "' + destination + '"')
	shutil.make_archive(destination, "zip", DIST)


if __name__ == "__main__":
    main()