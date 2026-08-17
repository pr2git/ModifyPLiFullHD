# for localized messages
from . import _
#################################################################################
#
#    Plugin for Enigma2
#    version:
#
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

from Plugins.Plugin import PluginDescriptor
from Components.config import config, ConfigSubsection, ConfigYesNo

config.plugins.ModifyPLiFullHD = ConfigSubsection()
config.plugins.ModifyPLiFullHD.enabled = ConfigYesNo(default=False)


def autostart(reason, **kwargs):
	from . import ui
	if reason == 0 and config.plugins.ModifyPLiFullHD.enabled.value and config.skin.primary_skin.value.split('/')[0] in ("PLi-FullHD", "PLi-FullNightHD", "PLi-HD1") and ui.reload_skin_on_start:
		ui.modifyskin.applyAutorun()

def main(session, **kwargs):
	from . import ui
	def recursive(answer=False):
		if answer:
			session.openWithCallback(recursive, ui.ModifyPLiFullHD, answer[0], answer[1])
	session.openWithCallback(recursive, ui.ModifyPLiFullHD)

def Plugins(path, **kwargs):
	global plugin_path
	plugin_path = path
	name = _("Modify PLi-FullHD")
	descr = _("Change regular font and colors in PLi FullHD/FullNightHD/HD1 skins")
	return [
		PluginDescriptor(name=name, description=descr, where=PluginDescriptor.WHERE_PLUGINMENU, icon='plugin.png', fnc=main),
		PluginDescriptor(name=name, description=descr, where=[PluginDescriptor.WHERE_SESSIONSTART], fnc=autostart),
	]
