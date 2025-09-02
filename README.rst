===========================
marshmallow-FastOneOfSchema
===========================

.. |marshmallow-support| image:: https://badgen.net/badge/marshmallow/3,4?list=1
    :target: https://marshmallow.readthedocs.io/en/latest/upgrading.html
    :alt: marshmallow 3|4 compatible

An extension to marshmallow to support fast schema (de)multiplexing.

marshmallow is a fantastic library for serialization and deserialization of data.
For more on that project see its `GitHub <https://github.com/marshmallow-code/marshmallow>`_
page or its `Documentation <http://marshmallow.readthedocs.org/en/latest/>`_.

This library adds a special kind of schema that actually multiplexes other schemas
based on object type. When serializing values, it uses get_obj_type() method
to get object type name. Then it uses ``type_schemas`` name-to-Schema mapping
to get schema for that particular object type, serializes object using that
schema and adds an extra field with name of object type. Deserialization is reverse.

Installing
----------

This fork is designed to be a drop‑in replacement for ``marshmallow-oneofschema``.

Using uv:

    $ uv add marshmallow-fastoneofschema

Using poetry::

    $ poetry add marshmallow-fastoneofschema

pip::

    $ pip install marshmallow-fastoneofschema

Example
-------

The code below demonstrates how to set up a polymorphic schema. For the full context check out the tests.
Once setup the schema should act like any other schema. If it does not then please file an Issue.

.. code:: python

    import marshmallow
    import marshmallow.fields
    from marshmallow_fastoneofschema import OneOfSchema


    class Foo:
        def __init__(self, foo):
            self.foo = foo


    class Bar:
        def __init__(self, bar):
            self.bar = bar


    class FooSchema(marshmallow.Schema):
        foo = marshmallow.fields.String(required=True)

        @marshmallow.post_load
        def make_foo(self, data, **kwargs):
            return Foo(**data)


    class BarSchema(marshmallow.Schema):
        bar = marshmallow.fields.Integer(required=True)

        @marshmallow.post_load
        def make_bar(self, data, **kwargs):
            return Bar(**data)


    class MyUberSchema(OneOfSchema):
        type_schemas = {"foo": FooSchema, "bar": BarSchema}

        def get_obj_type(self, obj):
            if isinstance(obj, Foo):
                return "foo"
            elif isinstance(obj, Bar):
                return "bar"
            else:
                raise Exception("Unknown object type: {}".format(obj.__class__.__name__))


    MyUberSchema().dump([Foo(foo="hello"), Bar(bar=123)], many=True)
    # => [{'type': 'foo', 'foo': 'hello'}, {'type': 'bar', 'bar': 123}]

    MyUberSchema().load(
        [{"type": "foo", "foo": "hello"}, {"type": "bar", "bar": 123}], many=True
    )
    # => [Foo('hello'), Bar(123)]

By default get_obj_type() returns obj.__class__.__name__, so you can just reuse that
to save some typing:

.. code:: python

    class MyUberSchema(OneOfSchema):
        type_schemas = {"Foo": FooSchema, "Bar": BarSchema}

You can customize type field with `type_field` class property:

.. code:: python

    class MyUberSchema(OneOfSchema):
        type_field = "object_type"
        type_schemas = {"Foo": FooSchema, "Bar": BarSchema}


    MyUberSchema().dump([Foo(foo="hello"), Bar(bar=123)], many=True)
    # => [{'object_type': 'Foo', 'foo': 'hello'}, {'object_type': 'Bar', 'bar': 123}]

You can use resulting schema everywhere marshmallow.Schema can be used, e.g.

.. code:: python

    import marshmallow as m
    import marshmallow.fields as f


    class MyOtherSchema(m.Schema):
        items = f.List(f.Nested(MyUberSchema))

License
-------

MIT licensed. See the bundled `LICENSE <https://github.com/Kalepa/marshmallow-fastoneofschema/blob/main/LICENSE>`_ file for more details.

Performance & Compatibility Notes
---------------------------------

- This fork preserves the public API and error shapes of the upstream package.
- Optimizations avoid unnecessary copies when ``type_field_remove`` is ``False`` and reduce overhead for ``many=True`` in default configurations.
- Aggressive instance caching can be disabled via ``FOO_DISABLE_AGGRESSIVE_MODE=1`` if needed.
- Supported Python versions: 3.11+.

DeepFriedMarshmallow Plugin
---------------------------

This fork ships a DFM plugin that can enable JIT inlining for ``Nested(OneOfSchema)`` fields.

- Discovery: via entry point group ``deepfriedmarshmallow.plugins`` or env ``DFM_PLUGINS``.
- Initial scope: Only engages when ``get_data_type``/``get_obj_type`` are default and all ``type_schemas`` keys are strings.
- Fallback: If conditions aren't met, DFM falls back to its standard generation.

Per‑Schema Controls & Flags
---------------------------

Migration
---------

Basic usage stays the same (plug‑and‑play). For projects that want to migrate explicitly to the new names:

- Replace dependency ``marshmallow-oneofschema`` with this fork.
- Optionally switch imports to the new package/class names:
  - ``from marshmallow_fastoneofschema import FastOneOfSchema``
  - Or keep ``from marshmallow_oneofschema import OneOfSchema`` (alias provided).
  - Existing code continues to work; new names are recommended for clarity.

- Env flags:
  - ``FOO_DISABLE_AGGRESSIVE_MODE=1``: disable instance caching.
  - ``FOO_CONTEXT_ISOLATION=1``: enable per-task schema instance caching (ContextVars).
- Per-schema overrides via ``class Meta: fastoneof = {...}``:
  - ``aggressive_mode: bool``
  - ``context_isolation: bool``
- Per-request overrides via ContextVars (advanced):
  - ``OneOfSchema._foo_aggressive_ctx.set(True|False)``
  - ``OneOfSchema._foo_isolation_ctx.set(True|False)``
