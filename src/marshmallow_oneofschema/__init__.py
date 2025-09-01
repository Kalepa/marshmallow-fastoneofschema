from __future__ import annotations

from importlib import metadata

try:
    dists = {dist.metadata.get("Name") for dist in metadata.distributions()}
    if "marshmallow-oneofschema" in dists and "marshmallow-fastoneofschema" in dists:
        raise ImportError(
            "Both marshmallow-oneofschema and marshmallow-fastoneofschema are installed. Uninstall marshmallow-oneofschema before using the fast version."
        )
except Exception:
    pass

from marshmallow_fastoneofschema.one_of_schema import OneOfSchema  # noqa: F401
from marshmallow_fastoneofschema.one_of_schema import OneOfSchema as FastOneOfSchema
