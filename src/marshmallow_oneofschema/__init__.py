from __future__ import annotations

import sys

try:
    from marshmallow_fastoneofschema._bootstrap_common import warn_if_both_installed

    warn_if_both_installed()
    try:
        from marshmallow_fastoneofschema import one_of_schema as _fast_one_of_schema

        sys.modules.setdefault(__name__ + ".one_of_schema", _fast_one_of_schema)
    except Exception:
        pass
except Exception:
    pass

__all__ = ["OneOfSchema", "FastOneOfSchema"]
from marshmallow_fastoneofschema.one_of_schema import OneOfSchema as FastOneOfSchema
from marshmallow_fastoneofschema.one_of_schema import OneOfSchema as OneOfSchema
