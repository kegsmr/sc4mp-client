import configparser
import hashlib
import os
import subprocess
import wx


#s = requests.Session()
#s.headers["User-Agent"] = "PMRClient 1.0.0" 
#TODO: dunno what these two lines are for

#stagedsaves = [] #TODO: dunno exactly what this is for

dmr_resources_path = "resources"

def_dmrpath = os.path.join(os.path.expanduser('~'),"Documents","SimCity 4","_DMR") + "\\"
def_resw = 1280
def_resh = 800
def_sc4path = ""

DMR_LAUNCHPATH = None
DMR_LAUNCHRESW = None
DMR_LAUNCHRESH = None
#DMR_SERVERPATH = "http://api.getpmr.com/" #TODO: will probably replace with a website hosting a server list
DMR_CUSTOMPATH = None


def get_dmr_path(filename):
	return os.path.join(dmr_resources_path, filename)


#TODO: dunno what this does
def md5(fname):
	hash_md5 = hashlib.md5()
	with open(fname, "rb") as f:
		for chunk in iter(lambda: f.read(4096), b""):
			hash_md5.update(chunk)
	return hash_md5.hexdigest()


#TODO: UI
class DMRClient(wx.Frame):
	
	def __init__(self, parent):
		super(DMRClient, self).__init__(parent, style=wx.CAPTION | wx.CLOSE_BOX)
		#self.Bind(EVT_SERVERSTATUSRESPONSE, self.onCheckServerReponse)
		#self.Bind(EVT_LISTINGRESPONSE, self.FinishRefreshList)
		
		self.InitUI()
		self.Fit()
		self.Centre()
		self.Show()

		#self.Prep()

		#self.CheckServer()
		#self.StartRefreshList()

		#self.Bind(wx.EVT_CLOSE, self.onClose)

	def InitUI(self):
		panel = wx.Panel(self)
		panel.SetBackgroundColour('#eeeeee')

		ico = wx.Icon(get_dmr_path('icon.ico'), wx.BITMAP_TYPE_ICO)
		self.SetIcon(ico)

		vbox = wx.BoxSizer(wx.VERTICAL)

		flag = wx.StaticBitmap(panel, wx.ID_ANY, wx.Bitmap(get_dmr_path("flag.png"), wx.BITMAP_TYPE_ANY))

		self.infotext = wx.StaticText(panel, label='To get started, select a region below and click \'Connect.\'', style=wx.ALIGN_CENTRE_HORIZONTAL | wx.ST_NO_AUTORESIZE)

		self.regionlist = wx.ListCtrl(panel, -1, style = wx.LC_REPORT, size=(-1,300)) 
		self.regionlist.InsertColumn(0, "Region Name", width=225)
		self.regionlist.InsertColumn(1, "Claimed Tiles", wx.LIST_FORMAT_RIGHT, width=100)
		self.regionlist.InsertColumn(2, "Mayors Online", wx.LIST_FORMAT_RIGHT, width=100)
		#self.regionlist.Bind(wx.EVT_LIST_ITEM_SELECTED, self.SelectRegion)
		#self.regionlist.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.DeselectRegion)
		#self.regionlist.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.ConnectToSelectedRegion)

		hbox = wx.BoxSizer(wx.HORIZONTAL)
		self.settingbtn = wx.Button(panel, label='SC4 Settings...')
		self.settingbtn.SetToolTip(wx.ToolTip("Set your preferred resolution and launch path"))
		#self.settingbtn.Bind(wx.EVT_BUTTON, self.ShowSettingsDialog)
		self.refreshbtn = wx.Button(panel, label='Refresh')
		#self.refreshbtn.Bind(wx.EVT_BUTTON, self.StartRefreshList)
		self.refreshbtn.SetToolTip(wx.ToolTip("Refresh the region listing"))
		self.connectbtn = wx.Button(panel, label='Connect')
		#self.connectbtn.Bind(wx.EVT_BUTTON, self.ConnectToSelectedRegion)
		self.connectbtn.SetToolTip(wx.ToolTip("Connect to the selected region"))
		self.connectbtn.Disable()
		hbox.Add(self.settingbtn, 0, wx.RIGHT | wx.ALIGN_LEFT, 5)
		hbox.InsertStretchSpacer(1)
		#hbox.Add(self.refreshbtn, 0, wx.RIGHT | wx.ALIGN_RIGHT, 5)
		#hbox.Add(self.connectbtn, 0, wx.ALIGN_RIGHT, 10)

		#vbox.Add(flag, 0, wx.ALL, 0)
		vbox.Add(self.infotext, 0, wx.EXPAND|wx.ALL, 10)
		vbox.Add(self.regionlist, 1, wx.EXPAND|wx.LEFT|wx.RIGHT, 10)
		vbox.Add(hbox, 0, wx.EXPAND|wx.ALL, 10)

		panel.SetSizer(vbox)
		panel.Fit()

		self.SetTitle("Poppy Multiplayer Regions")

