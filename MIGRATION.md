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

If `marshmallow-oneofschema` is still present, the fork logs an error and uses the fast fork. Additionally, a startup hook ensures imports are redirected to the fast fork even if the upstream was installed later. For reliability, uninstall `marshmallow-oneofschema` to avoid any packaging/order surprises.

Packaging
---------

- The wheel declares `Obsoletes-Dist: marshmallow-oneofschema` to signal that this fork supersedes the upstream distribution.
- The wheel ships a `.pth` bootstrap that aliases `marshmallow_oneofschema` imports to the fast fork at interpreter startup. Disable with `FASTONEOFSCHEMA_DISABLE_PTH=1` if needed.

Imports
-------

- Switch to the new package name:
  from marshmallow_fastoneofschema import FastOneOfSchema

- Or keep existing imports and use the alias (important: make sure `marshmallow-oneofschema` is uninstalled to avoid conflicts):
  from marshmallow_oneofschema import OneOfSchema


Behavior
--------

- Same API and error shapes as upstream.
- Faster load/dump paths; batch grouping for many=True.
- Flags:
  - FOO_DISABLE_AGGRESSIVE_MODE=1 disables schema instance reuse.
  - FOO_CONTEXT_ISOLATION=1 enables per‑task instance caches (ContextVars).
- Per‑schema toggles via Meta.fastoneof.
