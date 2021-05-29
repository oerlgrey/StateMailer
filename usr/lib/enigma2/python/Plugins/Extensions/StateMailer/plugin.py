# -*- coding: utf-8 -*-

#  StateMailer
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

from StateMailerBrowser import StateMailerBrowser
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from enigma import eTimer
from Components.config import config, configfile, ConfigSubsection, getConfigListEntry, ConfigSelection, ConfigText, ConfigYesNo, ConfigClock
from Components.ConfigList import ConfigListScreen
from os import path, environ
from Tools.Directories import fileExists, resolveFilename, SCOPE_LANGUAGE, SCOPE_PLUGINS
from Components.Language import language
import smtplib, gettext
from time import strftime, mktime
from datetime import datetime
from email.MIMEMultipart import MIMEMultipart

lang = language.getLanguage()
environ["LANGUAGE"] = lang[:2]
gettext.bindtextdomain("enigma2", resolveFilename(SCOPE_LANGUAGE))
gettext.textdomain("enigma2")
gettext.bindtextdomain("StateMailer", "%s%s" % (resolveFilename(SCOPE_PLUGINS), "Extensions/StateMailer/locale/"))

def _(txt):
	t = gettext.dgettext("StateMailer", txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t

def translateBlock(block):
	for x in TranslationHelper:
		if block.__contains__(x[0]):
			block = block.replace(x[0], x[1])
	return block

_session = None
state = "started"
subject = ""
daily = "started"
daily_timer = 0
errors = 0

config.plugins.StateMailer = ConfigSubsection()
config.plugins.StateMailer.activate = ConfigYesNo(default = False)

config.plugins.StateMailer.empty = ConfigSelection(default = "empty", choices = [
				("empty", _(" "))
				])

config.plugins.StateMailer.name = ConfigText(default = "")
config.plugins.StateMailer.submitter = ConfigText(default = "")
config.plugins.StateMailer.password = ConfigText(default = "")
config.plugins.StateMailer.smtp = ConfigText(default = "")
config.plugins.StateMailer.port = ConfigText(default = "")

config.plugins.StateMailer.security = ConfigSelection(default = "starttls", choices = [
				("starttls", _("starttls")),
				("ssl", _("ssl"))
				])

config.plugins.StateMailer.recipient = ConfigText(default = "")
config.plugins.StateMailer.cc = ConfigText(default = "")

config.plugins.StateMailer.dirfile = ConfigSelection(default = "file", choices = [
				("dir", _("Directory")),
				("file", _("File"))
				])

config.plugins.StateMailer.dir = ConfigText(default = "", fixed_size = False)
config.plugins.StateMailer.file = ConfigText(default = "")
				
config.plugins.StateMailer.exists = ConfigSelection(default = "exists", choices = [
				("exists", _("if exists")),
				("not-exist", _("if not exist"))
				])

config.plugins.StateMailer.checkInterval = ConfigSelection(default = "30", choices = [
				("15", _("15 sec")),
				("30", _("30 sec")),
				("60", _("1 min")),
				("120", _("2 min")),
				("300", _("5 min"))
				])

config.plugins.StateMailer.subService = ConfigText(default = "Dienst gestartet")
config.plugins.StateMailer.subAlarm = ConfigText(default = "Alarm!!!")
config.plugins.StateMailer.subSolved = ConfigText(default = "Problem behoben")
config.plugins.StateMailer.subTest = ConfigText(default = "tägliches Testmail")

config.plugins.StateMailer.dailymail = ConfigYesNo(default = False)
config.plugins.StateMailer.dailymailTime = ConfigClock(default = mktime((0, 0, 0, 20, 00, 0, 0, 0, 0)))

class StateMailer():
	def __init__(self):
		self.statetimer = eTimer()
		self.dailytimer = eTimer()
		self.retrytimer = eTimer()
		self.InternetAvailable = self.getInternetAvailable()

	def startSession(self, session):
		self.statetimer.callback.append(self.checkstate)
		self.dailytimer.callback.append(self.dailymail)
		self.retrytimer.callback.append(self.retryTransmit)
		self.checkstate()

	def checkstate(self):
		global state, subject
		if self.statetimer.isActive():
			self.statetimer.stop()
		timeout = max(15, int(config.plugins.StateMailer.checkInterval.value)) * 1000.0
		self.statetimer.start(int(timeout), True)
		if config.plugins.StateMailer.activate.value:
			if state == "started":
				subject = config.plugins.StateMailer.subService.value
				self.mailsender(subject)
				state = "standby"
			if state == "standby":
				if config.plugins.StateMailer.exists.value == "exists":
					if config.plugins.StateMailer.dirfile.value == "dir":
						if path.isdir(config.plugins.StateMailer.dir.value):
							subject = config.plugins.StateMailer.subAlarm.value
							self.mailsender(subject)
							state = "alarm"
					else:
						if fileExists(config.plugins.StateMailer.file.value):
							subject = config.plugins.StateMailer.subAlarm.value
							self.mailsender(subject)
							state = "alarm"
				else:
					if config.plugins.StateMailer.dirfile.value == "dir":
						if not path.isdir(config.plugins.StateMailer.dir.value):
							subject = config.plugins.StateMailer.subAlarm.value
							self.mailsender(subject)
							state = "alarm"
					else:
						if not fileExists(config.plugins.StateMailer.file.value):
							subject = config.plugins.StateMailer.subAlarm.value
							self.mailsender(subject)
							state = "alarm"
			if state == "alarm":
				if config.plugins.StateMailer.exists.value == "exists":
					if config.plugins.StateMailer.dirfile.value == "dir":
						if not path.isdir(config.plugins.StateMailer.dir.value):
							subject = config.plugins.StateMailer.subSolved.value
							self.mailsender(subject)
							state = "standby"
					else:
						if not fileExists(config.plugins.StateMailer.file.value):
							subject = config.plugins.StateMailer.subSolved.value
							self.mailsender(subject)
							state = "standby"
				else:
					if config.plugins.StateMailer.dirfile.value == "dir":
						if path.isdir(config.plugins.StateMailer.dir.value):
							subject = config.plugins.StateMailer.subSolved.value
							self.mailsender(subject)
							state = "standby"
					else:
						if fileExists(config.plugins.StateMailer.file.value):
							subject = config.plugins.StateMailer.subSolved.value
							self.mailsender(subject)
							state = "standby"
		else:
			state = "stopped"
		self.checkdailyTimer()

	def checkdailyTimer(self):
		global daily, daily_timer
		if config.plugins.StateMailer.dailymail.value:
			if daily == "started":
				if self.dailytimer.isActive():
					self.dailytimer.stop()
				now = datetime.now()
				now_hour = int(now.strftime("%H")) * 3600000
				now_min = int(now.strftime("%M")) * 60000
				now_time = now_hour + now_min
				daily_hour = int(config.plugins.StateMailer.dailymailTime.value[0]) * 3600000
				daily_min = int(config.plugins.StateMailer.dailymailTime.value[1]) * 60000
				daily_time = daily_hour + daily_min
				if daily_time > now_time:
					daily_timer = daily_time - now_time
				else:
					daily_timer = 86400000 - now_time + daily_time
				self.dailytimer.start(int(daily_timer), True)
				daily = "running"
		else:
			if self.dailytimer.isActive():
				self.dailytimer.stop()
			daily = "stopped"

	def dailymail(self):
		global daily, daily_timer, subject
		subject = config.plugins.StateMailer.subTest.value
		self.mailsender(subject)
		if not daily_timer == 86400000:
			daily_timer = 86400000
			self.dailytimer.changeInterval(int(daily_timer))

	def mailsender(self, subject):
		global errors
		if self.retrytimer.isActive():
			self.retrytimer.stop()
		if self.InternetAvailable:
			if errors == 0:
				sub = str(subject)
			elif errors == 1:
				sub = str(subject) + " (" + str(errors) + _(" Fehlversuch)")
			else:
				sub = str(subject) + " (" + str(errors) + _(" Fehlversuche)")
			name = config.plugins.StateMailer.name.value
			submitter = config.plugins.StateMailer.submitter.value
			recipient = [config.plugins.StateMailer.recipient.value]
			cc = [config.plugins.StateMailer.cc.value]
			receiver = recipient + cc
			smtp = config.plugins.StateMailer.smtp.value
			port = int(config.plugins.StateMailer.port.value)
			password = config.plugins.StateMailer.password.value
			try:
				msg = MIMEMultipart()
				msg['From'] = '%s <%s>' % (name, submitter)
				msg['To'] = ";".join(recipient)
				if not config.plugins.StateMailer.cc.value == "":
					msg['Cc'] = ";".join(cc)
				msg['Subject'] = sub.encode("iso-8859-1")
				if config.plugins.StateMailer.security.value == "starttls":
					server = smtplib.SMTP(smtp, port)
					server.ehlo()
					server.starttls()
				else:
					server = smtplib.SMTP_SSL(smtp, port)
				server.ehlo()
				server.login(submitter, password)
				if not config.plugins.StateMailer.cc.value == "":
					server.sendmail(submitter, receiver, msg.as_string())
				else:
					server.sendmail(submitter, recipient, msg.as_string())
				server.quit()
				errors = 0
				print "StateMailer: E-Mail was sent successfully."
			except:
				print "StateMailer: Sending E-Mail failed!"
				self.retrytimer.start(60000, True)
		else:
			print "StateMailer: Your box has no internet connection."
			self.retrytimer.start(60000, True)

	def retryTransmit(self):
		global subject, errors
		errors = int(errors) + 1
		self.mailsender(subject)

	def getInternetAvailable(self):
		import ping
		r = ping.doOne("8.8.8.8", 1.5)
		if r != None and r <= 1.5:
			return True
		else:
			return False

sMail = StateMailer()

def sessionstart(reason, **kwargs):
	global _session
	if reason == 0 and _session is None:
		_session = kwargs["session"]
		if _session:
			sMail.startSession(_session)

def main(session, **kwargs):
	try:
		session.open(StateMailerConfig)
	except:
		import traceback
		traceback.print_exc()

def Plugins(**kwargs):
	return [PluginDescriptor(where = [PluginDescriptor.WHERE_SESSIONSTART], fnc = sessionstart),
	PluginDescriptor(name = "StateMailer", description = _("StateMailer Settings"), where = PluginDescriptor.WHERE_PLUGINMENU, icon='plugin.png', fnc = main)]

class StateMailerConfig(ConfigListScreen, Screen):
	skin = """
			<screen name="StateMailerConfig" position="center,74" size="800,600">
				<widget name="config" position="20,12" size="760,510" itemHeight="30" font="Regular;20" scrollbarMode="showOnDemand" enableWrapAround="1" transparent="1"/>
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/StateMailer/images/red.png" position="20,543" size="140,40" alphatest="on"/>
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/StateMailer/images/green.png" position="165,543" size="140,40" alphatest="on"/>
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/StateMailer/images/yellow.png" position="310,543" size="140,40" alphatest="on"/>
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/StateMailer/images/blue.png" position="455,543" size="140,40" alphatest="on"/>
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/StateMailer/images/grey.png" position="675,543" size="50,40" alphatest="on"/>
				<ePixmap pixmap="/usr/lib/enigma2/python/Plugins/Extensions/StateMailer/images/grey.png" position="730,543" size="50,40" alphatest="on"/>
				<widget source="key_red" render="Label" position="20,543" size="140,40" backgroundColor="#9f1313" font="Regular;18" halign="center" valign="center" zPosition="1" transparent="1"/>
				<widget source="key_green" render="Label" position="165,543" size="140,40" backgroundColor="#1f771f" font="Regular;18" halign="center" valign="center" zPosition="1" transparent="1"/>
				<widget source="key_yellow" render="Label" position="310,543" size="140,40" backgroundColor="#a08500" font="Regular;18" halign="center" valign="center" zPosition="1" transparent="1"/>
				<widget source="key_blue" render="Label" position="455,543" size="140,40" backgroundColor="#18188b" font="Regular;18" halign="center" valign="center" zPosition="1" transparent="1"/>
				<eLabel text="OK " position="675,543" size="50,40" backgroundColor="#555555" font="Regular;18" halign="center" valign="center" zPosition="1" transparent="1" />
				<eLabel text="Exit " position="730,543" size="50,40" backgroundColor="#555555" font="Regular;18" halign="center" valign="center" zPosition="1" transparent="1" />
			</screen>
			"""

	def __init__(self, session, args = None):
		Screen.__init__(self, session)
		self.session = session
		Screen.setTitle(self, _("StateMailer Settings"))

		list = []
		ConfigListScreen.__init__(self, list)

		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ColorActions"],
		{
			"up": self.keyUp,
			"down": self.keyDown,
			"left": self.keyLeft,
			"right": self.keyRight,
			"red": self.exit,
			"green": self.save,
			"blue": self.sendTestmail,
			"yellow": self.clearCC,
			"cancel": self.exit,
			"ok": self.keyOK
		}, -2)

		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_("Save"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()

		self.timer = eTimer()
		self.timer.callback.append(self.updateMylist)
		self.onLayoutFinish.append(self.updateMylist)
		self.InternetAvailable = self.getInternetAvailable()

	def mylist(self):
		self.timer.start(100, True)

	def updateMylist(self):
		list = []
		list.append(getConfigListEntry(_("Activate StateMailer"), config.plugins.StateMailer.activate))
		if config.plugins.StateMailer.activate.value:
			list.append(getConfigListEntry(_("Submitter Settings:"), config.plugins.StateMailer.empty))
			list.append(getConfigListEntry(_("   Name"), config.plugins.StateMailer.name))
			list.append(getConfigListEntry(_("   E-Mail"), config.plugins.StateMailer.submitter))
			list.append(getConfigListEntry(_("   Password"), config.plugins.StateMailer.password))
			list.append(getConfigListEntry(_("   SMTP"), config.plugins.StateMailer.smtp))
			list.append(getConfigListEntry(_("   Port"), config.plugins.StateMailer.port))
			list.append(getConfigListEntry(_("   Security"), config.plugins.StateMailer.security))
			list.append(getConfigListEntry(_("Recipient Settings:"), config.plugins.StateMailer.empty))
			list.append(getConfigListEntry(_("   E-Mail"), config.plugins.StateMailer.recipient))
			list.append(getConfigListEntry(_("   CC"), config.plugins.StateMailer.cc))
			list.append(getConfigListEntry(_("File or Directory:"), config.plugins.StateMailer.dirfile))
			if config.plugins.StateMailer.dirfile.value == "dir":
				list.append(getConfigListEntry(_("   Directory"), config.plugins.StateMailer.dir))
			else:
				list.append(getConfigListEntry(_("   File"), config.plugins.StateMailer.file))
			list.append(getConfigListEntry(_("Alarm method"), config.plugins.StateMailer.exists))
			list.append(getConfigListEntry(_("Check interval"), config.plugins.StateMailer.checkInterval))
			list.append(getConfigListEntry(_("Send daily Testmail"), config.plugins.StateMailer.dailymail))
			if config.plugins.StateMailer.dailymail.value:
				list.append(getConfigListEntry(_("daily Testmail Time"), config.plugins.StateMailer.dailymailTime))
			else:
				list.append(getConfigListEntry("     ", config.plugins.StateMailer.empty))
			list.append(getConfigListEntry(_("Subject Settings:"), config.plugins.StateMailer.empty))
			list.append(getConfigListEntry(_("   Service started"), config.plugins.StateMailer.subService))
			list.append(getConfigListEntry(_("   Alarm"), config.plugins.StateMailer.subAlarm))
			list.append(getConfigListEntry(_("   Problem solved"), config.plugins.StateMailer.subSolved))
			list.append(getConfigListEntry(_("   daily Testmail"), config.plugins.StateMailer.subTest))

		self["config"].list = list
		self["config"].l.setList(list)
		self.setYellowText()
		self.setBlueText()

	def VirtualKeyBoardCallBack(self, callback):
		try:
			if callback:  
				self["config"].getCurrent()[1].value = callback
			else:
				pass
		except:
			pass

	def BrowserCallBack(self, callback):
		try:
			if callback:
				if config.plugins.StateMailer.dirfile.value == "dir":
					config.plugins.StateMailer.dir.value = callback
				else:
					config.plugins.StateMailer.file.value = callback
				self.mylist()
			else:
				pass
		except:
			pass

	def setYellowText(self):
		option = self["config"].getCurrent()[1]
		if option in (config.plugins.StateMailer.name, config.plugins.StateMailer.submitter, config.plugins.StateMailer.password, config.plugins.StateMailer.smtp, config.plugins.StateMailer.port, config.plugins.StateMailer.recipient, config.plugins.StateMailer.cc, config.plugins.StateMailer.subService, config.plugins.StateMailer.subAlarm, config.plugins.StateMailer.subSolved, config.plugins.StateMailer.subTest):
			if not option.value == "":
				self["key_yellow"].text = _("Delete entry")
			else:
				self["key_yellow"].text = ""
		else:
			self["key_yellow"].text = ""

	def setBlueText(self):
		if config.plugins.StateMailer.activate.value:
			self["key_blue"].text = _("Test E-Mail")
		else:
			self["key_blue"].text = ""

	def clearCC(self):
		option = self["config"].getCurrent()[1]
		if option in (config.plugins.StateMailer.name, config.plugins.StateMailer.submitter, config.plugins.StateMailer.password, config.plugins.StateMailer.smtp, config.plugins.StateMailer.port, config.plugins.StateMailer.recipient, config.plugins.StateMailer.cc, config.plugins.StateMailer.subService, config.plugins.StateMailer.subAlarm, config.plugins.StateMailer.subSolved, config.plugins.StateMailer.subTest):
			if not option.value == "":
				option.value = ""
				self.mylist()
		else:
			pass

	def sendTestmail(self):
		if config.plugins.StateMailer.activate.value:
			self.mailsender(_("Testmail"))

	def mailsender(self, subject):
		if self.InternetAvailable:
			name = config.plugins.StateMailer.name.value
			submitter = config.plugins.StateMailer.submitter.value
			recipient = [config.plugins.StateMailer.recipient.value]
			cc = [config.plugins.StateMailer.cc.value]
			receiver = recipient + cc
			smtp = config.plugins.StateMailer.smtp.value
			port = int(config.plugins.StateMailer.port.value)
			password = config.plugins.StateMailer.password.value
			try:
				msg = MIMEMultipart()
				msg['From'] = '%s <%s>' % (name, submitter)
				msg['To'] = ";".join(recipient)
				if not config.plugins.StateMailer.cc.value == "":
					msg['Cc'] = ";".join(cc)
				msg['Subject'] = subject.encode("iso-8859-1")
				if config.plugins.StateMailer.security.value == "starttls":
					server = smtplib.SMTP(smtp, port)
					server.ehlo()
					server.starttls()
				else:
					server = smtplib.SMTP_SSL(smtp, port)
				server.ehlo()
				server.login(submitter, password)
				if not config.plugins.StateMailer.cc.value == "":
					server.sendmail(submitter, receiver, msg.as_string())
				else:
					server.sendmail(submitter, recipient, msg.as_string())
				server.quit()
				self.session.open(MessageBox, _("E-Mail was sent successfully."), MessageBox.TYPE_INFO, timeout = 10)
			except:
				self.session.open(MessageBox, _("Sending E-Mail failed!\nPlease check your settings."), MessageBox.TYPE_INFO, timeout = 10)
		else:
			self.session.open(MessageBox, _("Your box has no internet connection.\nPlease solve the problem."), MessageBox.TYPE_INFO, timeout = 10)

	def keyOK(self):
		ConfigListScreen.keyOK(self)
		option = self["config"].getCurrent()[1]
		if option == config.plugins.StateMailer.dir:
			value = config.plugins.StateMailer.dirfile.value
			self.session.openWithCallback(self.BrowserCallBack, StateMailerBrowser, value = value)
		elif option == config.plugins.StateMailer.file:
			value = config.plugins.StateMailer.dirfile.value
			self.session.openWithCallback(self.BrowserCallBack, StateMailerBrowser, value = value)
		elif option == config.plugins.StateMailer.name:
			text = self["config"].getCurrent()[1].value
			title = _("Enter the submitter name:")
			self.session.openWithCallback(self.VirtualKeyBoardCallBack, VirtualKeyBoard, title = title, text = text)
			config.plugins.StateMailer.name.save()
		elif option == config.plugins.StateMailer.submitter:
			text = self["config"].getCurrent()[1].value
			title = _("Enter the submitter E-Mail address:")
			self.session.openWithCallback(self.VirtualKeyBoardCallBack, VirtualKeyBoard, title = title, text = text)
			config.plugins.StateMailer.submitter.save()
		elif option == config.plugins.StateMailer.password:
			text = self["config"].getCurrent()[1].value
			title = _("Enter the submitter password:")
			self.session.openWithCallback(self.VirtualKeyBoardCallBack, VirtualKeyBoard, title = title, text = text)
			config.plugins.StateMailer.password.save()
		elif option == config.plugins.StateMailer.smtp:
			text = self["config"].getCurrent()[1].value
			title = _("Enter the submitter SMTP:")
			self.session.openWithCallback(self.VirtualKeyBoardCallBack, VirtualKeyBoard, title = title, text = text)
			config.plugins.StateMailer.smtp.save()
		elif option == config.plugins.StateMailer.port:
			text = self["config"].getCurrent()[1].value
			title = _("Enter the submitter SMTP-Port:")
			self.session.openWithCallback(self.VirtualKeyBoardCallBack, VirtualKeyBoard, title = title, text = text)
			config.plugins.StateMailer.port.save()
		elif option == config.plugins.StateMailer.recipient:
			text = self["config"].getCurrent()[1].value
			title = _("Enter the recipient E-Mail address:")
			self.session.openWithCallback(self.VirtualKeyBoardCallBack, VirtualKeyBoard, title = title, text = text)
			config.plugins.StateMailer.recipient.save()
		elif option == config.plugins.StateMailer.cc:
			text = self["config"].getCurrent()[1].value
			title = _("Enter the CC E-Mail address:")
			self.session.openWithCallback(self.VirtualKeyBoardCallBack, VirtualKeyBoard, title = title, text = text)
			config.plugins.StateMailer.cc.save()
		elif option == config.plugins.StateMailer.subService:
			text = self["config"].getCurrent()[1].value
			title = _("Enter the subject:")
			self.session.openWithCallback(self.VirtualKeyBoardCallBack, VirtualKeyBoard, title = title, text = text)
			config.plugins.StateMailer.subService.save()
		elif option == config.plugins.StateMailer.subAlarm:
			text = self["config"].getCurrent()[1].value
			title = _("Enter the subject:")
			self.session.openWithCallback(self.VirtualKeyBoardCallBack, VirtualKeyBoard, title = title, text = text)
			config.plugins.StateMailer.subAlarm.save()
		elif option == config.plugins.StateMailer.subSolved:
			text = self["config"].getCurrent()[1].value
			title = _("Enter the subject:")
			self.session.openWithCallback(self.VirtualKeyBoardCallBack, VirtualKeyBoard, title = title, text = text)
			config.plugins.StateMailer.subSolved.save()
		elif option == config.plugins.StateMailer.subTest:
			text = self["config"].getCurrent()[1].value
			title = _("Enter the subject:")
			self.session.openWithCallback(self.VirtualKeyBoardCallBack, VirtualKeyBoard, title = title, text = text)
			config.plugins.StateMailer.subTest.save()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.mylist()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.mylist()

	def keyDown(self):
		self["config"].instance.moveSelection(self["config"].instance.moveDown)
		self.mylist()

	def keyUp(self):
		self["config"].instance.moveSelection(self["config"].instance.moveUp)
		self.mylist()

	def save(self):
		global state, daily
		if config.plugins.StateMailer.activate.value:
			state = "standby"
		else:
			state = "stopped"

		if config.plugins.StateMailer.dailymail.value:
			daily = "started"
		else:
			daily = "stopped"

		for x in self["config"].list:
			if len(x) > 1:
				x[1].save()
			else:
				pass

		configfile.save()
		self.close()

	def exit(self):
		askExit = self.session.openWithCallback(self.doExit, MessageBox,_("Do you really want to exit without saving?"), MessageBox.TYPE_YESNO)
		askExit.setTitle(_("Exit"))

	def doExit(self, answer):
		if answer is True:
			for x in self["config"].list:
				if len(x) > 1:
					x[1].cancel()
				else:
					pass

			self.close()
		else:
			self.mylist()

	def getInternetAvailable(self):
		import ping
		r = ping.doOne("8.8.8.8", 1.5)
		if r != None and r <= 1.5:
			return True
		else:
			return False
