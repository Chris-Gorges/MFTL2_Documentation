"""Drawing kit for the MFTL manual's figures. See ``figures/README.md``."""

from __future__ import annotations

from typing import Callable

#: name -> function(outfile) that draws one figure. Filled by :func:`register`.
REGISTRY: dict[str, Callable] = {}


def register(name: str):
    """Decorator: register a function drawing ``images/<name>.svg``.

    The function takes no arguments and returns the matplotlib figure; the
    driver saves it, so every figure is written with the same settings.
    """

    def wrap(fn):
        if name in REGISTRY:
            raise ValueError(f"figure {name!r} registered twice")
        REGISTRY[name] = fn
        return fn

    return wrap
