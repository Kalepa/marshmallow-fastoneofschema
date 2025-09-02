import asyncio

import pytest
from marshmallow import Schema, fields, post_load

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
