from __future__ import annotations

import importlib.machinery
import os
import sys
import types
import warnings


def _make_pkg_module(name: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__package__ = name
    spec = importlib.machinery.ModuleSpec(name, loader=None, is_package=True)
    spec.submodule_search_locations = []
    mod.__spec__ = spec
    mod.__path__ = []
    return mod


def install() -> None:
    if os.getenv("FASTONEOFSCHEMA_DISABLE_PTH"):
        return

    target_root = "marshmallow_oneofschema"
    target_sub = f"{target_root}.one_of_schema"

    try:
        from ._bootstrap_common import warn_if_both_installed

        warn_if_both_installed()
    except Exception:
        pass

    try:
        from marshmallow_fastoneofschema import one_of_schema as _fast_mod
        from marshmallow_fastoneofschema.one_of_schema import OneOfSchema as _FastOneOf
    except Exception as exc:
        warnings.warn(
            f"fastoneofschema .pth bootstrap could not import fast module: {exc}",
            RuntimeWarning,
            stacklevel=1,
        )
        return

    sys.modules[target_sub] = _fast_mod

    root = sys.modules.get(target_root)
    if root is None or getattr(root, "__spec__", None) is None:
        root = _make_pkg_module(target_root)
        sys.modules[target_root] = root

    try:
        root.OneOfSchema = _FastOneOf  # type: ignore[attr-defined]
        root.FastOneOfSchema = _FastOneOf  # type: ignore[attr-defined]
        root.__all__ = ["OneOfSchema", "FastOneOfSchema"]  # type: ignore[attr-defined]
    except Exception:
        pass
