from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from rich.pretty import pretty_repr
from shapely import Polygon, from_wkt


class Model(BaseModel):
    def __str__(self):
        return pretty_repr(self)

    def __repr__(self):
        return self.__str__()

    model_config = ConfigDict(
        arbitrary_types_allowed=True)


class ForecastSeries(Model):
    oid: UUID | None = None
    project_oid: UUID | None = None
    name: str | None = None
    description: str | None = None
    status: str | None = None
    bounding_polygon: Polygon | None = None
    depth_min: float | None = None
    depth_max: float | None = None
    tags: list[str] | None = None
    seismicityobservation_required: str | None = None
    injectionobservation_required: str | None = None
    fdsnws_url: str | None = None
    hydws_url: str | None = None
    creationinfo: dict | None = None
    injectionplans: list[str] | None = None
    modelconfigs: list[str] | None = None

    observation_starttime: datetime | None = None
    observation_endtime: datetime | None = None
    observation_window: int | None = None

    @field_validator('bounding_polygon', mode='before')
    @classmethod
    def validate_bounding_polygon(cls, value: str) -> Self:
        if isinstance(value, str):
            return from_wkt(value)
        return value

    @field_validator('injectionplans', mode='before')
    @classmethod
    def validate_injectionplans(cls,
                                value: list[dict] | None) -> Self:
        if value is None:
            return None
        value = sorted([v['name'] for v in value])
        return value

    @field_validator('modelconfigs', mode='before')
    @classmethod
    def validate_modelconfigs(cls,
                              value: list[dict] | None) -> Self:
        if value is None:
            return None
        value = sorted([v['name'] for v in value])
        return value


class InjectionPlanTemplate(Model):
    oid: UUID | None = None
    name: str | None = None
    borehole_hydraulics: dict | None = None


class ModelConfig(Model):
    oid: UUID | None = None
    name: str | None = None
    enabled: bool = True
    description: str | None = None
    result_type: str | None = None
    sfm_module: str | None = None
    sfm_function: str | None = None
    last_modified: datetime | None = None

    model_parameters: dict = {}

    tags: list[str] = []


class ForecastInfo(Model):
    oid: UUID | None = None

    status: str | None = None

    starttime: datetime | None = None
    endtime: datetime | None = None
    creationinfo: dict | None = None

    injectionplans: list[str] | None = None
    modelconfigs: list[str] | None = None

    @field_validator('injectionplans', mode='before')
    @classmethod
    def validate_injectionplans(cls,
                                value: list[dict] | None) -> Self:
        if value is None:
            return None
        value = sorted([v['name'] for v in value])
        return value

    @field_validator('modelconfigs', mode='before')
    @classmethod
    def validate_modelconfigs(cls,
                              value: list[dict] | None) -> Self:
        if value is None:
            return None
        value = sorted([v['name'] for v in value])
        return value


class ModelRunInfo(Model):
    oid: UUID | None = None
    injectionplan: str | None = None
    modelconfig: str | None = None
    status: str | None = None
    result_type: str | None = None

    @field_validator('injectionplan', mode='before')
    @classmethod
    def validate_injectionplan(cls,
                               value: dict | None) -> Self:
        if value is None:
            return None
        value = value['name']
        return value

    @field_validator('modelconfig', mode='before')
    @classmethod
    def validate_modelconfig(cls,
                             value: dict | None) -> Self:
        if value is None:
            return None
        value = value['name']
        return value

    @model_validator(mode='before')
    @classmethod
    def get_result_type(cls, data: Any) -> Any:
        if isinstance(data, dict) and 'modelconfig' in data:
            if 'result_type' in data['modelconfig']:
                data['result_type'] = data['modelconfig']['result_type']
        return data
