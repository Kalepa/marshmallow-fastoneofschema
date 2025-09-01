Migration from marshmallow-oneofschema
=====================================

Install
-------

uv::

  uv add marshmallow-fastoneofschema

poetry::

  poetry add marshmallow-fastoneofschema

pip::

  pip install marshmallow-fastoneofschema

Remove `marshmallow-oneofschema` if present to avoid conflicts. The fork will raise ImportError if both are installed.

Imports
-------

- Keep existing imports (plug‑and‑play):
  from marshmallow_oneofschema import OneOfSchema

- Or switch to the alias:
  from marshmallow_fastoneofschema import FastOneOfSchema

Behavior
--------

- Same API and error shapes as upstream.
- Faster load/dump paths; batch grouping for many=True.
- Flags:
  - FOO_DISABLE_AGGRESSIVE_MODE=1 disables schema instance reuse.
  - FOO_CONTEXT_ISOLATION=1 enables per‑task instance caches (ContextVars).
- Per‑schema toggles via Meta.fastoneof.
