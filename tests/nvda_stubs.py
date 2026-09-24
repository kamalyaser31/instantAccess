"""Load real add-on modules with isolated NVDA/wx and Windows input test doubles."""

import builtins
import importlib
from pathlib import Path
import sys
import types
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
builtins._ = lambda text: text


def stub(name, **attrs):
	mod = types.ModuleType(name)
	mod.__dict__.update(attrs)
	sys.modules[name] = mod
	return mod


stub("addonHandler", initTranslation=lambda: None)
wx = stub(
	"wx",
	Dialog=object,
	IsMainThread=lambda: True,
	YES=1,
	NO=0,
	YES_NO=2,
	ICON_QUESTION=4,
	OK=8,
	ICON_ERROR=16,
)
pending = []
wx.CallAfter = lambda fn, *a, **kw: pending.append((fn, a, kw))
gui = stub("gui", messageBox=lambda *a, **kw: wx.NO, guiHelper=Mock(), nvdaControls=Mock())
stub("gui.settingsDialogs", SettingsPanel=object)
gui.settingsDialogs = types.SimpleNamespace(NVDASettingsDialog=types.SimpleNamespace(categoryClasses=[]))
api = stub("api", copyToClip=lambda *a, **kw: True)
stub("ui", message=lambda *a: None)
stub("inputCore", manager=Mock())
stub("keyboardHandler", KeyboardInputGesture=Mock())
stub("scriptHandler", script=lambda **kw: lambda f: f)
stub("tones", beep=lambda *a: None)


class BasePlugin:
	def __init__(self):
		pass

	def getScript(self, gesture):
		return None

	def clearGestureBindings(self):
		pass

	def bindGestures(self, gestures):
		pass


stub("globalPluginHandler", GlobalPlugin=BasePlugin)
gv = stub("globalVars", appArgs=types.SimpleNamespace(secure=True))
pkg = stub("auditcore")
pkg.__path__ = [str(ROOT / "addon/globalPlugins/core")]
# Import the actual vendored library, replacing only its OS backend.
backend = stub(
	"auditcore.keyboard._winkeyboard",
	init=lambda: None,
	press=Mock(),
	release=Mock(),
	type_unicode=Mock(),
	map_name=lambda name: [],
)
keyboard = importlib.import_module("auditcore.keyboard")
# The add-on supports Windows only; exercise that branch on Linux CI as well.
keyboard._platform = types.SimpleNamespace(system=lambda: "Windows")
io = importlib.import_module("auditcore.config_io")
cm = importlib.import_module("auditcore.config_manager")
ex = importlib.import_module("auditcore.executor")
dialogs = importlib.import_module("auditcore.item_dialog")
plugin = importlib.import_module("auditcore.plugin")
