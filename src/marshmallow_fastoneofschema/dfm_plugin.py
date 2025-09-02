from __future__ import annotations


def dfm_register(registry) -> None:  # pragma: no cover - registration side effect
    try:
        from marshmallow import Schema, ValidationError, fields  # noqa: F401

        from .one_of_schema import OneOfSchema, _HidingKeyDict  # noqa: F401
    except Exception:
        return

    def factory(field_obj, context) -> str | tuple | None:
        try:
            from marshmallow import fields  # local import for safety

            if not isinstance(field_obj, fields.Nested):
                return None

            schema = field_obj.schema
            if callable(schema):
                schema = schema()
            if not isinstance(schema, OneOfSchema):
                return None
        except Exception:
            return None

        suffix = str(id(field_obj))
        parent_var = f"__dfm_oneof_parent_{suffix}"
        schema_var = f"__dfm_oneof_schema_{suffix}"
        func_name = f"__dfm_oneof_inline_{suffix}"
        cache_var = f"__dfm_oneof_cache_{suffix}"

        try:
            context.namespace[parent_var] = getattr(field_obj, "parent", None)
        except Exception:
            context.namespace[parent_var] = None
        context.namespace[schema_var] = schema
        context.namespace[cache_var] = {}

        dispatch_items = list(getattr(schema, "type_schemas", {}).items())
        dispatch_var = f"__dfm_oneof_dispatch_{suffix}"
        context.namespace[dispatch_var] = dispatch_items

        if context.is_serializing:

            def _inline_serialize(
                value,
                _schema_ref=schema_var,
                _parent_ref=parent_var,
                _dispatch_ref=dispatch_var,
            ):
                schema_obj = context.namespace[_schema_ref]
                parent_obj = context.namespace[_parent_ref]
                if value is None:
                    return None
                if hasattr(schema_obj, "context"):
                    try:
                        schema_obj.context.clear()
                    except Exception:
                        schema_obj.context = {}
                    if parent_obj is not None and hasattr(parent_obj, "context"):
                        schema_obj.context.update(getattr(parent_obj, "context", {}))

                if getattr(field_obj, "many", False):
                    res = []
                    for v in value:
                        res.append(schema_obj.dump(v))
                    return res
                return schema_obj.dump(value)

            context.namespace[func_name] = _inline_serialize
        else:

            def _inline_deserialize(
                value, _schema_ref=schema_var, _cache_ref=cache_var
            ):
                schema_obj: OneOfSchema = context.namespace[_schema_ref]
                local_cache: dict = context.namespace[_cache_ref]
                if value is None:
                    return None

                type_field = schema_obj.type_field
                remove = schema_obj.type_field_remove
                default_getter = (
                    getattr(schema_obj.get_data_type, "__func__", None)
                    is OneOfSchema.get_data_type
                )

                def _resolve_tv(obj):
                    try:
                        if default_getter:
                            tv = obj.get(type_field)
                        else:
                            tv = schema_obj.get_data_type(dict(obj) if remove else obj)
                    except Exception as err:
                        raise ValueError("hook failure") from err
                    return tv

                def _resolve_schema(tv):
                    inst = local_cache.get(tv)
                    if inst is not None:
                        return inst
                    try:
                        sub = schema_obj.type_schemas.get(tv)
                    except TypeError as err:
                        raise ValueError("unhashable type key") from err
                    if not sub:
                        raise ValueError("unsupported type")
                    if isinstance(sub, Schema):
                        inst = sub
                    else:
                        get_cache = getattr(schema_obj, "_foo_get_instance_cache", None)
                        if callable(get_cache):
                            cache = get_cache()
                            inst = cache.get(tv)
                            if inst is None:
                                inst = sub()
                                cache[tv] = inst
                        else:
                            inst = sub()
                    local_cache[tv] = inst
                    return inst

                def _apply_context(nested):
                    if hasattr(nested, "context"):
                        src_ctx = getattr(schema_obj, "context", {})
                        if nested.context != src_ctx:
                            try:
                                nested.context.clear()
                            except Exception:
                                nested.context = {}
                            nested.context.update(src_ctx)

                if getattr(field_obj, "many", False):
                    groups = {}
                    indices = {}
                    for idx, item in enumerate(value):
                        tv = _resolve_tv(item)
                        entry = groups.get(tv)
                        if entry is None:
                            entry = []
                            groups[tv] = entry
                            indices[tv] = []
                        if remove and tv is not None and type_field in item:
                            entry.append(_HidingKeyDict(item, type_field))
                        else:
                            entry.append(item)
                        indices[tv].append(idx)

                    results = [None] * len(value)
                    for tv, items in groups.items():
                        nested = _resolve_schema(tv)
                        _apply_context(nested)
                        unknown = getattr(field_obj, "unknown", None)
                        if unknown is not None:
                            loaded = nested.load(items, many=True, unknown=unknown)
                        else:
                            loaded = nested.load(items, many=True)
                        for pos, idx in enumerate(indices[tv]):
                            results[idx] = loaded[pos]
                    return results

                tv = _resolve_tv(value)
                nested = _resolve_schema(tv)
                _apply_context(nested)
                data_for_schema = value
                if remove and tv is not None and type_field in value:
                    data_for_schema = _HidingKeyDict(value, type_field)
                unknown = getattr(field_obj, "unknown", None)
                if unknown is not None:
                    return nested.load(data_for_schema, unknown=unknown)
                return nested.load(data_for_schema)

            context.namespace[func_name] = _inline_deserialize
        return f"{func_name}({{0}})"

    registry.register_field_inliner_factory(factory)