#TODO: documentation
# Load configuration file, or create one if it doesn't exist
def loadConfig():

	global DMR_LAUNCHPATH
	global DMR_LAUNCHRESW
	global DMR_LAUNCHRESH
	global DMR_CUSTOMPATH
	
	#TODO add cpu options for start parameters
	configpath = get_dmr_path("config.ini")
	try:
		config = configparser.RawConfigParser()
		config.read(configpath)

		DMR_LAUNCHPATH = config.get('launcher', 'path')
		DMR_LAUNCHRESW = config.get('launcher', 'resw')
		DMR_LAUNCHRESH = config.get('launcher', 'resh')
		DMR_CUSTOMPATH = config.get('launcher', 'sc4path')
	except:
		config.remove_section('launcher')
		config.add_section('launcher')
		config.set('launcher', 'path', def_dmrpath)
		config.set('launcher', 'resw', def_resw)
		config.set('launcher', 'resh', def_resh)
		config.set('launcher', 'sc4path', def_sc4path)
		
		with open(configpath, 'wt') as configfile: #apparently you have to use 'wt' for this now instead of 'wb'
			config.write(configfile)

		DMR_LAUNCHPATH = def_dmrpath
		DMR_LAUNCHRESW = def_resw
		DMR_LAUNCHRESH = def_resh
		DMR_CUSTOMPATH = def_sc4path


#TODO: documentation
def createDirectories():

	directories = ["DMRCache", "DMRPluginsCache", "DMRSalvage", "Regions", "Plugins", os.path.join("Plugins","DMRPlugins")]

	for directory in directories:
		directorytocreate = os.path.join(DMR_LAUNCHPATH, directory)
		if not os.path.exists(directorytocreate):
			try:
				os.makedirs(directorytocreate)
			except:
				return "Failed to create directories."
		if directory == "Plugins":
			noticepath = os.path.join(DMR_LAUNCHPATH, directory, "__PUT YOUR PLUGINS IN THIS FOLDER__.txt")
			open(noticepath, 'a').close()

	return None


#TODO: documentation
def loadPlugins():
	#TODO: implement
	return None


#TODO: documentation
def loadRegions():
	#TODO: implement
	return None


#TODO: documentation
def startSC4():

	possiblePaths = [
		os.path.abspath(os.path.join("\\", "Program Files (x86)", "Steam", "steamapps", "common", "SimCity 4 Deluxe", "Apps", "SimCity 4.exe")),
		os.path.abspath(os.path.join("\\", "Program Files", "Steam", "steamapps", "common", "SimCity 4 Deluxe", "Apps", "SimCity 4.exe")),
		os.path.abspath(os.path.join("\\", "Program Files (x86)", "Maxis", "SimCity 4 Deluxe", "Apps", "SimCity 4.exe")),
		os.path.abspath(os.path.join("\\", "Program Files", "Maxis", "SimCity 4 Deluxe", "Apps", "SimCity 4.exe")),
		DMR_CUSTOMPATH,
		os.path.join(DMR_CUSTOMPATH, "SimCity 4.exe"),
		os.path.join(DMR_CUSTOMPATH, "Apps", "SimCity 4.exe")
	]

	path = None

	for possiblePath in possiblePaths:
		if possiblePath:
			if os.path.isfile(possiblePath):
				path = '"' + possiblePath + '"'
				break

	if not path:
		return "Path to Simcity 4 not found."

	arguments = [path, ' -UserDir:"' + DMR_LAUNCHPATH + '"', ' -intro:off', ' -w', ' -CustomResolution:enabled', ' -r' + str(DMR_LAUNCHRESW) + 'x' + str(DMR_LAUNCHRESH) + 'x32']
	
	try:
		subprocess.run(' '.join(arguments))
	except PermissionError:
		return "Permission denied. Run the program as administrator."

	return None


#TODO: documentation
def cmd():
	print(loadConfig())
	print(createDirectories())
	print(loadPlugins())
	print(loadRegions())
	print(startSC4())


#TODO: documentation
def main():
	dmr = wx.App()
	DMRClient(None)
	dmr.MainLoop()


# Load the main function
if __name__ == '__main__':
	cmd()