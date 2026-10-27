import pytest
from marshmallow import Schema, ValidationError, fields, pre_dump

from marshmallow_fastoneofschema import OneOfSchema


class Item:
    def __init__(self, v):
        self.v = v


class ItemSchema(Schema):
    v = fields.Integer()

    @pre_dump
    def reject_negative(self, obj, **kwargs):
        if obj.v < 0:
            raise ValidationError("negative")
        return obj


class ItemUnion(OneOfSchema):
    type_schemas = {"Item": ItemSchema}


def test_dump_many_failed_batch_keeps_good_items():
    with pytest.raises(ValidationError) as ei:
        ItemUnion().dump([Item(1), Item(-1), Item(3)], many=True)
    assert ei.value.messages == {1: {"_schema": ["negative"]}}
    assert ei.value.valid_data == [
        {"v": 1, "type": "Item"},
        None,
        {"v": 3, "type": "Item"},
    ]
