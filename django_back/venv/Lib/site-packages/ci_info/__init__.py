from builtins import str  # remove this once Py2 is dropped
import json
import os

try:
    from ._version import __version__
except ImportError:
    __version__ = "0+unknown"

_here = os.path.dirname(__file__)
with open(os.path.join(_here, "vendors.json")) as fp:
    vendors = json.load(fp)


def _detect_env(env=None):
    if env is None:
        env = os.environ

    for vendor in vendors:
        vend = vendor.get("env")
        if isinstance(vend, str) and vend in env:
            return vendor
        if isinstance(vend, list):
            if all(ev in env for ev in vend):
                return vendor
        elif isinstance(vend, dict):
            if "includes" in vend:
                # Envvar needs to be present and include some value
                if vend["env"] in env and vend["includes"] in env[vend["env"]]:
                    return vendor
            elif "any" in vend:
                if any(ev in env for ev in vend["any"]):
                    return vendor
            else:
                for ev, val in vend.items():
                    if ev in env and env[ev] == val:
                        return vendor
    return {}


def name(env=None):
    """
    Returns a string containing name of the CI server the code is running on.
    If CI server is not detected, returns None.
    """
    return _detect_env(env).get("name")


def is_ci(env=None):
    """
    Returns a boolean. Will be `True` if the code is running on a CI server,
    otherwise `False`.
    """
    return bool(name(env))


def is_pr(env=None):
    """
    Returns a boolean if PR detection is supported for the current CI server.
    Will be `True` if a PR is being tested, otherwise `False`. If PR detection
    is not supported for the current CI server, the value will be `None`.
    """
    if env is None:
        env = os.environ
    vendor = _detect_env(env)

    vpr = vendor.get("pr")
    if vpr is None:
        return

    if isinstance(vpr, str):
        return bool(env.get(vpr))
    if isinstance(vpr, dict):
        if "env" in vpr:
            # Envvar is not equal to
            if "ne" in vpr:
                return bool(env.get(vpr["env"])) and env.get(vpr["env"]) != vpr["ne"]
            # Envvar is one of a set of values
            elif "any" in vpr:
                return env.get(vpr["env"]) in vpr["any"]
        # Envvar is one of a set of values
        elif "any" in vpr:
            for k in vpr["any"]:
                if env.get(k):
                    return True
            return False
        # Specific value(s)
        else:
            for k, v in vpr.items():
                if env.get(k) != v:
                    return False
            return True
    return None


def info(env=None):
    """Return a dictionary with all info: name, is_ci, is_pr."""
    return {
        "name": name(env),
        "is_ci": is_ci(env),
        "is_pr": is_pr(env),
    }
