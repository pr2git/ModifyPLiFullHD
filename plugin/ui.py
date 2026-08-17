from __future__ import print_function
# for localized messages
from . import _
#################################################################################
#
#    Plugin for Enigma2
#    version:
VERSION = "1.50"
#    Coded by ims (c)2015-2026
#
#    This program is free software; you can redistribute it and/or
#    modify it under the terms of the GNU General Public License
#    as published by the Free Software Foundation; either version 2
#    of the License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#################################################################################

from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import ConfigIP, NoSave, ConfigSubsection, config, ConfigSelection, ConfigYesNo
from Components.ActionMap import ActionMap
from Components.Label import Label
from Screens.Standby import TryQuitMainloop
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Components.ScrollLabel import ScrollLabel

import os
import skin
import enigma
import shutil
from Tools.Directories import resolveFilename, SCOPE_CONFIG, SCOPE_CURRENT_SKIN, fileExists, SCOPE_FONTS
import xml.etree.cElementTree as ET
import glob
from .plugin import plugin_path

cfg = config.plugins.ModifyPLiFullHD
cfg.skin = NoSave(ConfigSelection(default="PLi-FullHD", choices=[("PLi-FullHD", "PLi-FullHD"), ("PLi-FullNightHD", "PLi-FullNightHD"), ("PLi-HD1", "PLi-HD1")]))
cfg.toptemplatecolor = NoSave(ConfigIP(default=[0, 0, 0, 48]))
cfg.basictemplatecolor = NoSave(ConfigIP(default=[0, 0, 0, 32]))
cfg.selectorcolor = NoSave(ConfigIP(default=[0, 0, 0, 48]))
cfg.transponderinfocolor = NoSave(ConfigIP(default=[0, 0, 144, 240]))
cfg.selectedfgcolor = NoSave(ConfigIP(default=[0, 252, 192, 0]))
cfg.selectedfgeventcolor = NoSave(ConfigIP(default=[0, 240, 240, 240]))
cfg.yellowcolor = NoSave(ConfigIP(default=[0, 255, 192, 0]))
cfg.yellowsoftcolor = NoSave(ConfigIP(default=[0, 204, 172, 104]))
cfg.redcolor = NoSave(ConfigIP(default=[0, 250, 64, 16]))
cfg.secondfgcolor = NoSave(ConfigIP(default=[0, 252, 192, 0]))
cfg.greycolor = NoSave(ConfigIP(default=[0, 170, 170, 170]))
cfg.darkgreycolor = NoSave(ConfigIP(default=[0, 85, 85, 85]))
cfg.backgroundcolor = NoSave(ConfigIP(default=[0, 0, 0, 0]))
cfg.blackcolor = NoSave(ConfigIP(default=[0, 0, 0, 0]))
cfg.fallbackcolor = NoSave(ConfigIP(default=[0, 176, 176, 192]))
cfg.notavailablecolor = NoSave(ConfigIP(default=[0, 94, 94, 94]))
cfg.selector_vertical = ConfigSelection(default="both", choices=[("both", _("both")), ("left", _("left only")), ("right", _("right only")), ("no", _("none"))])
cfg.oopera_scale = ConfigSelection(default="standard", choices=[("fullhd", _("FullHD")), ("standard", _("Standard"))])
cfg.altwin = ConfigYesNo(default=False)

XML_NAME = "PLi-FullHD_Pars.xml"
XML_FILE = resolveFilename(SCOPE_CONFIG, XML_NAME)
BACKUP = "/tmp/skintmp.xml"
OPERA_INI_PATH = "/usr/local/OpenOpera/home/opera.ini"

reload_skin_on_start = True

def colorText(color, text):
    color = int(skin.parseColor(color).argb())
    return "\\c%08x%s\\C" % (color, text)

