from enum import Enum

import pytest
from marshmallow import EXCLUDE, Schema, ValidationError, fields

from marshmallow_fastoneofschema import OneOfSchema


class DumpFoo:
    def __init__(self, v):
        self.v = v


class DumpFooSchema(Schema):
    v = fields.Integer(required=True)


class DumpBar:
    def __init__(self, v):
        self.v = v


class DumpBarSchema(Schema):
    v = fields.Integer(required=True)


class DumpOneOf(OneOfSchema):
    type_schemas = {"DumpFoo": DumpFooSchema, "DumpBar": DumpBarSchema}


def test_dump_unsupported_type_single_raises_validationerror():
    class Unknown:
        pass

    s = DumpOneOf()
    with pytest.raises(ValidationError) as ei:
        s.dump(Unknown())
    assert "_schema" in ei.value.messages


def test_dump_many_collects_errors_for_unsupported_types():
    data = [DumpFoo(1), object(), DumpBar(2)]
    s = DumpOneOf()
    with pytest.raises(ValidationError) as ei:
        s.dump(data, many=True)
    msgs = ei.value.messages
    assert 1 in msgs and "_schema" in msgs[1]


class UChildUnknownExclude(Schema):
    class Meta:
        unknown = EXCLUDE

    a = fields.Integer(required=True)


class UChildUnknownRaise(Schema):
    a = fields.Integer(required=True)


class UUnknown(OneOfSchema):
    type_schemas = {"X": UChildUnknownExclude, "Y": UChildUnknownRaise}


def test_child_meta_unknown_exclude_preserved_when_parent_unknown_not_set():
    s = UUnknown()
    res = s.load({"type": "X", "a": 1, "extra": "ignored"})
    assert res == {"a": 1}


def test_parent_unknown_raise_overrides_child_meta_unknown():
    s = UUnknown()
    with pytest.raises(ValidationError) as ei:
        s.load({"type": "X", "a": 1, "extra": "boom"}, unknown="raise")
    msgs = ei.value.messages
    assert "Unknown field" in msgs.get("extra", [""])[0]


class MyStrEnum(str, Enum):
    A = "A"
    B = "B"


class EnumSchemaA(Schema):
    v = fields.Integer(required=True)


class EnumSchemaB(Schema):
    v = fields.Integer(required=True)


class EnumKeysOneOf(OneOfSchema):
    type_schemas = {MyStrEnum.A: EnumSchemaA, MyStrEnum.B: EnumSchemaB}


def test_enum_keys_accept_string_values_on_load():
    s = EnumKeysOneOf()
    out = s.load({"type": "A", "v": 3})
    assert out == {"v": 3}


class SimpleObj:
    def __init__(self, a, b):
        self.a = a
        self.b = b


class SimpleSchema(Schema):
    a = fields.Integer(required=True)
    b = fields.Integer(required=True)


class ExcludableLike(OneOfSchema):
    type_schemas = {"S": SimpleSchema}

    def __init__(self, *args, **kwargs):
        self._schema_args = args
        self._schema_kwargs = kwargs
        self._schema_kwargs["exclude_original"] = kwargs.get("exclude")
        self.type_schemas = {
            k: self._with_args(v) for k, v in self.type_schemas.items()
        }
        super().__init__()

    def _with_args(self, schema_cls):
        def init_schema():
            kw = {
                k: v for k, v in self._schema_kwargs.items() if k != "exclude_original"
            }
            if self._schema_kwargs.get("exclude_original"):
                kw["exclude"] = self._schema_kwargs["exclude_original"]
            return schema_cls(*self._schema_args, **kw)

        return init_schema

    def get_obj_type(self, obj):
        return "S" if isinstance(obj, SimpleObj) else None


def test_callable_type_schema_and_exclude_forwarding_on_dump():
    s = ExcludableLike(exclude=("b",))
    obj = SimpleObj(1, 2)
    out = s.dump(obj)
    assert out == {"type": "S", "a": 1}


class ChildSetsTypeSchema(Schema):
    type = fields.String()
    a = fields.Integer(required=True)

    def dump(self, obj, *, many=None, **kwargs):
        return {"type": "CUSTOM", "a": obj.a}


class OneOfWithChildType(OneOfSchema):
    type_field = "type"
    type_field_remove = False
    type_schemas = {"S": ChildSetsTypeSchema}

    def get_obj_type(self, obj):
        return "S"


def test_dump_does_not_override_child_type_field():
    obj = SimpleObj(1, 2)
    out = OneOfWithChildType().dump(obj)
    assert out == {"type": "CUSTOM", "a": 1}
