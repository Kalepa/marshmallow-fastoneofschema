from __future__ import annotations

import os
import typing
from contextvars import ContextVar

from marshmallow import Schema, ValidationError


class _HidingKeyDict(typing.Mapping[str, typing.Any]):
    __slots__ = ("_data", "_hide")

    def __init__(self, data: typing.Mapping[str, typing.Any], hide: str):
        self._data = data
        self._hide = hide

    def __getitem__(self, key: str) -> typing.Any:  # noqa: D401
        if key == self._hide:
            raise KeyError(key)
        return self._data[key]

    def get(self, key: str, default=None):  # noqa: A003
        if key == self._hide:
            return default
        return self._data.get(key, default)

    def __iter__(self):  # noqa: D401
        for k in self._data:
            if k != self._hide:
                yield k

    def __len__(self) -> int:  # noqa: D401
        return len(self._data) - (1 if self._hide in self._data else 0)

    def __contains__(self, key: object) -> bool:  # noqa: D401
        return key != self._hide and key in self._data

    def items(self):  # noqa: D401
        for k, v in self._data.items():
            if k != self._hide:
                yield (k, v)

    def keys(self):  # noqa: D401
        for k in self._data.keys():
            if k != self._hide:
                yield k

    def values(self):  # noqa: D401
        for k, v in self._data.items():
            if k != self._hide:
                yield v


