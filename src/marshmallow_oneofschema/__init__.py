from __future__ import annotations

import logging
import sys
import warnings
from importlib import metadata

try:
    dists = {dist.metadata.get("Name") for dist in metadata.distributions()}
    if "marshmallow-oneofschema" in dists and "marshmallow-fastoneofschema" in dists:
        msg = (
            "Both marshmallow-oneofschema and marshmallow-fastoneofschema are installed. "
            "Proceeding with the fast fork and ignoring the upstream package. "
            "For reliability, uninstall marshmallow-oneofschema."
        )
        logging.getLogger(__name__).error(msg)
        warnings.warn(msg, RuntimeWarning, stacklevel=2)
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
