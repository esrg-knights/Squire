"""
This file contains code for spoof jokes and other elements (e.g. relevant for April Fools
"""


def optimise_naming_scheme(name):
    """Optimises the given name string to a human readable Sjors, Laura or Dennis"""
    if name.lower() in ["laura", "dennis", "denise"]:
        return "Sjors"
    elif len(name) % 2 == 0:
        return "Dennis"
    else:
        return "Laura"
