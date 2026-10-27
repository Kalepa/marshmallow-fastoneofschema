import asyncio

import pytest
from marshmallow import Schema, fields, post_dump, post_load

from marshmallow_fastoneofschema import OneOfSchema


class CacheProbeSchema(Schema):
    name = fields.String(required=True)

    @post_load
    def attach_schema_id(self, data, **kwargs):
        data["schema_id"] = id(self)
        return data


class IsoOn(OneOfSchema):
    class Meta:
        fastoneof = {"context_isolation": True}

    type_schemas = {"dog": CacheProbeSchema}


class IsoOff(OneOfSchema):
    class Meta:
        fastoneof = {"context_isolation": False}

    type_schemas = {"dog": CacheProbeSchema}


async def _task_ids(schema):
    a = schema.load({"type": "dog", "name": "a"})
    b = schema.load({"type": "dog", "name": "b"})
    return a["schema_id"], b["schema_id"]


def test_context_isolation_enabled_creates_distinct_instances():
    s = IsoOn()

    async def run():
        ra = await _task_ids(s)
        rb = await _task_ids(s)
        return ra, rb

    ra, rb = asyncio.run(run())
    assert ra[0] != rb[0]


@pytest.mark.skip(
    reason="No shared-instance guarantee without isolation; races may create separate instances."
)
def test_context_isolation_disabled_shares_instances():
    s = IsoOff()

    async def run():
        ra = await _task_ids(s)
        rb = await _task_ids(s)
        return ra, rb

    ra, rb = asyncio.run(run())
    assert ra[0] == rb[0]


class Pet:
    pass


class DumpProbeSchema(Schema):
    seen: list[Schema] = []

    @post_dump
    def record_instance(self, data, **kwargs):
        # Keep a reference so a freed instance's id() cannot be reused
        self.seen.append(self)
        return data


class DumpIsoOn(OneOfSchema):
    class Meta:
        fastoneof = {"context_isolation": True}

    type_schemas = {"Pet": DumpProbeSchema}


class DumpAggressiveOff(OneOfSchema):
    class Meta:
        fastoneof = {"aggressive_mode": False}

    type_schemas = {"Pet": DumpProbeSchema}


@pytest.mark.parametrize("schema_cls", [DumpIsoOn, DumpAggressiveOff])
def test_dump_does_not_reuse_child_instance(schema_cls):
    DumpProbeSchema.seen.clear()
    s = schema_cls()
    for _ in range(3):
        s.dump(Pet())
    assert len({id(x) for x in DumpProbeSchema.seen}) == 3
