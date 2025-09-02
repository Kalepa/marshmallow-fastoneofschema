from .one_of_schema import OneOfSchema  # noqa: F401
from .one_of_schema import OneOfSchema as FastOneOfSchema

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("marshmallow-fastoneofschema")
except PackageNotFoundError:
    __version__ = "0+unknown"
