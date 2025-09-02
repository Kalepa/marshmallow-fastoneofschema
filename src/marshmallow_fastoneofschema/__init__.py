from importlib.metadata import PackageNotFoundError, version

from .one_of_schema import OneOfSchema as FastOneOfSchema

__all__ = ["OneOfSchema", "FastOneOfSchema", "__version__"]

from .one_of_schema import OneOfSchema as OneOfSchema

try:
    __version__ = version("marshmallow-fastoneofschema")
except PackageNotFoundError:
    __version__ = "0+unknown"
