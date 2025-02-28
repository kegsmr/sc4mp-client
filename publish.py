import sys

from sc4mpclient import SC4MP_VERSION, SC4MP_GITHUB_REPO
from core.util import publish_release, get_release_asset_path, get_current_git_branch


repo = SC4MP_GITHUB_REPO
token = sys.argv[1]
version = SC4MP_VERSION
assets = [
	("setupbuilds", f"sc4mp-client-installer-windows-v{version}"),
	("builds", f"sc4mp-client-windows-64-v{version}"),
	("builds", f"sc4mp-client-windows-32-v{version}"),
]


target = get_current_git_branch()

if target == "main":
	name = f"Draft {version}"
	body = "\n".join([
		"- {CHANGE}.",
		"- {CHANGE}.",
		"- {CHANGE}.",
	])
	prerelease = False
if target == "feature":
	name = f"Preview {version}"
	body = "\n\n".join([
		"This is a pre-release introducing new features from the next update, but also likely many bugs.",
		"If you encounter any issues, please report them on GitHub or in the SC4MP Discord.",
		"Thank you for playing on the SC4MP network, and stay tuned for further updates!",
	])
	prerelease = True
else:
	raise Exception("Releases can only be published from the `main` or `feature` branch.")

assets = [get_release_asset_path(directory, prefix) for directory, prefix in assets]
assets = [asset for asset in assets if asset is not None]

publish_release(repo=repo, token=token, version=version, name=name, body=body, assets=assets, prerelease=prerelease)