class ModifyPLiFullHD(Screen, ConfigListScreen):
	skin = """
	<screen name="ModifyPLiFullHD" position="center,center" size="610,323" title="Modify PLi-FullHD - setup font and colors" backgroundColor="#31000000">
		<widget name="config" position="10,10" size="590,250" zPosition="1" backgroundColor="#31000000" scrollbarMode="showOnDemand"/>
		<ePixmap pixmap="skin_default/div-h.png" position="5,288" zPosition="2" size="600,2"/>
		<widget name="key_red"   position="005,294" zPosition="2" size="150,28" valign="center" halign="center" font="Regular;22" foregroundColor="red" transparent="1"/>
		<widget name="key_green" position="155,294" zPosition="2" size="150,28" valign="center" halign="center" font="Regular;22" foregroundColor="green" transparent="1"/>
		<widget name="key_yellow" position="305,294" zPosition="2" size="150,28" valign="center" halign="center" font="Regular;22" foregroundColor="yellow" transparent="1"/>
		<widget name="key_blue"  position="455,294" zPosition="2" size="150,28" valign="center" halign="center" font="Regular;22" foregroundColor="blue" transparent="1"/>
		<widget name="info" position="5,262" size="600,25" font="Regular;20" halign="center" transparent="1"/>
	</screen>"""

	def __init__(self, session, selected=None, show_apply=False):
		Screen.__init__(self, session)
		self.session = session
		self.menuSelectedIndex = selected
		self.withApply = show_apply

		choicelist = self.readFonts()
		cfg.font = NoSave(ConfigSelection(default="LiberationSans-Regular.ttf", choices=choicelist))

		self.list = []
		self.onChangedEntry = []

		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.changedEntry)

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"cancel": self.keyCancel,
				"red": self.keyCancel,
				"green": self.keySave,
				"yellow": self.applyChanges,
				"blue": self.showFileOptions,
			}, -2)

		self["key_green"] = Label(_("Ok"))
		self["key_red"] = Label(_("Cancel"))
		self["key_yellow"] = Label(_("Apply"))
		self["key_blue"] = Label(_("Options"))
		self["info"]= Label()

		self.wrong_xml = False
		self.selectionChoiceBox = 0

		self.titleText = _("Modify PLi-FullHD - setup font and colors") + _(" - v.%s") % VERSION

		self.current_skin = config.skin.primary_skin.value.split('/')[0]
		cfg.skin.value = self.current_skin

		operaScale = self.get_opera_scale()
		if operaScale:
			cfg.oopera_scale.value = operaScale

		self.onShown.append(self.testSkin)

	def testSkin(self):
		self.setTitle(self.titleText)

		def testSkinCallback(choice):
			self.close()
		if self.current_skin in ("PLi-FullHD", "PLi-FullNightHD", "PLi-HD1"):
			self.loadMenu()
		else:
			self.session.openWithCallback(	testSkinCallback,
							MessageBox,
							_("Plugin can be run under skins 'PLi-FullHD', 'PLi-FullNightHD' or 'PLiHD1' only!"),
							type=MessageBox.TYPE_INFO, timeout=4)
			self.close()

	def readFonts(self):
		path = resolveFilename(SCOPE_FONTS)
		return [file.replace(path, "") for file in sorted(glob.glob(path + "*.ttf"))]

	def loadMenu(self):
		self.showButtons()

		self["info"].setText("")
		self.setSkinPath()

		if self.testFile(XML_FILE):
			if self.isParseable():
				if not self.withApply:
					self.backupParseFile(XML_FILE)
				cfg.font.value = self.parseFont()
				self.parseColors()
			else:
				self["info"].setText(_("!!! Invalid format: %s, not used !!!") % XML_NAME)
		else:
			self["info"].setText(_("Was created new config file, restart for apply."))
			self.createDefaultCfgFile(cfg.skin.value)
			if not self.withApply:
				self.backupParseFile(XML_FILE)

		self.skin_enabled = _("Use modify skin")
		self.skin_name = _("Skin")
		self.loadConfig()

	def loadConfig(self):
		self.list = []
		self.list.append((self.skin_enabled, cfg.enabled))
		if cfg.enabled.value:
			self.list.append((self.skin_name, cfg.skin))
			self.list.append((_("Regular font"), cfg.font))
			self.list.append((_("Top color  (a,r,g,b)"), cfg.toptemplatecolor))
			self.list.append((_("Selector color  (a,r,g,b)"), cfg.selectorcolor))
			self.list.append((_("Bottom color  (a,r,g,b)"), cfg.basictemplatecolor))
			self.list.append((_("Vertical selector's lines"), cfg.selector_vertical))
			self.list.append((colorText("selectedFG", _("SelectedFG color  (a,r,g,b)")), cfg.selectedfgcolor))
			self.list.append((colorText("selectedFGEvent", _("SelectedFGEvent color  (a,r,g,b)")), cfg.selectedfgeventcolor))
			self.list.append((colorText("secondFG", _("SecondFG color  (a,r,g,b)")), cfg.secondfgcolor))
			self.list.append((colorText("yellow", _("Yellow color  (a,r,g,b)")), cfg.yellowcolor))
			self.list.append((colorText("yellowsoft", _("Yellowsoft color  (a,r,g,b)")), cfg.yellowsoftcolor))
			self.list.append((colorText("transponderinfo", _("TransponderInfo color  (a,r,g,b)")), cfg.transponderinfocolor))
			self.list.append((colorText("red", _("Red color  (a,r,g,b)")), cfg.redcolor))
			self.list.append((colorText("grey", _("Grey color  (a,r,g,b)")), cfg.greycolor))
			self.list.append((colorText("darkgrey", _("Darkgrey color  (a,r,g,b)")), cfg.darkgreycolor))
			self.list.append((colorText("fallback", _("Fallback color  (a,r,g,b)")), cfg.fallbackcolor))
			self.list.append((colorText("notavailable", _("Notavailable color  (a,r,g,b)")), cfg.notavailablecolor))
			self.list.append((_("Background color  (a,r,g,b)"), cfg.backgroundcolor))
			self.list.append((_("Black color  (a,r,g,b)"), cfg.blackcolor))
			if cfg.skin.value in ("PLi-FullHD", "PLi-FullNightHD"):
				self.list.append((_("Alternative windows border"), cfg.altwin))
			if self.get_opera_scale():
				self.list.append((_("OpenOpera scale for skin"), cfg.oopera_scale))

		self["config"].list = self.list
		if self.menuSelectedIndex:
			self["config"].setCurrentIndex(self.menuSelectedIndex)

	def showButtons(self):
		if self.withApply:
			self["key_yellow"].show()
		else:
			self["key_yellow"].hide()

	def changedEntry(self):
		self["key_yellow"].show()
		if self["config"].getCurrent()[0] in (self.skin_name, self.skin_enabled):
			self.loadMenu()

	def setSkinPath(self):
		global XML_NAME, XML_FILE
		XML_NAME = "PLi-FullHD_Pars.xml"
		if cfg.skin.value == "PLi-HD1":
			XML_NAME = "PLi-HD1_Pars.xml"
		elif cfg.skin.value == "PLi-FullNightHD":
			XML_NAME = "PLi-FullNightHD_Pars.xml"
		XML_FILE = resolveFilename(SCOPE_CONFIG, XML_NAME)

	def testFile(self, name):
		try:
			fi = open(name, "r")
		except:
			return False
		else:
			fi.close()
			return True

	def saveParametersToFile(self):
		colors = ["#" + value for value in self.getColorsFromCfg()]
		self.writeToFile(*colors)

	def parseFont(self):
		root = ET.parse(XML_FILE).getroot()
		fonts = root.find('fonts')
		for font in fonts:
			name = font.attrib.get('name', None)
			if name == "Regular":
				filename = font.attrib.get('filename', None)
				if filename:
					return filename
		return "nmsbd.ttf"

	def parseColors(self):
		root = ET.parse(XML_FILE).getroot()
		colors = root.find('colors')

		colorConfig = {
			"toptemplatecolor": cfg.toptemplatecolor,
			"basictemplatecolor": cfg.basictemplatecolor,
			"selectorcolor": cfg.selectorcolor,
			"transponderinfo": cfg.transponderinfocolor,
			"selectedFG": cfg.selectedfgcolor,
			"selectedFGEvent": cfg.selectedfgeventcolor,
			"yellow": cfg.yellowcolor,
			"yellowsoft": cfg.yellowsoftcolor,
			"red": cfg.redcolor,
			"grey": cfg.greycolor,
			"darkgrey": cfg.darkgreycolor,
			"secondFG": cfg.secondfgcolor,
			"fallback": cfg.fallbackcolor,
			"notavailable": cfg.notavailablecolor,
			"background": cfg.backgroundcolor,
			"black": cfg.blackcolor,
		}
		for color in colors:
			configItem = colorConfig.get(color.attrib.get("name"))
			value = color.attrib.get("value")

			if configItem is not None and value:
				configItem.value = self.map(value.lstrip("#"))

	def map(self, colorstring):
		return [int(colorstring[0:2], 16), int(colorstring[2:4], 16), int(colorstring[4:6], 16), int(colorstring[6:8], 16)]

	def getColorsFromCfg(self):
		toptemplate = self.l2h(cfg.toptemplatecolor.value)
		basictemplate = self.l2h(cfg.basictemplatecolor.value)
		selector = self.l2h(cfg.selectorcolor.value)
		transponderinfo = self.l2h(cfg.transponderinfocolor.value)
		selectedfg = self.l2h(cfg.selectedfgcolor.value)
		selectedfgevent = self.l2h(cfg.selectedfgeventcolor.value)
		yellow = self.l2h(cfg.yellowcolor.value)
		yellowsoft = self.l2h(cfg.yellowsoftcolor.value)
		red = self.l2h(cfg.redcolor.value)
		grey = self.l2h(cfg.greycolor.value)
		darkgrey = self.l2h(cfg.darkgreycolor.value)
		secondfg = self.l2h(cfg.secondfgcolor.value)
		fallback = self.l2h(cfg.fallbackcolor.value)
		notavailable = self.l2h(cfg.notavailablecolor.value)
		background = self.l2h(cfg.backgroundcolor.value)
		black = self.l2h(cfg.blackcolor.value)

		return toptemplate, basictemplate, selector, transponderinfo, selectedfg, selectedfgevent, yellow, yellowsoft, red, grey, darkgrey, secondfg, fallback, notavailable, background, black

	def l2h(self, l):
		return "%02x%02x%02x%02x" % (l[0], l[1], l[2], l[3])

	def keySave(self):
		self.setSkinPath()
		self.saveParametersToFile()
		self.oopera_scale()
		if self["config"].isChanged() and self.current_skin == cfg.skin.value:
			self.saveConfig()
			restartbox = self.session.openWithCallback(self.applyCallback, MessageBox, _("Some screens could be in old colors still.\nDo you want to restart the GUI now?"))
			restartbox.setTitle(self.titleText)
		else:
			self.saveConfig()
			self.close()

	def applyCallback(self, answer):
		if answer:
			self.session.open(TryQuitMainloop, 3)
		self.close()

	def saveConfig(self):
		cfg.enabled.save()
		cfg.selector_vertical.save()
		cfg.altwin.save()

	def keyCancel(self):
		if self["config"].isChanged():
			restartbox = self.session.openWithCallback(self.cancelCallback, MessageBox, _("Really close without apply changes?"))
			restartbox.setTitle(self.titleText)
		else:
			self.close()

	def cancelCallback(self, answer):
		if answer:
			cfg.cancel()
			self.useBackupFile()
			self.applyChanges(recurse=False)

	def deleteParseFile(self, name):
		if self.testFile(name):
			os.unlink(name)
	def backupParseFile(self, name):
		if self.testFile(BACKUP):
			if  not self.withApply:
				os.unlink(BACKUP)
				shutil.copyfile(name, BACKUP)
				return True
			return False
		shutil.copyfile(name, BACKUP)
		return True
	def useBackupFile(self):
		if self.testFile(BACKUP):
			shutil.move(BACKUP, XML_FILE)

	def isParseable(self):
		try:
			root = ET.parse(XML_FILE).getroot()
		except:
			print("[ModifyPLiFullHD] ERROR - file %s corrupted ?" % XML_FILE)
			self.wrong_xml = True
			return False
		else:
			self.wrong_xml = False
			return True

	def applyChanges(self, recurse=True):
		if recurse:
			self.oopera_scale()
			self.setSkinPath()
			self.saveParametersToFile()
		self.reloadSkin()
		self.reloadChanellSelection()
		if recurse:
			self.close((self["config"].getCurrentIndex(), True))
		else:
			self.deleteParseFile(BACKUP)
			self.close()

	def oopera_scale(self):
		status = self.get_opera_scale()
		if status:
			if "fullhd" in cfg.oopera_scale.value and status == "standard" :
				os.system("sed -i 's/Scale=100/Scale=150/' %s" % OPERA_INI_PATH)
			elif "standard" in cfg.oopera_scale.value and status == "fullhd":
				os.system("sed -i 's/Scale=150/Scale=100/' %s" % OPERA_INI_PATH)

	def get_opera_scale(self):
		try:
			with open(OPERA_INI_PATH, "r") as fi:
				for line in fi:
					if "Scale=100" in line:
						return "standard"
					elif "Scale=150" in line:
						return "fullhd"
		except IOError:
			pass
		return None

	def reloadChanellSelection(self):
		import Screens

