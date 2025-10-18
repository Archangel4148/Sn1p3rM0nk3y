VERBOSE = True
SUPPRESS_SCREEN_MATCHING_OUTPUT = True
SUPPRESS_FOCUS_OUTPUT = True

PIXELS_PER_BLOONS_UNIT = 5.375


def vprint(*args, **kwargs):
    if VERBOSE:
        print(*args, **kwargs)
