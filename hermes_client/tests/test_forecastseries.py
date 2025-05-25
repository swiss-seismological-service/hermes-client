from datetime import datetime, timedelta
from uuid import UUID

import pytest

from hermes_client import ForecastSeriesClient
from hermes_client.base import NotFound
from hermes_client.schemas import (ForecastSeries, InjectionPlanTemplate,
                                   ModelConfig)


def test_forecastseries_client_init(fs_client: ForecastSeriesClient,
                                    base_url,
                                    project_ind,
                                    fs_ind,
                                    proj2_ind_oid
                                    ):
    fs_client = ForecastSeriesClient(
        url=base_url,
        forecastseries=fs_ind['name'],
        project=project_ind['oid']
    )
    assert fs_client.metadata.oid == UUID(fs_ind['oid'])

    fs_client = ForecastSeriesClient(
        url=base_url,
        forecastseries=fs_ind['oid']
    )
    assert fs_client.metadata.oid == UUID(fs_ind['oid'])

    fs_client = ForecastSeriesClient(
        url=base_url,
        forecastseries=fs_ind['name'],
        project=project_ind['name']
    )
    assert fs_client.metadata.oid == UUID(fs_ind['oid'])

    with pytest.raises(ValueError):
        fs_client = ForecastSeriesClient(
            url=base_url,
            forecastseries=fs_ind['name']
        )

    with pytest.raises(NotFound):
        fs_client = ForecastSeriesClient(
            url=base_url,
            forecastseries="nonexistent_fs",
            project=project_ind['oid']
        )

    with pytest.raises(NotFound):
        fs_client = ForecastSeriesClient(
            url=base_url,
            forecastseries="nonexistent_fs",
            project=proj2_ind_oid
        )


def test_forecastseries_properties(fs_client: ForecastSeriesClient,
                                   fs_ind,
                                   forecast_ind):
    assert isinstance(fs_client.metadata, ForecastSeries)

    assert fs_client.metadata.oid == UUID(fs_ind['oid'])
    assert fs_client.metadata.name == fs_ind['name']

    assert fs_ind['model_settings'] == fs_client.modelsettings

    assert len(fs_client.injectionplans) == 2
    assert isinstance(fs_client.injectionplans[0], InjectionPlanTemplate)

    assert len(fs_client.modelconfigs) == 2
    assert isinstance(fs_client.modelconfigs[0], ModelConfig)

    assert len(fs_client.forecasts) == 3
    assert fs_client.forecasts[0].metadata.oid == UUID(
        forecast_ind[0]['oid'])


def test_forecastseries_get_forecast(fs_client: ForecastSeriesClient,
                                     forecast_ind):
    t1 = datetime.fromisoformat(forecast_ind[0]['starttime'])
    t2 = datetime.fromisoformat(forecast_ind[1]['starttime'])
    time = t1 + (t2 - t1) / 2

    nearest = fs_client.get_forecast_by_time(time - timedelta(seconds=10))
    previous = fs_client.get_forecast_by_time(
        time, method='previous')
    next_ = fs_client.get_forecast_by_time(
        time, method='next')

    assert nearest.metadata.oid == UUID(forecast_ind[0]['oid'])
    assert previous.metadata.oid == UUID(forecast_ind[0]['oid'])
    assert next_.metadata.oid == UUID(forecast_ind[1]['oid'])

    with pytest.raises(ValueError):
        fs_client.get_forecast_by_time(
            time, method='invalid_method')

    fs_client._forecasts = []
    assert fs_client.get_forecast_by_time(
        time, method='nearest') is None
