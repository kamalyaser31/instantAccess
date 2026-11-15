# -*- coding: utf-8 -*-
"""Windows backend that sends key presses and Unicode characters with SendInput.

Trimmed for instant Access from boppreh/keyboard 0.13.5 (MIT License, see LICENSE.txt in this
folder). Only the name tables and the sending functions remain; the keyboard hook and its
message loop were removed because instant Access never listens to the keyboard.
"""

import ctypes
from collections import defaultdict
from ctypes import POINTER, c_int, c_long, c_uint, c_uint8
from ctypes.wintypes import DWORD, LONG, LPWSTR, WORD
from threading import Lock

from ._canonical_names import normalize_name

ULONG_PTR = POINTER(DWORD)

# https://github.com/boppreh/mouse/issues/1
user32 = ctypes.WinDLL("user32", use_last_error=True)

INPUT_KEYBOARD = 1

KEYEVENTF_EXTENDEDKEY = 0x01
KEYEVENTF_KEYUP = 0x02
KEYEVENTF_UNICODE = 0x04

keyboard_state_type = c_uint8 * 256


class MOUSEINPUT(ctypes.Structure):
	_fields_ = (
		("dx", LONG),
		("dy", LONG),
		("mouseData", DWORD),
		("dwFlags", DWORD),
		("time", DWORD),
		("dwExtraInfo", ULONG_PTR),
	)


class KEYBDINPUT(ctypes.Structure):
	_fields_ = (
		("wVk", WORD),
		("wScan", WORD),
		("dwFlags", DWORD),
		("time", DWORD),
		("dwExtraInfo", ULONG_PTR),
	)


class HARDWAREINPUT(ctypes.Structure):
	_fields_ = (
		("uMsg", DWORD),
		("wParamL", WORD),
		("wParamH", WORD),
	)


class _INPUTunion(ctypes.Union):
	_fields_ = (
		("mi", MOUSEINPUT),
		("ki", KEYBDINPUT),
		("hi", HARDWAREINPUT),
	)


class INPUT(ctypes.Structure):
	_fields_ = (
		("type", DWORD),
		("union", _INPUTunion),
	)


GetKeyNameText = user32.GetKeyNameTextW
GetKeyNameText.argtypes = [c_long, LPWSTR, c_int]
GetKeyNameText.restype = c_int

MapVirtualKey = user32.MapVirtualKeyW
MapVirtualKey.argtypes = [c_uint, c_uint]
MapVirtualKey.restype = c_uint

ToUnicode = user32.ToUnicode
ToUnicode.argtypes = [c_uint, c_uint, keyboard_state_type, LPWSTR, c_int, c_uint]
ToUnicode.restype = c_int

SendInput = user32.SendInput
SendInput.argtypes = [c_uint, POINTER(INPUT), c_int]
SendInput.restype = c_uint

# https://msdn.microsoft.com/en-us/library/windows/desktop/ms646307(v=vs.85).aspx
MAPVK_VK_TO_CHAR = 2
MAPVK_VK_TO_VSC = 0
MAPVK_VSC_TO_VK = 1
MAPVK_VK_TO_VSC_EX = 4
MAPVK_VSC_TO_VK_EX = 3