#		ChannelSelection = Screens.InfoBar.InfoBar.instance.servicelist
#		ChannelSelection.applySkin()
#		ChannelSelection.setMode()

		old = Screens.InfoBar.InfoBar.instance.servicelist
		history_pos = old.history_pos
		servicePathTV = old.servicePathTV
		servicePathRadio = old.servicePathRadio
		servicePath = old.servicePath
		history = old.history
		rootChanged = old.rootChanged
		startRoot = old.startRoot
		selectionNumber = old.selectionNumber
		mode = old.mode
		dopipzap = old.dopipzap
		pathChangeDisabled = old.pathChangeDisabled
		movemode = old.movemode
		showSatDetails = old.showSatDetails

		Screens.InfoBar.InfoBar.instance.servicelist = self.session.instantiateDialog(Screens.ChannelSelection.ChannelSelection)

		new = Screens.InfoBar.InfoBar.instance.servicelist
		new.servicePathTV = servicePathTV
		new.servicePathRadio = servicePathRadio
		new.servicePath = servicePath
		new.history = history
		new.rootChanged = rootChanged
		new.startRoot = startRoot
		new.selectionNumber = selectionNumber
		new.mode = mode
		new.dopipzap = dopipzap
		new.pathChangeDisabled = pathChangeDisabled
		new.movemode = movemode
		new.showSatDetails = showSatDetails
		new.history_pos = history_pos
		new.recallBouquetMode()

	def applyAutorun(self):
		self.disableAutorun()
		self.setSkinPath()
		if self.testFile(XML_FILE):
			if self.isParseable():
				self.reloadSkin()
		else:
			self.createDefaultCfgFile(cfg.skin.value)
			if self.isParseable():
				self.reloadSkin()

	def disableAutorun(self):
		global reload_skin_on_start
		reload_skin_on_start = False

	def reloadSkin(self):
		path = os.path.dirname(XML_FILE) + "/"
		print("[ModifyPLiFullHD] parsing %s" % XML_FILE)

		# remove disabled items in plugin's setup from xml before reloading skin
		root = ET.parse(XML_FILE).getroot()
		windowstyle = root.find('windowstyle')
		for borderset in windowstyle.findall("borderset"):
			for pixmap in borderset.findall("pixmap"):
				if borderset.attrib.get("name", None) == "bsListboxEntry":
					if pixmap.attrib.get("pos") == "bpLeft":
						if cfg.selector_vertical.value in ("no", "right"):
							borderset.remove(pixmap)
					if pixmap.attrib.get("pos") ==  "bpRight":
						if cfg.selector_vertical.value in ("no", "left"):
							borderset.remove(pixmap)
		# call reload skin
		try:
			skin.loadSingleSkinData(enigma.getDesktop(0), root, path)
			print("[ModifyPLiFullHD] skin reload - old skin code")
		except TypeError:
			skin.loadSingleSkinData(enigma.getDesktop(0), skin.GUI_SKIN_ID, root, path)
			print("[ModifyPLiFullHD] skin reload - new skin code")
		for elem in root:
			if elem.tag == 'screen':
				name = elem.attrib.get('name', None)
				if name:
					sid = elem.attrib.get('id', None)
					if sid and (sid != skin.display_skin_id):
						elem.clear()
						continue
					if name in skin.dom_screens:
						skin.dom_screens[name][0].clear()
					skin.dom_screens[name] = (elem, path)
				else:
					elem.clear()
			else:
				elem.clear()

	def line(self, name):
		return "border/%s.png" % name

	def createDefaultCfgFile(self, typ=""):
		if typ == "PLi-FullNightHD":
			toptemplatecolor = "#000D0F16"
			basictemplatecolor = "#00000000"
			selectorcolor = "#06303240"
			transponderinfo = "#00f0f0f0"
			selectedFG = "#00fcc000"
			selectedFGEvent = "#00CCAC68"
			yellow = "#00F9C731"
			yellowsoft = "#00CCAC68"
			secondFG = "#00F9C731"
			red = "#00ff4a3c"
			grey = "#00aaaaaa"
			darkgrey = "#00555555"
			fallback = "#00b0b0c0"
			notavailable = "#005e5e5e"
			background = "#00000000"
			black = "#00000000"
		else:
			toptemplatecolor = "#00000014"
			basictemplatecolor = "#00000010"
			selectorcolor = "#00000020"
			transponderinfo = "#00808080"
			selectedFG = "#00c8aa40"
			selectedFGEvent = "#00f0f0f0"
			yellow = "#00c8aa40"
			yellowsoft = "#00CCAC68"
			secondFG = "#00c8aa40"
			red = "#00fa4010"
			grey = "#00aaaaaa"
			darkgrey = "#00555555"
			fallback = "#00a8a8c0"
			notavailable = "#005e5e5e"
			background = "#00000000"
			black = "#00000000"

		if typ == "fah":
			toptemplatecolor = "#00001414"
			basictemplatecolor = "#00001010"
			selectorcolor = "#00001414"
			transponderinfo = "#00b0b080"
			selectedFG = "#00dcc050"
			yellow = "#00dcc050"
			secondFG = "#00dcc050"
		if typ == "purple":
			toptemplatecolor = "#001e001e"
			basictemplatecolor = "#00140014"
			selectorcolor = "#001e001e"
			transponderinfo = "#00b0b080"
			selectedFG = "#00dcc050"
			yellow = "#00dcc050"
			secondFG = "#00dcc050"
		if typ == "violet":
			toptemplatecolor = "#000c001e"
			basictemplatecolor = "#000a0014"
			selectorcolor = "#0014001e"
			transponderinfo = "#00b0b080"
			selectedFG = "#00dcc050"
			yellow = "#00dcc050"
			secondFG = "#00dcc050"
		if typ == "grey" or typ == "grey2":
			toptemplatecolor = "#001c1c1c"
			basictemplatecolor = "#00181818"
			selectorcolor = "#001c1c1c"
			if typ == "grey":
				transponderinfo = "#00a0a080"
				selectedFG = "#00dcc050"
				yellow = "#00dcc050"
				secondFG = "#00dcc050"
			if typ == "grey2":
				transponderinfo = "#00b0b0b0"
				selectedFG = "#00f0b140"
				yellow = "#00f0b140"
				secondFG = "#00f0b140"
		if typ == "blueclass":
			toptemplatecolor = "#00000030"
			basictemplatecolor = "#00000020"
			selectorcolor = "#00000030"
			transponderinfo = "#000090f0"
			selectedFG = "#00fcc000"
			yellow = "#00ffc000"
			secondFG = "#00fcc000"

		self.writeToFile(toptemplatecolor, basictemplatecolor, selectorcolor, transponderinfo, selectedFG, selectedFGEvent, yellow, yellowsoft, red, grey, darkgrey, secondFG, fallback, notavailable, background, black)

	def writeToFile(self, toptemplatecolor, basictemplatecolor, selectorcolor, transponderinfo, selectedFG, selectedFGEvent, yellow, yellowsoft, red, grey, darkgrey, secondFG, fallback, notavailable, background, black):
		def indent(elem, level=0):
			i = "\n" + level*"  "
			if len(elem):
				if not elem.text or not elem.text.strip():
					elem.text = i + "  "
				if not elem.tail or not elem.tail.strip():
					elem.tail = i
				for elem in elem:
					indent(elem, level+1)
				if not elem.tail or not elem.tail.strip():
					elem.tail = i
			else:
				if level and (not elem.tail or not elem.tail.strip()):
					elem.tail = i

		root = ET.Element('skin')

		fonts = ET.SubElement(root, 'fonts')
		ET.SubElement(fonts, 'font', filename="%s" % cfg.font.value, name="Regular", scale="100")

		colors = ET.SubElement(root, 'colors')
		ET.SubElement(colors, 'color', name="toptemplatecolor", value="%s" % toptemplatecolor)
		ET.SubElement(colors, 'color', name="basictemplatecolor", value="%s" % basictemplatecolor)
		ET.SubElement(colors, 'color', name="selectorcolor", value="%s" % selectorcolor)
		ET.SubElement(colors, 'color', name="transponderinfo", value="%s" % transponderinfo)
		ET.SubElement(colors, 'color', name="selectedFG", value="%s" % selectedFG)
		ET.SubElement(colors, 'color', name="selectedFGEvent", value="%s" % selectedFGEvent)
		ET.SubElement(colors, 'color', name="yellow", value="%s" % yellow)
		ET.SubElement(colors, 'color', name="yellowsoft", value="%s" % yellowsoft)
		ET.SubElement(colors, 'color', name="red", value="%s" % red)
		ET.SubElement(colors, 'color', name="grey", value="%s" % grey)
		ET.SubElement(colors, 'color', name="darkgrey", value="%s" % darkgrey)
		ET.SubElement(colors, 'color', name="secondFG", value="%s" % secondFG)
		ET.SubElement(colors, 'color', name="fallback", value="%s" % fallback)
		ET.SubElement(colors, 'color', name="notavailable", value="%s" % notavailable)
		ET.SubElement(colors, 'color', name="background", value="%s" % background)
		ET.SubElement(colors, 'color', name="black", value="%s" % black)

		windowstyle = ET.SubElement(root, 'windowstyle', id="0", type="skinned")
		ET.SubElement(windowstyle, 'title', offset="20,6", font="Regular;26")
		ET.SubElement(windowstyle, 'color', name="Background", color="background")
		ET.SubElement(windowstyle, 'color', name="LabelForeground", color="foreground")
		ET.SubElement(windowstyle, 'color', name="ListboxBackground", color="background")
		ET.SubElement(windowstyle, 'color', name="ListboxForeground", color="foreground")
		ET.SubElement(windowstyle, 'color', name="ListboxSelectedBackground", color="selectorcolor")
		ET.SubElement(windowstyle, 'color', name="ListboxSelectedForeground", color="selectedFG")
		ET.SubElement(windowstyle, 'color', name="ListboxMarkedBackground", color="un40a0aa0")
		ET.SubElement(windowstyle, 'color', name="ListboxMarkedForeground", color="red")
		ET.SubElement(windowstyle, 'color', name="ListboxMarkedAndSelectedBackground", color="un4a00a0a")
		ET.SubElement(windowstyle, 'color', name="ListboxMarkedAndSelectedForeground", color="red")
		ET.SubElement(windowstyle, 'color', name="WindowTitleForeground", color="foreground")
		ET.SubElement(windowstyle, 'color', name="WindowTitleBackground", color="background")

		bsWinPath = "window"
		if self.current_skin == "PLi-HD1": # HD1 using HD bswindow pictures
			bsWinPath = "PLi-HD/" + bsWinPath
		elif cfg.altwin.value: # alternate window borders for FullHD skins
			bsWinPath = plugin_path + "/win2k/"

		bswindow = ET.SubElement(windowstyle, 'borderset', name="bsWindow")
		ET.SubElement(bswindow, 'pixmap', filename="%s/top_left_corner.png" % bsWinPath, pos="bpTopLeft")
		ET.SubElement(bswindow, 'pixmap', filename="%s/top_edge.png" % bsWinPath, pos="bpTop")
		ET.SubElement(bswindow, 'pixmap', filename="%s/top_right_corner.png" % bsWinPath, pos="bpTopRight")
		ET.SubElement(bswindow, 'pixmap', filename="%s/left_edge.png" % bsWinPath, pos="bpLeft")
		ET.SubElement(bswindow, 'pixmap', filename="%s/right_edge.png" % bsWinPath, pos="bpRight")
		ET.SubElement(bswindow, 'pixmap', filename="%s/bottom_left_corner.png" % bsWinPath, pos="bpBottomLeft")
		ET.SubElement(bswindow, 'pixmap', filename="%s/bottom_edge.png" % bsWinPath, pos="bpBottom")
		ET.SubElement(bswindow, 'pixmap', filename="%s/bottom_right_corner.png" % bsWinPath, pos="bpBottomRight")

		bslistboxentry = ET.SubElement(windowstyle, 'borderset', name="bsListboxEntry")
		ET.SubElement(bslistboxentry, 'pixmap', filename=self.line("line"), pos="bpTop")
		ET.SubElement(bslistboxentry, 'pixmap', filename=self.line("line"), pos="bpBottom")
		ET.SubElement(bslistboxentry, 'pixmap', filename=self.line("vline"), pos="bpLeft")
		ET.SubElement(bslistboxentry, 'pixmap', filename=self.line("vline"), pos="bpRight")

		indent(root)
		et = ET.ElementTree(root)
		fo = open(XML_FILE, "wb")
		et.write(fo, encoding='utf-8', xml_declaration=None, default_namespace=None, method="xml")
		self.wrong_xml = False

	def showFileOptions(self):
		menu = []
		if cfg.skin.value in ("PLi-HD1", "PLi-FullHD"):
			menu.append((_("Create new file with default values"), 100, ""))
		elif cfg.skin.value == "PLi-FullNightHD":
			menu.append((_("Create new file with default values"), 200, ""))
		menu.append((_("Save current parameters"), 1))
		menu.append((_("Delete file with parameters and close plugin"), 2, ""))
		if cfg.skin.value in ("PLi-HD1", "PLi-FullHD", "PLi-FullNightHD"):
			menu.append((_("Create new \"%s\" file") % "F&H", 3, ""))
			menu.append((_("Create new \"%s\" file") % "Purple", 4, ""))
			menu.append((_("Create new \"%s\" file") % "Grey", 5, ""))
			menu.append((_("Create new \"%s\" file") % "Grey 2", 6, ""))
			menu.append((_("Create new \"%s\" file") % "Violet", 7, ""))
			menu.append((_("Create new \"%s\" file") % "Blue Classic", 10, ""))

		menu.append((_("Font sizes table"), 20, ""))
		selection = menu.index(self.selectionChoiceBox) if self.selectionChoiceBox in menu else 0
		self.session.openWithCallback(self.fileOptionsCallback, ChoiceBox, title=_("Operations with configuration file"), list=menu, selection=selection)

	def fileOptionsCallback(self, choice):
		if choice is None:
			return

		index = self["config"].getCurrentIndex()
		self.selectionChoiceBox = choice
		selected = int(choice[1])

		if selected == 100:
			self.createDefaultCfgFile()
			self.close((index, True))
		elif selected == 1:
			self.saveParametersToFile()
		elif selected == 2:
			self.deleteParseFile(XML_FILE)
			self.close()
		elif selected == 3:
			self.createDefaultCfgFile("fah")
			self.close((index, True))
		elif selected == 4:
			self.createDefaultCfgFile("purple")
			self.close((index, True))
		elif selected == 5:
			self.createDefaultCfgFile("grey")
			self.close((index, True))
		elif selected == 6:
			self.createDefaultCfgFile("grey2")
			self.close((index, True))
		elif selected == 7:
			self.createDefaultCfgFile("violet")
			self.close((index, True))
		elif selected == 10:
			self.createDefaultCfgFile("blueclass")
			self.close((index, True))
		elif selected == 200:
			self.createDefaultCfgFile("PLi-FullNightHD")
			self.close((index, True))
		elif selected == 20:
			self.session.open(ModifyPLiFullHDFontInfo)
		else:
			return