class OneOfSchema(Schema):
    type_field = "type"
    type_field_remove = True
    type_schemas: typing.Mapping[str, type[Schema] | Schema] = {}

    _foo_disable_aggressive = os.getenv("FOO_DISABLE_AGGRESSIVE_MODE", "0") in (
        "1",
        "true",
        "True",
    )
    _foo_context_isolation_env = os.getenv("FOO_CONTEXT_ISOLATION", "0") in (
        "1",
        "true",
        "True",
    )

    _foo_dump_cache: dict[type, tuple[str, Schema]] | None = None
    _foo_schema_instance_cache: dict[typing.Any, Schema] | None = None

    _foo_aggressive_ctx: ContextVar[bool | None] = ContextVar(
        "foo_aggressive_mode", default=None
    )
    _foo_isolation_ctx: ContextVar[bool | None] = ContextVar(
        "foo_context_isolation", default=None
    )
    _foo_ctx_instance_caches: ContextVar[dict | None] = ContextVar(
        "foo_instance_caches", default=None
    )
    _foo_keepalive_limit = 16

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Read per-class config from Meta.fastoneof; fall back to opts for MM3
        opts = getattr(getattr(self, "opts", None), "fastoneof", None)
        if opts is None:
            meta = getattr(self.__class__, "Meta", None)
            opts = getattr(meta, "fastoneof", {}) if meta is not None else {}
        self._foo_aggressive_override: bool | None = (
            opts.get("aggressive_mode") if isinstance(opts, dict) else None
        )
        self._foo_context_isolation_override: bool | None = (
            opts.get("context_isolation") if isinstance(opts, dict) else None
        )

    def _foo_aggressive_enabled(self) -> bool:
        cv = self._foo_aggressive_ctx.get()
        if cv is not None:
            return bool(cv)
        if self._foo_aggressive_override is not None:
            return bool(self._foo_aggressive_override)
        return not self._foo_disable_aggressive

    def _foo_context_isolation_enabled(self) -> bool:
        cv = self._foo_isolation_ctx.get()
        if cv is not None:
            return bool(cv)
        if self._foo_context_isolation_override is not None:
            return bool(self._foo_context_isolation_override)
        return bool(self._foo_context_isolation_env)

    def _foo_get_instance_cache(self) -> dict:
        if self._foo_context_isolation_enabled():
            caches = self._foo_ctx_instance_caches.get()
            if caches is None:
                caches = {}
                self._foo_ctx_instance_caches.set(caches)
            cache = caches.get(id(self))
            if cache is None:
                cache = {}
                caches[id(self)] = cache
            return cache
        if self._foo_schema_instance_cache is None:
            self._foo_schema_instance_cache = {}
        return self._foo_schema_instance_cache

    def _foo_resolve_type_key(self, tval):
        # Exact match first
        try:
            if tval in self.type_schemas:
                return tval
        except TypeError:
            return None
        # Case-insensitive fallback for string keys
        if isinstance(tval, str):
            for k in self.type_schemas.keys():
                if isinstance(k, str) and k.lower() == tval.lower():
                    return k
        return None

    def get_obj_type(self, obj):
        return obj.__class__.__name__

    def get_data_type(self, data):
        data_type = data.get(self.type_field)
        if self.type_field in data and self.type_field_remove:
            data.pop(self.type_field)
        return data_type

    def dump(self, obj, *, many=None, **kwargs):
        errors = {}
        result_data = []
        result_errors = {}
        many = self.many if many is None else bool(many)
        if not many:
            result = result_data = self._dump(obj, **kwargs)
        else:
            fast_path = (
                getattr(self.get_obj_type, "__func__", None) is OneOfSchema.get_obj_type
            )
            if not fast_path:
                for idx, o in enumerate(obj):
                    try:
                        result = self._dump(o, **kwargs)
                        result_data.append(result)
                    except ValidationError as error:
                        result_errors[idx] = error.normalized_messages()
                        result_data.append(error.valid_data)
            else:
                from collections import defaultdict

                groups = defaultdict(list)
                for idx, o in enumerate(obj):
                    tval = self.get_obj_type(o)
                    groups[tval].append((idx, o))
                results = [None] * len(obj)
                for tval, items in groups.items():
                    if tval is None:
                        for idx, _ in items:
                            result_errors[idx] = {
                                "_schema": f"Unknown object class: {obj.__class__.__name__}"
                            }
                            results[idx] = None
                        continue
                    key = self._foo_resolve_type_key(tval)
                    type_schema = (
                        self.type_schemas.get(key) if key is not None else None
                    )
                    if not type_schema:
                        for idx, _ in items:
                            result_errors[idx] = {
                                "_schema": f"Unsupported object type: {tval}"
                            }
                            results[idx] = None
                        continue
                    if isinstance(type_schema, Schema):
                        schema = type_schema
                    else:
                        if self._foo_aggressive_enabled():
                            cache = self._foo_get_instance_cache()
                            schema = cache.get(tval)
                            if schema is None:
                                schema = type_schema()
                                self._foo_keepalive_append(schema)
                                cache[tval] = schema
                        else:
                            schema = type_schema()
                            self._foo_keepalive_append(schema)
                    if hasattr(schema, "context"):
                        src_ctx = getattr(self, "context", {})
                        if schema.context != src_ctx:
                            try:
                                schema.context.clear()
                            except Exception:
                                schema.context = {}
                            schema.context.update(src_ctx)
                    batch = [o for (_, o) in items]
                    indices = [idx for (idx, _) in items]
                    try:
                        dumped = schema.dump(batch, many=True, **kwargs)
                        for pos, i in enumerate(indices):
                            res = dumped[pos]
                            if res is not None:
                                res[self.type_field] = tval
                            results[i] = res
                    except ValidationError as e:
                        msgs = e.messages
                        vdata = getattr(e, "valid_data", None)
                        for pos, i in enumerate(indices):
                            handled = False
                            if isinstance(msgs, dict):
                                if pos in msgs and msgs[pos]:
                                    result_errors[i] = msgs[pos]
                                    results[i] = None
                                    handled = True
                            elif isinstance(msgs, list):
                                if pos < len(msgs) and msgs[pos]:
                                    result_errors[i] = msgs[pos]
                                    results[i] = None
                                    handled = True
                            if not handled:
                                # Try to fill valid data if provided
                                if isinstance(vdata, list) and pos < len(vdata):
                                    results[i] = vdata[pos]
                                else:
                                    # Fallback: validate individually to recover per-item outcome
                                    try:
                                        results[i] = schema.load(
                                            items[pos],
                                            many=False,
                                            **kwargs,
                                        )
                                    except ValidationError as ee:
                                        result_errors[i] = ee.messages
                                        results[i] = getattr(ee, "valid_data", None)
                for i in range(len(obj)):
                    result_data.append(results[i])
        result = result_data
        errors = result_errors
        if not errors:
            return result
        else:
            exc = ValidationError(errors, data=obj, valid_data=result)
            raise exc

    def _dump(self, obj, *, update_fields=True, **kwargs):
        default_getter = (
            getattr(self.get_obj_type, "__func__", None) is OneOfSchema.get_obj_type
        )
        if default_getter:
            if self._foo_dump_cache is None:
                self._foo_dump_cache = {}
            entry = self._foo_dump_cache.get(obj.__class__)
            if entry is not None:
                obj_type, schema = entry
            else:
                obj_type = obj.__class__.__name__
                key = self._foo_resolve_type_key(obj_type)
                type_schema = self.type_schemas.get(key) if key is not None else None
                if not type_schema:
                    return None, {"_schema": f"Unsupported object type: {obj_type}"}
                if isinstance(type_schema, Schema):
                    schema = type_schema
                else:
                    if self._foo_context_isolation_enabled():
                        schema = type_schema()
                        self._foo_keepalive_append(schema)
                    elif self._foo_aggressive_enabled():
                        cache = self._foo_get_instance_cache()
                        schema = cache.get(obj_type)
                        if schema is None:
                            schema = type_schema()
                            self._foo_keepalive_append(schema)
                            cache[obj_type] = schema
                    else:
                        schema = type_schema()
                        self._foo_keepalive_append(schema)
                self._foo_dump_cache[obj.__class__] = (obj_type, schema)
        else:
            obj_type = self.get_obj_type(obj)
            if obj_type is None:
                return None, {
                    "_schema": f"Unknown object class: {obj.__class__.__name__}"
                }
            key = self._foo_resolve_type_key(obj_type)
            type_schema = self.type_schemas.get(key) if key is not None else None
            if not type_schema:
                return None, {"_schema": f"Unsupported object type: {obj_type}"}
            if isinstance(type_schema, Schema):
                schema = type_schema
            else:
                if self._foo_context_isolation_enabled():
                    schema = type_schema()
                    self._foo_keepalive_append(schema)
                elif self._foo_aggressive_enabled():
                    cache = self._foo_get_instance_cache()
                    schema = cache.get(obj_type)
                    if schema is None:
                        schema = type_schema()
                        self._foo_keepalive_append(schema)
                        cache[obj_type] = schema
                else:
                    schema = type_schema()
                    self._foo_keepalive_append(schema)
        if hasattr(schema, "context"):
            src_ctx = getattr(self, "context", {})
            if schema.context != src_ctx:
                try:
                    schema.context.clear()
                except Exception:
                    schema.context = {}
                schema.context.update(src_ctx)
        result = schema.dump(obj, many=False, **kwargs)
        if result is not None:
            result[self.type_field] = obj_type
        return result

    def load(self, data, *, many=None, partial=None, unknown=None, **kwargs):
        errors = {}
        result_data = []
        result_errors = {}
        many = self.many if many is None else bool(many)
        if partial is None:
            partial = self.partial
        if not many:
            try:
                result = result_data = self._load(
                    data, partial=partial, unknown=unknown, **kwargs
                )
            except ValidationError as error:
                result_errors = error.normalized_messages()
                result_data.append(error.valid_data)
        else:
            from collections import defaultdict

            groups = defaultdict(list)
            results = [None] * len(data)
            default_getter = (
                getattr(self.get_data_type, "__func__", None)
                is OneOfSchema.get_data_type
            )
            for idx, item in enumerate(data):
                if default_getter:
                    tval = item.get(self.type_field)
                    if (
                        self.type_field_remove
                        and tval is not None
                        and self.type_field in item
                    ):
                        data_for_schema = _HidingKeyDict(item, self.type_field)
                    else:
                        data_for_schema = item
                else:
                    data_for_schema = dict(item)
                    try:
                        tval = self.get_data_type(data_for_schema)
                    except Exception:
                        result_errors[idx] = {self.type_field: ["Invalid data"]}
                        results[idx] = None
                        continue
                try:
                    groups[tval].append((idx, data_for_schema))
                except TypeError:
                    result_errors[idx] = {self.type_field: [f"Invalid value: {tval}"]}
                    results[idx] = None
                    continue
            for tval, items in groups.items():
                if tval is None:
                    for idx, _ in items:
                        result_errors[idx] = {
                            self.type_field: ["Missing data for required field."]
                        }
                        results[idx] = None
                    continue
                try:
                    type_schema = self.type_schemas.get(tval)
                except TypeError:
                    for idx, _ in items:
                        result_errors[idx] = {
                            self.type_field: [f"Invalid value: {tval}"]
                        }
                        results[idx] = None
                    continue
                if not type_schema:
                    for idx, _ in items:
                        result_errors[idx] = {
                            self.type_field: [f"Unsupported value: {tval}"]
                        }
                        results[idx] = None
                    continue
                if isinstance(type_schema, Schema):
                    schema = type_schema
                else:
                    if self._foo_context_isolation_enabled():
                        schema = type_schema()
                        self._foo_keepalive_append(schema)
                    elif self._foo_aggressive_enabled():
                        cache = self._foo_get_instance_cache()
                        schema = cache.get(tval)
                        if schema is None:
                            schema = type_schema()
                            self._foo_keepalive_append(schema)
                            cache[tval] = schema
                    else:
                        schema = type_schema()
                        self._foo_keepalive_append(schema)
                if hasattr(schema, "context"):
                    src_ctx = getattr(self, "context", {})
                    if schema.context != src_ctx:
                        try:
                            schema.context.clear()
                        except Exception:
                            schema.context = {}
                        schema.context.update(src_ctx)
                batch = []
                indices = []
                for idx, prepared in items:
                    batch.append(prepared)
                    indices.append(idx)
                try:
                    loaded = schema.load(
                        batch, many=True, partial=partial, unknown=unknown, **kwargs
                    )
                    for i, val in zip(indices, loaded, strict=False):
                        results[i] = val
                except ValidationError as e:
                    msgs = e.messages
                    vdata = getattr(e, "valid_data", None)
                    for pos, i in enumerate(indices):
                        if isinstance(msgs, dict) and pos in msgs and msgs[pos]:
                            result_errors[i] = msgs[pos]
                            results[i] = None
                        elif isinstance(msgs, list) and pos < len(msgs) and msgs[pos]:
                            result_errors[i] = msgs[pos]
                            results[i] = None
                        else:
                            if isinstance(vdata, list) and pos < len(vdata):
                                results[i] = vdata[pos]
                            else:
                                results[i] = results[i]
            for i in range(len(data)):
                result_data.append(results[i])
        result = result_data
        errors = result_errors
        if not errors:
            return result
        else:
            exc = ValidationError(errors, data=data, valid_data=result)
            raise exc

    def _load(self, data, *, partial=None, unknown=None, **kwargs):
        if not isinstance(data, dict):
            raise ValidationError({"_schema": f"Invalid data type: {data}"})
        default_getter = (
            getattr(self.get_data_type, "__func__", None) is OneOfSchema.get_data_type
        )
        if default_getter:
            data_type = data.get(self.type_field)
            if (
                self.type_field_remove
                and data_type is not None
                and self.type_field in data
            ):
                data = _HidingKeyDict(data, self.type_field)
            unknown = unknown or self.unknown
        else:
            data = dict(data)
            unknown = unknown or self.unknown
            data_type = self.get_data_type(data)
        if data_type is None:
            raise ValidationError(
                {self.type_field: ["Missing data for required field."]}
            )
        try:
            type_schema = self.type_schemas.get(data_type)
        except TypeError as error:
            raise ValidationError(
                {self.type_field: [f"Invalid value: {data_type}"]}
            ) from error
        if not type_schema:
            raise ValidationError(
                {self.type_field: [f"Unsupported value: {data_type}"]}
            )
        if isinstance(type_schema, Schema):
            schema = type_schema
        else:
            if self._foo_context_isolation_enabled():
                schema = type_schema()
                self._foo_keepalive_append(schema)
            elif self._foo_aggressive_enabled():
                cache = self._foo_get_instance_cache()
                schema = cache.get(data_type)
                if schema is None:
                    schema = type_schema()
                    self._foo_keepalive_append(schema)
                    cache[data_type] = schema
            else:
                schema = type_schema()
                self._foo_keepalive_append(schema)
        if hasattr(schema, "context"):
            src_ctx = getattr(self, "context", {})
            if schema.context != src_ctx:
                try:
                    schema.context.clear()
                except Exception:
                    schema.context = {}
                schema.context.update(src_ctx)
        return schema.load(data, many=False, partial=partial, unknown=unknown, **kwargs)

    def validate(self, data, *, many=None, partial=None):
        try:
            self.load(data, many=many, partial=partial)
        except ValidationError as ve:
            return ve.messages
        return {}

    # Internal helpers
    def _foo_keepalive_append(self, obj) -> None:
        if not self._foo_context_isolation_enabled():
            return
        lst = getattr(self, "_foo_keepalive", None)
        if lst is None:
            lst = []
            self._foo_keepalive = lst
        lst.append(obj)
        if len(lst) > self._foo_keepalive_limit:
            del lst[0]
