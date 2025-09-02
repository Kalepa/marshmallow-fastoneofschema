from __future__ import annotations

import logging
import warnings
from importlib import metadata


def warn_if_both_installed() -> None:
    """Emit a warning if both upstream and fast packages are installed."""
    try:
        dists = {dist.metadata.get("Name") for dist in metadata.distributions()}
        if (
            "marshmallow-oneofschema" in dists
            and "marshmallow-fastoneofschema" in dists
        ):
            msg = (
                "Both marshmallow-oneofschema and marshmallow-fastoneofschema are installed. "
                "Proceeding with the fast fork and ignoring the upstream package. "
                "For reliability, uninstall marshmallow-oneofschema."
            )
            logging.getLogger("marshmallow_oneofschema").error(msg)
            warnings.warn(msg, RuntimeWarning, stacklevel=2)
    except Exception:
        pass
