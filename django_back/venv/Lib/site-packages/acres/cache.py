from __future__ import annotations

import atexit
from contextlib import ExitStack
from functools import cache

from . import typ as t
from ._compat import files, as_file


EXIT_STACK = ExitStack()
atexit.register(EXIT_STACK.close)


@cache
def cached_resource(anchor: str | t.ModuleType, segments: tuple[str, ...]) -> t.Path:
    return EXIT_STACK.enter_context(as_file(files(anchor).joinpath(*segments)))
