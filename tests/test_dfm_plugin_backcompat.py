import importlib
import os

import pytest
from marshmallow import Schema, ValidationError, fields, post_load

from marshmallow_fastoneofschema import OneOfSchema

# Skip this test module entirely if DeepFriedMarshmallow is unavailable
pytest.importorskip(
    "deepfriedmarshmallow",
    reason="DeepFriedMarshmallow not installed; skipping DFM backcompat tests",
)


def _enable_dfm_with_oneof_plugin():
    # Ensure OneOf plugin can be discovered by DFM
    os.environ.pop("DFM_DISABLE_AUTO_PLUGINS", None)
    os.environ["DFM_PLUGINS"] = "marshmallow_oneofschema.dfm_plugin:dfm_register"

    # Refresh the plugin registry and enable DFM's JIT for marshmallow
    from deepfriedmarshmallow.jit import plugins as dfm_plugins

    importlib.reload(dfm_plugins)
    dfm_plugins.discover_plugins()

    from deepfriedmarshmallow import deep_fry_marshmallow

    deep_fry_marshmallow()


class Dog:
    def __init__(self, name):
        self.name = name


class Cat:
    def __init__(self, name):
        self.name = name


class DogSchema(Schema):
    name = fields.String(required=True)

    @post_load
    def make(self, data, **kwargs):
        return Dog(**data)


class CatSchema(Schema):
    name = fields.String(required=True)

    @post_load
    def make(self, data, **kwargs):
        return Cat(**data)


class MyOneOf(OneOfSchema):
    type_schemas = {"dog": DogSchema, "cat": CatSchema}


def test_dfm_plugin_backcompat_basic_roundtrip(monkeypatch):
    # Baseline without DFM
    s0 = MyOneOf()
    inp = {"type": "dog", "name": "Rex"}
    out0 = s0.dump(s0.load(inp))

    # With DFM + plugin
    _enable_dfm_with_oneof_plugin()
    s1 = MyOneOf()
    out1 = s1.dump(s1.load(inp))

    assert out0 == out1


def test_dfm_plugin_backcompat_many_errors(monkeypatch):
    # Baseline
    s0 = MyOneOf()
    bad = [
        {"name": "NoType"},  # missing type
        {"type": "frog", "name": "Unsupported"},  # unsupported
    ]
    with pytest.raises(ValidationError) as e0:
        s0.load(bad, many=True)
    msgs0 = e0.value.messages

    # With DFM + plugin
    _enable_dfm_with_oneof_plugin()
    s1 = MyOneOf()
    with pytest.raises(ValidationError) as e1:
        s1.load(bad, many=True)
    msgs1 = e1.value.messages

    assert msgs0 == msgs1


def test_dfm_plugin_backcompat_custom_hook(monkeypatch):
    # Custom hook schema
    class Hooked(OneOfSchema):
        type_field = "k"
        type_schemas = {"dog": DogSchema, "cat": CatSchema}

        def get_data_type(self, data):
            # Preserve upstream semantics
            v = data.get(self.type_field)
            if self.type_field in data and self.type_field_remove:
                data.pop(self.type_field)
            return v

    payload = {"k": "cat", "name": "Mimi"}

    # Baseline
    b = Hooked()
    out0 = b.dump(b.load(payload))

    # With DFM + plugin
    _enable_dfm_with_oneof_plugin()
    j = Hooked()
    out1 = j.dump(j.load(payload))

    assert out0 == out1


def test_dfm_plugin_backcompat_dump_many(monkeypatch):
    # Prepare objects
    dogs_and_cats = [Dog("Rex"), Cat("Mimi"), Dog("Fido")]

    # Baseline
    s0 = MyOneOf()
    out0 = s0.dump(dogs_and_cats, many=True)

    # DFM + plugin
    _enable_dfm_with_oneof_plugin()
    s1 = MyOneOf()
    out1 = s1.dump(dogs_and_cats, many=True)

    assert out0 == out1


def test_dfm_plugin_backcompat_custom_type_field_name(monkeypatch):
    class MyOneOfKind(OneOfSchema):
        type_field = "kind"
        type_schemas = {"dog": DogSchema, "cat": CatSchema}

    # Baseline
    s0 = MyOneOfKind()
    out0 = s0.dump([Dog("Rex"), Cat("Mimi")], many=True)

    # DFM + plugin
    _enable_dfm_with_oneof_plugin()
    s1 = MyOneOfKind()
    out1 = s1.dump([Dog("Rex"), Cat("Mimi")], many=True)

    assert out0 == out1