# List taken from the official documentation, but stripped of the OEM-specific keys.
# Keys are virtual key codes, values are pairs (name, is_keypad).
official_virtual_keys = {
	0x03: ("control-break processing", False),
	0x08: ("backspace", False),
	0x09: ("tab", False),
	0x0C: ("clear", False),
	0x0D: ("enter", False),
	0x10: ("shift", False),
	0x11: ("ctrl", False),
	0x12: ("alt", False),
	0x13: ("pause", False),
	0x14: ("caps lock", False),
	0x15: ("ime kana mode", False),
	0x15: ("ime hanguel mode", False),
	0x15: ("ime hangul mode", False),
	0x17: ("ime junja mode", False),
	0x18: ("ime final mode", False),
	0x19: ("ime hanja mode", False),
	0x19: ("ime kanji mode", False),
	0x1B: ("esc", False),
	0x1C: ("ime convert", False),
	0x1D: ("ime nonconvert", False),
	0x1E: ("ime accept", False),
	0x1F: ("ime mode change request", False),
	0x20: ("spacebar", False),
	0x21: ("page up", False),
	0x22: ("page down", False),
	0x23: ("end", False),
	0x24: ("home", False),
	0x25: ("left", False),
	0x26: ("up", False),
	0x27: ("right", False),
	0x28: ("down", False),
	0x29: ("select", False),
	0x2A: ("print", False),
	0x2B: ("execute", False),
	0x2C: ("print screen", False),
	0x2D: ("insert", False),
	0x2E: ("delete", False),
	0x2F: ("help", False),
	0x30: ("0", False),
	0x31: ("1", False),
	0x32: ("2", False),
	0x33: ("3", False),
	0x34: ("4", False),
	0x35: ("5", False),
	0x36: ("6", False),
	0x37: ("7", False),
	0x38: ("8", False),
	0x39: ("9", False),
	0x41: ("a", False),
	0x42: ("b", False),
	0x43: ("c", False),
	0x44: ("d", False),
	0x45: ("e", False),
	0x46: ("f", False),
	0x47: ("g", False),
	0x48: ("h", False),
	0x49: ("i", False),
	0x4A: ("j", False),
	0x4B: ("k", False),
	0x4C: ("l", False),
	0x4D: ("m", False),
	0x4E: ("n", False),
	0x4F: ("o", False),
	0x50: ("p", False),
	0x51: ("q", False),
	0x52: ("r", False),
	0x53: ("s", False),
	0x54: ("t", False),
	0x55: ("u", False),
	0x56: ("v", False),
	0x57: ("w", False),
	0x58: ("x", False),
	0x59: ("y", False),
	0x5A: ("z", False),
	0x5B: ("left windows", False),
	0x5C: ("right windows", False),
	0x5D: ("applications", False),
	0x5F: ("sleep", False),
	0x60: ("0", True),
	0x61: ("1", True),
	0x62: ("2", True),
	0x63: ("3", True),
	0x64: ("4", True),
	0x65: ("5", True),
	0x66: ("6", True),
	0x67: ("7", True),
	0x68: ("8", True),
	0x69: ("9", True),
	0x6A: ("*", True),
	0x6B: ("+", True),
	0x6C: ("separator", True),
	0x6D: ("-", True),
	0x6E: ("decimal", True),
	0x6F: ("/", True),
	0x70: ("f1", False),
	0x71: ("f2", False),
	0x72: ("f3", False),
	0x73: ("f4", False),
	0x74: ("f5", False),
	0x75: ("f6", False),
	0x76: ("f7", False),
	0x77: ("f8", False),
	0x78: ("f9", False),
	0x79: ("f10", False),
	0x7A: ("f11", False),
	0x7B: ("f12", False),
	0x7C: ("f13", False),
	0x7D: ("f14", False),
	0x7E: ("f15", False),
	0x7F: ("f16", False),
	0x80: ("f17", False),
	0x81: ("f18", False),
	0x82: ("f19", False),
	0x83: ("f20", False),
	0x84: ("f21", False),
	0x85: ("f22", False),
	0x86: ("f23", False),
	0x87: ("f24", False),
	0x90: ("num lock", False),
	0x91: ("scroll lock", False),
	0xA0: ("left shift", False),
	0xA1: ("right shift", False),
	0xA2: ("left ctrl", False),
	0xA3: ("right ctrl", False),
	0xA4: ("left menu", False),
	0xA5: ("right menu", False),
	0xA6: ("browser back", False),
	0xA7: ("browser forward", False),
	0xA8: ("browser refresh", False),
	0xA9: ("browser stop", False),
	0xAA: ("browser search key", False),
	0xAB: ("browser favorites", False),
	0xAC: ("browser start and home", False),
	0xAD: ("volume mute", False),
	0xAE: ("volume down", False),
	0xAF: ("volume up", False),
	0xB0: ("next track", False),
	0xB1: ("previous track", False),
	0xB2: ("stop media", False),
	0xB3: ("play/pause media", False),
	0xB4: ("start mail", False),
	0xB5: ("select media", False),
	0xB6: ("start application 1", False),
	0xB7: ("start application 2", False),
	0xBB: ("+", False),
	0xBC: (",", False),
	0xBD: ("-", False),
	0xBE: (".", False),
	# 0xbe:('/', False), # Used for miscellaneous characters; it can vary by keyboard. For the US standard keyboard, the '/?.
	0xE5: ("ime process", False),
	0xF6: ("attn", False),
	0xF7: ("crsel", False),
	0xF8: ("exsel", False),
	0xF9: ("erase eof", False),
	0xFA: ("play", False),
	0xFB: ("zoom", False),
	0xFC: ("reserved ", False),
	0xFD: ("pa1", False),
	0xFE: ("clear", False),
}