# not used, may be for future:
	def colorDict(self):
		# 2 lines to init
		self.newColors = {}
		self.newColorsKeys = self.newColors.keys()

		toptemplatecolor, basictemplatecolor, selectorcolor, transponderinfo, selectedFG, selectedFGEvent, yellow, yellowsoft, red, grey, darkgrey, secondFG, fallback, notavailable, background, black = self.getColorsFromCfg()
		self.newColors = {
			'toptemplatecolor': toptemplatecolor,
			'basictemplatecolor': basictemplatecolor,
			'selectorcolor': selectorcolor,
			'transponderinfo': transponderinfo,
			'selectedFG': selectedFG,
			'selectedFGEvent': selectedFGEvent,
			'yellow': yellow,
			'yellowsoft': yellowsoft,
			'red': red,
			'grey': grey,
			'darkgrey': darkgrey,
			'secondFG': secondFG,
			'fallback': fallback,
			'notavailable': notavailable,
			'background': background,
			'black': black
		}
		self.newColorsKeys = self.newColors.keys()

	def changeColorsOnline(self):
		self.setSkinPath()
		self.saveParametersToFile()
		import skin
		import enigma
		self.colorDict()
		for n in skin.colorNames:
			if n in self.newColors.keys():
#				skin.colorNames[n] = enigma.gRGB(int(self.newColors[n], 0x10))
				skin.colorNames[n] = skin.parseColor("#%s" % self.newColors[n])
