from marshmallow import Schema, fields

from marshmallow_fastoneofschema import OneOfSchema


class A(Schema):
    x = fields.Integer(required=True)


class B(Schema):
    y = fields.Integer(required=True)


class U(OneOfSchema):
    type_schemas = {"A": A, "B": B}


def test_validate_returns_empty_on_valid():
    s = U()
    assert s.validate({"type": "A", "x": 1}) == {}


def test_validate_returns_messages_on_invalid_single():
    s = U()
    msgs = s.validate({"type": "A"})
    assert "x" in msgs


def test_validate_returns_messages_on_invalid_many():
    s = U()
    data = [{"type": "A"}, {"type": "B", "y": 2}]
    msgs = s.validate(data, many=True)
    assert 0 in msgs and "x" in msgs[0]
    assert 1 not in msgs  # second is valid