tables_lock = Lock()
to_name = defaultdict(list)
from_name = defaultdict(list)
scan_code_to_vk = {}

distinct_modifiers = [
	(),
	("shift",),
	("alt gr",),
	("num lock",),
	("shift", "num lock"),
	("caps lock",),
	("shift", "caps lock"),
	("alt gr", "num lock"),
]

name_buffer = ctypes.create_unicode_buffer(32)
unicode_buffer = ctypes.create_unicode_buffer(32)
keyboard_state = keyboard_state_type()


def get_event_names(scan_code, vk, is_extended, modifiers):
	is_keypad = (scan_code, vk, is_extended) in keypad_keys
	is_official = vk in official_virtual_keys
	if is_keypad and is_official:
		yield official_virtual_keys[vk][0]

	keyboard_state[0x10] = 0x80 * ("shift" in modifiers)
	keyboard_state[0x11] = 0x80 * ("alt gr" in modifiers)
	keyboard_state[0x12] = 0x80 * ("alt gr" in modifiers)
	keyboard_state[0x14] = 0x01 * ("caps lock" in modifiers)
	keyboard_state[0x90] = 0x01 * ("num lock" in modifiers)
	keyboard_state[0x91] = 0x01 * ("scroll lock" in modifiers)
	unicode_ret = ToUnicode(vk, scan_code, keyboard_state, unicode_buffer, len(unicode_buffer), 0)
	if unicode_ret and unicode_buffer.value:
		yield unicode_buffer.value
		# unicode_ret == -1 -> is dead key
		# ToUnicode has the side effect of setting global flags for dead keys.
		# Therefore we need to call it twice to clear those flags.
		# If your 6 and 7 keys are named "^6" and "^7", this is the reason.
		ToUnicode(vk, scan_code, keyboard_state, unicode_buffer, len(unicode_buffer), 0)

	name_ret = GetKeyNameText(scan_code << 16 | is_extended << 24, name_buffer, len(name_buffer))
	if name_ret and name_buffer.value:
		yield name_buffer.value

	char = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_CHAR) & 0xFF
	if char != 0:
		yield chr(char)

	if not is_keypad and is_official:
		yield official_virtual_keys[vk][0]


