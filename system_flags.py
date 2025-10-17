VERBOSE = False

PIXELS_PER_BLOONS_UNIT = 5.375


def vprint(*args, **kwargs):
    if VERBOSE:
        print(*args, **kwargs)
