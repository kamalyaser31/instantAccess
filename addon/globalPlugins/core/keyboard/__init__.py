# -*- coding: utf-8 -*-
"""Send hotkeys and type text for instant Access.

Trimmed from boppreh/keyboard 0.13.5 (https://github.com/boppreh/keyboard), MIT License,
Copyright (c) 2016 BoppreH; the full notice is in LICENSE.txt in this folder. Only `send` and
`write` remain. The hooks, hotkeys, recording, word listeners and the key-state tracking that
depended on them were removed, because instant Access never listens to the keyboard. Local
changes: `write` accepts `cancel_event`, and `send` releases the keys it pressed if sending fails.
"""

import collections as _collections
import re as _re
import time as _time

from . import _winkeyboard as _os_keyboard
from ._canonical_names import normalize_name, sided_modifiers


def _is_number(x):
	return isinstance(x, int)


def _is_list(x):
	return isinstance(x, (list, tuple))


def _is_str(x):
	return isinstance(x, str)


def key_to_scan_codes(key, error_if_missing=True):
	"""
	Returns a list of scan codes associated with this key (name or scan code).
	"""
	if _is_number(key):
		return (key,)
	elif _is_list(key):
		return sum((key_to_scan_codes(i) for i in key), ())
	elif not _is_str(key):
		raise ValueError("Unexpected key type " + str(type(key)) + ", value (" + repr(key) + ")")

	normalized = normalize_name(key)
	if normalized in sided_modifiers:
		left_scan_codes = key_to_scan_codes("left " + normalized, False)
		right_scan_codes = key_to_scan_codes("right " + normalized, False)
		return left_scan_codes + tuple(c for c in right_scan_codes if c not in left_scan_codes)

	try:
		# Put items in ordered dict to remove duplicates.
		t = tuple(
			_collections.OrderedDict(
				(scan_code, True) for scan_code, modifier in _os_keyboard.map_name(normalized)
			),
		)
		e = None
	except (KeyError, ValueError) as exception:
		t = ()
		e = exception

	if not t and error_if_missing:
		raise ValueError("Key {} is not mapped to any known key.".format(repr(key)), e)
	else:
		return t


def parse_hotkey(hotkey):
	"""
	Parses a user-provided hotkey into nested tuples representing the
	parsed structure, with the bottom values being lists of scan codes.
	Also accepts raw scan codes, which are then wrapped in the required
	number of nestings.

	Example:

	    parse_hotkey("alt+shift+a, alt+b, c")
	    #    Keys:    ^~^ ^~~~^ ^  ^~^ ^  ^
	    #    Steps:   ^~~~~~~~~~^  ^~~~^  ^

	    # ((alt_codes, shift_codes, a_codes), (alt_codes, b_codes), (c_codes,))
	"""
	if _is_number(hotkey) or len(hotkey) == 1:
		scan_codes = key_to_scan_codes(hotkey)
		step = (scan_codes,)
		steps = (step,)
		return steps
	elif _is_list(hotkey):
		if not any(map(_is_list, hotkey)):
			step = tuple(key_to_scan_codes(k) for k in hotkey)
			steps = (step,)
			return steps
		return hotkey

	steps = []
	for step in _re.split(r",\s?", hotkey):
		keys = _re.split(r"\s?\+\s?", step)
		steps.append(tuple(key_to_scan_codes(key) for key in keys))
	return tuple(steps)


def send(hotkey, do_press=True, do_release=True):
	"""
	Sends OS events that perform the given *hotkey* hotkey.

	- `hotkey` can be either a scan code (e.g. 57 for space), single key
	(e.g. 'space') or multi-key, multi-step hotkey (e.g. 'alt+F4, enter').
	- `do_press` if true then press events are sent. Defaults to True.
	- `do_release` if true then release events are sent. Defaults to True.

	Keys are released in the opposite order they were pressed. If sending fails,
	every key pressed so far is released before the error is raised.
	"""
	parsed = parse_hotkey(hotkey)
	pressed = []
	try:
		for step in parsed:
			if do_press:
				for scan_codes in step:
					_os_keyboard.press(scan_codes[0])
					pressed.append(scan_codes[0])
			if do_release:
				for scan_codes in reversed(step):
					_os_keyboard.release(scan_codes[0])
					if scan_codes[0] in pressed:
						pressed.remove(scan_codes[0])
	except Exception:
		for scan_code in reversed(pressed):
			try:
				_os_keyboard.release(scan_code)
			except Exception:
				pass
		raise


def write(text, delay=0, cancel_event=None):
	"""
	Types *text* as explicit Unicode input, one character at a time; line breaks and
	backspace are sent as keys. `delay` is the number of seconds between characters.

	Returns False when `cancel_event` is set before the text is complete, otherwise True.
	"""
	for letter in text:
		if cancel_event is not None and cancel_event.is_set():
			return False
		if letter in "\n\b":
			send(letter)
		else:
			_os_keyboard.type_unicode(letter)
		if delay:
			if cancel_event is not None:
				if cancel_event.wait(delay):
					return False
			else:
				_time.sleep(delay)
	return True
