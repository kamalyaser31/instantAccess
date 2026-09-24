# -*- coding: utf-8 -*-

import math
import threading


def parseDelay(value):
	"""Parse a finite, non-negative duration without treating zero as missing."""
	if isinstance(value, bool):
		raise ValueError("Invalid delay")
	try:
		number = float(value)
	except (TypeError, OverflowError) as error:
		raise ValueError("Invalid delay") from error
	if not math.isfinite(number) or number < 0 or number > threading.TIMEOUT_MAX:
		raise ValueError("Invalid delay")
	return number
