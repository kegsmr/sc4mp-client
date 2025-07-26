import requests

import core.util as utils
from sc4mpclient import SC4MP_GITHUB_REPO, SC4MP_VERSION


def main():
	
	github_online: bool = requests.head(
		"https://github.com/"
	).ok

	release_exists: bool = requests.head(
		f"https://github.com/{SC4MP_GITHUB_REPO}/releases/tag/v{SC4MP_VERSION}"
	).ok

	if github_online and release_exists:

		v: tuple = utils.unformat_version(SC4MP_VERSION)
		version: str = utils.format_version(v[:-1] + (v[-1] + 1,))

		utils.update_python_version("sc4mpclient.py", version)


if __name__ == '__main__':
	main()