###

modifyskin = ModifyPLiFullHD(Screen)

class ModifyPLiFullHDFontInfo(Screen, ConfigListScreen):
	skin = """
	<screen name="ModifyPLiFullHDFontInfo" position="center,center" size="610,520" title="Modify PLi-FullHD - font info" backgroundColor="#31000000">
		<widget name="config" position="5,2" size="600,25"/>
		<widget name="info" position="20,29" size="600,18" font="Regular;16" halign="left" transparent="1"/>
		<ePixmap pixmap="skin_default/div-h.png" position="5,48" zPosition="2" size="600,2"/>
		<widget name="fontsinfo" position="20,53" size="590,440" font="Regular;19" zPosition="1" backgroundColor="#31000000" scrollbarMode="showOnDemand"/>
		<ePixmap pixmap="skin_default/div-h.png" position="5,493" zPosition="2" size="600,2"/>
		<widget name="key_red"   position="005,495" zPosition="2" size="150,25" valign="center" halign="center" font="Regular;22" foregroundColor="red" transparent="1"/>
		<widget name="key_green" position="155,495" zPosition="2" size="150,25" valign="center" halign="center" font="Regular;22" foregroundColor="green" transparent="1"/>
		<widget name="key_yellow" position="305,495" zPosition="2" size="150,25" valign="center" halign="center" font="Regular;22" foregroundColor="yellow" transparent="1"/>
		<widget name="key_blue"  position="455,495" zPosition="2" size="150,25" valign="center" halign="center" font="Regular;22" foregroundColor="blue" transparent="1"/>
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.title = _("Modify PLi-FullHD font info")

		### do not remove self["tmp"] !!!
		self["tmp"] = Label("")
		###

		choicelist = self.readFonts()
		config.plugins.ModifyPLiFullHD.fonts = NoSave(ConfigSelection(default=choicelist[0], choices=choicelist))

		self["info"] = Label(_("Font size / line height (px)"))
		self["fontsinfo"] = Label()

		self.FontInfoCfg = [(_("Select font"), config.plugins.ModifyPLiFullHD.fonts)]

		ConfigListScreen.__init__(self, self.FontInfoCfg, session=session, on_change=self.displayValues)

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "DirectionActions"],
			{
				"cancel": self.close,
				"red": self.close,
			}, -2)

		self["key_red"] = Label(_("Cancel"))
		self.onLayoutFinish.append(self.displayValues)

	def displayValues(self):
		family = config.plugins.ModifyPLiFullHD.fonts.value.split(',')[0]
		self["tmp"].instance.setNoWrap(1)
		self["tmp"].setText("W")
		info = ""
		for h in range(1, 21):
			info += ("%02d / %02d") % (h, self.lineHeight(h, family)) + "\t"
			info += ("%02d / %02d") % (h + 20, self.lineHeight(h + 20, family)) + "\t"
			info += ("%02d / %02d") % (h + 40, self.lineHeight(h + 40, family)) + "\t"
			info += ("%02d / %02d") % (h + 60, self.lineHeight(h + 60, family)) + "\n"
		self["fontsinfo"].setText(info)

	def lineHeight(self, size, family):
		fnt = enigma.gFont(family, size)
		self["tmp"].instance.setFont(fnt)
		return self["tmp"].instance.calculateSize().height()

	def readFonts(self):
		path = config.skin.primary_skin.value.split('/')[0]
		if path == ".":
			skin = resolveFilename(SCOPE_CURRENT_SKIN, "skin_default.xml")
		else:
			skin = resolveFilename(SCOPE_CURRENT_SKIN, config.skin.primary_skin.value)
		root = ET.parse(skin).getroot()
		fonts = root.find('fonts')
		list = []
		for font in fonts.findall('font'):
			list.append(("%s, %s") % (font.attrib.get('name', None), font.attrib.get('filename', None)))
		return list