def _setup_name_tables():
	"""
	Ensures the scan code/virtual key code/name translation tables are
	filled.
	"""
	with tables_lock:
		if to_name:
			return

		# Go through every possible scan code, and map them to virtual key codes.
		# Then vice-versa.
		all_scan_codes = [(sc, user32.MapVirtualKeyExW(sc, MAPVK_VSC_TO_VK_EX, 0)) for sc in range(0x100)]
		all_vks = [(user32.MapVirtualKeyExW(vk, MAPVK_VK_TO_VSC_EX, 0), vk) for vk in range(0x100)]
		for scan_code, vk in all_scan_codes + all_vks:
			# `to_name` and `from_name` entries will be a tuple (scan_code, vk, extended, shift_state).
			if (scan_code, vk, 0, 0, 0) in to_name:
				continue

			if scan_code not in scan_code_to_vk:
				scan_code_to_vk[scan_code] = vk

			# Brute force all combinations to find all possible names.
			for extended in [0, 1]:
				for modifiers in distinct_modifiers:
					entry = (scan_code, vk, extended, modifiers)
					# Get key names from ToUnicode, GetKeyNameText, MapVirtualKeyW and official virtual keys.
					names = list(get_event_names(*entry))
					if names:
						# Also map lowercased key names, but only after the properly cased ones.
						lowercase_names = [name.lower() for name in names]
						to_name[entry] = names + lowercase_names
						# Remember the "id" of the name, as the first techniques
						# have better results and therefore priority.
						for i, name in enumerate(map(normalize_name, names + lowercase_names)):
							from_name[name].append((i, entry))

		# TODO: single quotes on US INTL is returning the dead key (?), and therefore
		# not typing properly.

		# Alt gr is way outside the usual range of keys (0..127) and on my
		# computer is named as 'ctrl'. Therefore we add it manually and hope
		# Windows is consistent in its inconsistency.
		for extended in [0, 1]:
			for modifiers in distinct_modifiers:
				to_name[(541, 162, extended, modifiers)] = ["alt gr"]
				from_name["alt gr"].append((1, (541, 162, extended, modifiers)))

	modifiers_preference = defaultdict(lambda: 10)
	modifiers_preference.update({(): 0, ("shift",): 1, ("alt gr",): 2, ("ctrl",): 3, ("alt",): 4})

	def order_key(line):
		i, entry = line
		scan_code, vk, extended, modifiers = entry
		return modifiers_preference[modifiers], i, extended, vk, scan_code

	for name, entries in list(from_name.items()):
		from_name[name] = sorted(set(entries), key=order_key)


# Called by keyboard/__init__.py
init = _setup_name_tables

# List created manually.
keypad_keys = [
	# (scan_code, virtual_key_code, is_extended)
	(126, 194, 0),
	(126, 194, 0),
	(28, 13, 1),
	(28, 13, 1),
	(53, 111, 1),
	(53, 111, 1),
	(55, 106, 0),
	(55, 106, 0),
	(69, 144, 1),
	(69, 144, 1),
	(71, 103, 0),
	(71, 36, 0),
	(72, 104, 0),
	(72, 38, 0),
	(73, 105, 0),
	(73, 33, 0),
	(74, 109, 0),
	(74, 109, 0),
	(75, 100, 0),
	(75, 37, 0),
	(76, 101, 0),
	(76, 12, 0),
	(77, 102, 0),
	(77, 39, 0),
	(78, 107, 0),
	(78, 107, 0),
	(79, 35, 0),
	(79, 97, 0),
	(80, 40, 0),
	(80, 98, 0),
	(81, 34, 0),
	(81, 99, 0),
	(82, 45, 0),
	(82, 96, 0),
	(83, 110, 0),
	(83, 46, 0),
]
# (scan code, virtual key, extended). Special keys must not compete with localized
# GetKeyNameText results: for example, Windows can call Pause's E1 scan code "Right Ctrl".
NAMED_KEYS = {
	"enter": (0x1C, 0x0D, False),
	"pause": (0x45, 0x13, False),
	"page up": (0x49, 0x21, True),
	"page down": (0x51, 0x22, True),
	"end": (0x4F, 0x23, True),
	"home": (0x47, 0x24, True),
	"left": (0x4B, 0x25, True),
	"up": (0x48, 0x26, True),
	"right": (0x4D, 0x27, True),
	"down": (0x50, 0x28, True),
	"print screen": (0x37, 0x2C, True),
	"insert": (0x52, 0x2D, True),
	"delete": (0x53, 0x2E, True),
	"left windows": (0x5B, 0x5B, True),
	"right windows": (0x5C, 0x5C, True),
	"menu": (0x5D, 0x5D, True),
	"num lock": (0x45, 0x90, True),
	"left shift": (0x2A, 0xA0, False),
	"right shift": (0x36, 0xA1, False),
	"left ctrl": (0x1D, 0xA2, False),
	"right ctrl": (0x1D, 0xA3, True),
	"left alt": (0x38, 0xA4, False),
	"right alt": (0x38, 0xA5, True),
	"numpadenter": (0x1C, 0x0D, True),
	"numpadmultiply": (0x37, 0x6A, False),
	"numpadplus": (0x4E, 0x6B, False),
	"numpadminus": (0x4A, 0x6D, False),
	"numpaddecimal": (0x53, 0x6E, False),
	"numpaddivide": (0x35, 0x6F, True),
	"numpadclear": (0x4C, 0x0C, False),
}
NAMED_KEYS.update(
	(f"numpad{digit}", (scan, 0x60 + digit, False))
	for digit, scan in enumerate((0x52, 0x4F, 0x50, 0x51, 0x4B, 0x4C, 0x4D, 0x47, 0x48, 0x49))
)
NAMED_KEYS.update(
	("numpad" + name.replace(" ", ""), (*NAMED_KEYS[name][:2], False))
	for name in ("home", "end", "up", "down", "left", "right", "page up", "page down", "insert", "delete")
)


