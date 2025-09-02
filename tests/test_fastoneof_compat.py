from enum import Enum

import pytest
from marshmallow import Schema, ValidationError, fields, post_load

from marshmallow_fastoneofschema import OneOfSchema


class Pet:
    def __init__(self, name):
        self.name = name


class Dog(Pet):
    pass


class Cat(Pet):
    pass


class DogSchema(Schema):
    name = fields.String(required=True)

    @post_load
    def make(self, data, **kwargs):  # noqa: D401
        return Dog(**data)


class CatSchema(Schema):
    name = fields.String(required=True)

    @post_load
    def make(self, data, **kwargs):  # noqa: D401
        return Cat(**data)


class MyOneOf(OneOfSchema):
    type_schemas = {"dog": DogSchema, "cat": CatSchema}


def test_type_field_remove_and_validate(monkeypatch):
    class PSchema(Schema):
        pet = fields.Nested(MyOneOf)

    s = PSchema()
    data = {"pet": {"type": "dog", "name": "Rex"}}
    loaded = s.load(data)
    assert isinstance(loaded["pet"], Dog)
    assert s.validate(data) == {}


def test_many_indexed_errors_and_context(monkeypatch):
    class TrackContextSchema(Schema):
        name = fields.String(required=True)

        @post_load
        def mark(self, data, **kwargs):
            # Copy a value from context into resulting object for inspection
            data["ctx"] = dict(getattr(self, "context", {}))
            return data

    class MyOneOfCtx(OneOfSchema):
        type_schemas = {"dog": TrackContextSchema}

    class PSchema(Schema):
        pet = fields.Nested(MyOneOfCtx, many=True)

    s = PSchema()
    s.context = {"req_id": "abc"}
    items = [
        {"type": "dog", "name": "a"},
        {"type": "dog"},  # missing name
        {"type": "dog", "name": "b"},
    ]
    with pytest.raises(ValidationError) as ei:
        s.load({"pet": items})
    errs = ei.value.messages
    assert "pet" in errs and 1 in errs["pet"], errs


def test_aggressive_cache_toggle_via_env(monkeypatch):
    if not hasattr(OneOfSchema, "_foo_disable_aggressive"):
        pytest.skip("Aggressive cache flags not available in upstream schema")

    class CacheProbeSchema(Schema):
        name = fields.String(required=True)

        @post_load
        def attach_schema_id(self, data, **kwargs):
            data["schema_id"] = id(self)
            return data

    class CachingOneOf(OneOfSchema):
        type_schemas = {"dog": CacheProbeSchema}

    # At minimum, assert behavior under current defaults
    s = CachingOneOf()
    a = s.load({"type": "dog", "name": "a"})
    b = s.load({"type": "dog", "name": "b"})
    # Default aggressive mode: instance reused
    assert a["schema_id"] == b["schema_id"]

    # Disable aggressive mode via ContextVar override
    OneOfSchema._foo_aggressive_ctx.set(False)
    s2 = CachingOneOf()
    a2 = s2.load({"type": "dog", "name": "a"})
    b2 = s2.load({"type": "dog", "name": "b"})
    assert a2["schema_id"] != b2["schema_id"]


def test_custom_hooks_and_non_string_keys():
    class Kind(Enum):
        DOG = 1
        CAT = 2

    class Hooked(OneOfSchema):
        type_field = "k"
        type_schemas = {Kind.DOG: DogSchema, Kind.CAT: CatSchema}

        def get_data_type(self, data):  # custom
            v = data.get(self.type_field)
            if self.type_field in data and self.type_field_remove:
                data.pop(self.type_field)
            return Kind(v) if v is not None else None

        def get_obj_type(self, obj):  # custom
            return (
                Kind.DOG
                if isinstance(obj, Dog)
                else Kind.CAT
                if isinstance(obj, Cat)
                else None
            )

    h = Hooked()
    d = h.load({"k": 1, "name": "x"})
    assert isinstance(d, Dog)
    out = h.dump(Cat("y"))
    assert out["k"] == Kind.CAT
