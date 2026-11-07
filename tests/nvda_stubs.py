"""Load real add-on modules with isolated NVDA/wx and Windows input test doubles."""

import builtins
import importlib
import logging
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
class _StubMenu:
	def __init__(self, *a, **kw):
		pass
	def Append(self, *a, **kw):
		return Mock()
	def Destroy(self):
		pass


class _StubDialog:
	def __init__(self, *a, **kw):
		pass
	def SetMinSize(self, *a):
		pass
	def SetSizerAndFit(self, *a):
		pass
	def Bind(self, *a, **kw):
		pass
	def ShowModal(self):
		return 5100
	def EndModal(self, code):
		pass
	def Destroy(self):
		pass
	def PopupMenu(self, *a, **kw):
		pass

wx = stub(
	"wx",
	Dialog=_StubDialog,
	BoxSizer=lambda *a, **kw: Mock(),
	StaticText=lambda *a, **kw: Mock(),
	TextCtrl=lambda *a, **kw: Mock(),
	ListBox=lambda *a, **kw: Mock(),
	IsMainThread=lambda: True,
	YES=1,
	NO=0,
	YES_NO=2,
	ICON_QUESTION=4,
	OK=8,
	ICON_ERROR=16,
	ID_ANY=-1,
	ID_OK=5100,
	ID_CANCEL=5101,
	NOT_FOUND=-1,
	DEFAULT_DIALOG_STYLE=0,
	RESIZE_BORDER=0,
	VERTICAL=1,
	HORIZONTAL=2,
	EXPAND=4,
	ALL=8,
	ALIGN_CENTER=16,
	LB_SINGLE=0,
	EVT_TEXT=None,
	EVT_LISTBOX_DCLICK=None,
	EVT_BUTTON=None,
	EVT_MENU=None,
	Menu=_StubMenu,
	Button=lambda *a, **kw: Mock(),
)
pending = []
wx.CallAfter = lambda fn, *a, **kw: pending.append((fn, a, kw))
gui = stub("gui", messageBox=lambda *a, **kw: wx.NO, guiHelper=Mock(), nvdaControls=Mock(), mainFrame=Mock())
stub("gui.settingsDialogs", SettingsPanel=object)
gui.settingsDialogs = types.SimpleNamespace(NVDASettingsDialog=types.SimpleNamespace(categoryClasses=[]))
api = stub("api", copyToClip=lambda *a, **kw: True)
stub("ui", message=lambda *a: None)


def normalizeGestureIdentifier(identifier):
	"""Copy of NVDA's inputCore.normalizeGestureIdentifier (lower case, sorted + parts)."""
	prefix, main = identifier.lower().split(":", 1)
	return f"{prefix}:{'+'.join(sorted(main.split('+')))}"


stub("inputCore", manager=Mock(), normalizeGestureIdentifier=normalizeGestureIdentifier)
stub("keyboardHandler", KeyboardInputGesture=Mock())
stub("scriptHandler", script=lambda **kw: lambda f: f)
stub("tones", beep=lambda *a: None)
stub("NVDAState", shouldWriteToDisk=lambda: True)
nvdaLog = logging.getLogger("nvda")
nvdaLog.debugWarning = nvdaLog.warning
stub("logHandler", log=nvdaLog)


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

stub("textInfos", POSITION_SELECTION=1)
