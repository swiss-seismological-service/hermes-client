import enum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator
from rich.pretty import pretty_repr
from shapely import Polygon, from_wkt


class Model(BaseModel):
    def __str__(self):
        return pretty_repr(self)

    def __repr__(self):
        return self.__str__()

    model_config = ConfigDict(
        arbitrary_types_allowed=True)


class EStatus(str, enum.Enum):
    PENDING = 'PENDING'
    SCHEDULED = 'SCHEDULED'
    PAUSED = 'PAUSED'
    RUNNING = 'RUNNING'
    CANCELLED = 'CANCELLED'
    FAILED = 'FAILED'
    COMPLETED = 'COMPLETED'


class ForecastSeries(Model):
    oid: UUID | None = None
    project_oid: UUID | None = None
    name: str | None = None
    description: str | None = None
    status: EStatus | None = None
    bounding_polygon: Polygon | None = None
    depth_min: float | None = None
    depth_max: float | None = None
    tags: list[str] | None = None
    seismicityobservation_required: str | None = None
    injectionobservation_required: str | None = None
    fdsnws_url: str | None = None
    hydws_url: str | None = None
    creationinfo: dict | None = None

    @field_validator('bounding_polygon', mode='before')
    @classmethod
    def validate_bounding_polygon(cls, value: str) -> Self:
        if isinstance(value, str):
            return from_wkt(value)

        return value
