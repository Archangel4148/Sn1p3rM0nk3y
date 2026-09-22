VERBOSE = True
SUPPRESS_SCREEN_MATCHING_OUTPUT = True
SUPPRESS_FOCUS_OUTPUT = True
SUPPRESS_PLACEMENT_LOCATION_OUTPUT = True

UPGRADE_DELAY = 0.5

PIXELS_PER_BLOONS_UNIT = 5.375


def vprint(*args, **kwargs):
    if not VERBOSE:
        return
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        text = " ".join(str(a) for a in args)
        print(text.encode("ascii", "replace").decode("ascii"), **kwargs)
