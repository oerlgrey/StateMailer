# -*- coding: utf-8 -*-

#  StateMailer Browser
#
#  Coded by örlgrey
#  Based on openHDF image source code
#
#  This code is licensed under the Creative Commons 
#  Attribution-NonCommercial-ShareAlike 3.0 Unported 
#  License. To view a copy of this license, visit
#  http://creativecommons.org/licenses/by-nc-sa/3.0/ 
#  or send a letter to Creative Commons, 559 Nathan 
#  Abbott Way, Stanford, California 94305, USA.
#
#  If you think this license infringes any rights,
#  please contact me at ochzoetna@gmail.com

from Components.FileList import FileList
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText

class StateMailerBrowser(Screen):
	skin = """
			<screen name="StateMailerBrowser" position="center,74" size="800,600">
				<widget name="list" position="20,12" size="760,480" itemHeight="30" font="Regular;20" scrollbarMode="showOnDemand" enableWrapAround="1" transparent="1"/>
				<widget source="info" render="Label" position="20,510" size="760,28" font="Regular;20" noWrap="1" valign="center" transparent="1"/>
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/StateMailer/images/red.png" position="20,543" size="140,40" alphatest="on"/>
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/StateMailer/images/green.png" position="165,543" size="140,40" alphatest="on"/>
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/StateMailer/images/grey.png" position="675,543" size="50,40" alphatest="on"/>
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/StateMailer/images/grey.png" position="730,543" size="50,40" alphatest="on"/>
				<widget source="key_red" render="Label" position="20,543" size="140,40" backgroundColor="#9f1313" font="Regular;18" halign="center" valign="center" zPosition="1" transparent="1"/>
				<widget source="key_green" render="Label" position="165,543" size="140,40" backgroundColor="#1f771f" font="Regular;18" halign="center" valign="center" zPosition="1" transparent="1"/>
				<eLabel text="OK " position="675,543" size="50,40" backgroundColor="#555555" font="Regular;18" halign="center" valign="center" zPosition="1" transparent="1" />
				<eLabel text="Exit " position="730,543" size="50,40" backgroundColor="#555555" font="Regular;18" halign="center" valign="center" zPosition="1" transparent="1" />
			</screen>
			"""

	def __init__(self, session, value = ""):
		Screen.__init__(self, session)
		self.session = session
		Screen.setTitle(self, _("StateMailer Settings"))
		self["list"] = FileList("/", matchingPattern = "")

		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"],
		{
			"up": self.keyUp,
			"down": self.keyDown,
			"left": self.keyLeft,
			"right": self.keyRight,
			"green": self.save,
			"ok": self.keyOK,
			"red": self.exit,
			"cancel": self.exit
		}, -1)

		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_("Save"))
		self["info"] = StaticText()
		self.value = value

	def showInfo(self):
		currFolder = self["list"].getSelection()[0].rsplit("/", 1)[0]
		currFile = str(self["list"].getCurrentDirectory()) + str(self["list"].getFilename())
		if self.value == "dir":
			if self["list"].canDescent():
				self["info"].setText(currFolder)
			else:
				self["info"].setText("")
		else:
			if not self["list"].canDescent():
				self["info"].setText(currFile)
			else:
				self["info"].setText("")

	def keyLeft(self):
		self["list"].pageUp()
		self.showInfo()

	def keyRight(self):
		self["list"].pageDown()
		self.showInfo()

	def keyUp(self):
		self["list"].up()
		self.showInfo()

	def keyDown(self):
		self["list"].down()
		self.showInfo()

	def keyOK(self):
		if self["list"].canDescent():
			self["list"].descent()
		else:
			pass
		self.showInfo()

	def save(self):
		currFolder = self["list"].getSelection()[0].rsplit('/', 1)[0]
		currFile = str(self["list"].getCurrentDirectory()) + str(self["list"].getFilename())
		if self.value == "dir":
			if self["list"].canDescent():
				self.close(currFolder)
			else:
				pass
		else:
			if not self["list"].canDescent():
				self.close(currFile)
			else:
				pass
		return

	def exit(self):
		self.close(None)
		return
