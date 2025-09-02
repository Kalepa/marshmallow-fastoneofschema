import pytest
from marshmallow import Schema, ValidationError, fields

from marshmallow_fastoneofschema import OneOfSchema


class A(Schema):
    x = fields.Integer(required=True)


class B(Schema):
    y = fields.Integer(required=True)


class U(OneOfSchema):
    type_schemas = {"A": A, "B": B}


def test_invalid_input_type():
    u = U()
    with pytest.raises(ValidationError) as ei:
        u.load(["not", "a", "dict"])
    assert "_schema" in ei.value.messages


def test_missing_type_many():
    u = U()
    data = [{"x": 1}, {"y": 2}]
    with pytest.raises(ValidationError) as ei:
        u.load(data, many=True)
    msgs = ei.value.messages
    assert 0 in msgs and "type" in msgs[0]


def test_unhashable_type_many():
    u = U()
    # type value is a list -> unhashable
    data = [{"type": [1], "x": 1}]
    with pytest.raises(ValidationError) as ei:
        u.load(data, many=True)
    msgs = ei.value.messages
    assert 0 in msgs and "type" in msgs[0]
    assert "Invalid value" in msgs[0]["type"][0]


def test_unsupported_type_many():
    u = U()
    data = [{"type": "C", "x": 1}]
    with pytest.raises(ValidationError) as ei:
        u.load(data, many=True)
    msgs = ei.value.messages
    assert 0 in msgs and "type" in msgs[0]
    assert "Unsupported value" in msgs[0]["type"][0]


def test_missing_type_single():
    u = U()
    import pytest

    with pytest.raises(ValidationError) as ei:
        u.load({"x": 1})
    msgs = ei.value.messages
    assert "type" in msgs


def test_unsupported_type_single():
    u = U()
    import pytest

    with pytest.raises(ValidationError) as ei:
        u.load({"type": "C", "x": 1})
    msgs = ei.value.messages
    assert "type" in msgs and "Unsupported value" in msgs["type"][0]
