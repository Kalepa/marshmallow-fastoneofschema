from __future__ import annotations

from typing import Any

try:
    from hatchling.metadata.plugin.interface import MetadataHookInterface
except Exception:

    class MetadataHookInterface:  # type: ignore[no-redef]
        pass


class ObsoletesHook(MetadataHookInterface):
    PLUGIN_NAME = "obsoletes"
    _VALUE = "marshmallow-oneofschema"

    def update(self, metadata: Any) -> None:
        try:
            core = getattr(metadata, "core", None)
            if core is not None:
                for attr in ("data", "fields", "metadata", "_data"):
                    mapping = getattr(core, attr, None)
                    if isinstance(mapping, dict):
                        existing = mapping.get("Obsoletes-Dist")
                        if isinstance(existing, list):
                            if self._VALUE not in existing:
                                existing.append(self._VALUE)
                        else:
                            mapping["Obsoletes-Dist"] = [self._VALUE]
                        return
        except Exception:
            pass

        try:
            if isinstance(metadata, dict):
                existing = metadata.get("Obsoletes-Dist")
                if isinstance(existing, list):
                    if self._VALUE not in existing:
                        existing.append(self._VALUE)
                else:
                    metadata["Obsoletes-Dist"] = [self._VALUE]
        except Exception:
            pass