def map_name(name):
	if name in NAMED_KEYS:
		yield NAMED_KEYS[name], ()
		return
	_setup_name_tables()

	entries = from_name.get(name)
	if not entries:
		raise ValueError("Key name {} is not mapped to any known key.".format(repr(name)))
	for i, entry in entries:
		scan_code, vk, is_extended, modifiers = entry
		if scan_code == 541:
			yield scan_code, modifiers
		else:
			yield (scan_code & 0xFF, vk, bool(is_extended or scan_code >> 8 == 0xE0)), modifiers


# Page Up/Down, End, Home, the arrows, Insert and Delete. Without the extended flag Windows
# takes them for their numeric keypad twins, and Shift+End moves without selecting.
EXTENDED_VKS = frozenset((0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E))


def _with_extended_flag(vk, event_type):
	return event_type | KEYEVENTF_EXTENDEDKEY if vk in EXTENDED_VKS else event_type


def _send_event(code, event_type):
	if isinstance(code, tuple):
		scan_code, vk, is_extended = code
		flags = event_type | (KEYEVENTF_EXTENDEDKEY if is_extended else 0)
		user32.keybd_event(vk, scan_code, flags, 0)
	elif code == 541:
		# Alt-gr is made of ctrl+alt. Just sending even 541 doesn't do anything.
		user32.keybd_event(0x11, code, event_type, 0)
		user32.keybd_event(0x12, code, event_type, 0)
	elif code > 0:
		vk = scan_code_to_vk.get(code, 0)
		user32.keybd_event(vk, code, _with_extended_flag(vk, event_type), 0)
	else:
		# Negative scan code is a way to indicate we don't have a scan code,
		# and the value actually contains the Virtual key code.
		user32.keybd_event(-code, 0, _with_extended_flag(-code, event_type), 0)


def press(code):
	_send_event(code, 0)


def release(code):
	_send_event(code, 2)


def type_unicode(character):
	# This code and related structures are based on
	# http://stackoverflow.com/a/11910555/252218
	surrogates = bytearray(character.encode("utf-16le"))
	presses = []
	releases = []
	for i in range(0, len(surrogates), 2):
		higher, lower = surrogates[i : i + 2]
		structure = KEYBDINPUT(0, (lower << 8) + higher, KEYEVENTF_UNICODE, 0, None)
		presses.append(INPUT(INPUT_KEYBOARD, _INPUTunion(ki=structure)))
		structure = KEYBDINPUT(0, (lower << 8) + higher, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, None)
		releases.append(INPUT(INPUT_KEYBOARD, _INPUTunion(ki=structure)))
	inputs = presses + releases
	nInputs = len(inputs)
	LPINPUT = INPUT * nInputs
	pInputs = LPINPUT(*inputs)
	cbSize = c_int(ctypes.sizeof(INPUT))
	if SendInput(nInputs, pInputs, cbSize) != nInputs:
		raise OSError("Could not send Unicode keyboard input")
