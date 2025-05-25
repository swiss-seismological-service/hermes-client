import logging
from datetime import datetime
from typing import Literal
from uuid import UUID

from hermes_client.base import BaseClient, NotFound
from hermes_client.forecast import ForecastClient
from hermes_client.hermes import HermesClient
from hermes_client.schemas import (ForecastSeries, InjectionPlanTemplate,
                                   ModelConfig)


class ForecastSeriesClient(BaseClient):
    """
    Client for the HERMES API to interact with ForecastSeries.

    Either the ForecastSeries UUID must be provided, or both the
    ForecastSeries name and the Project UUID or name.

    Args:
        url: Base URL of the HERMES API.
        forecastseries: UUID or name of the ForecastSeries.
        project: UUID or name of the Project.
        timeout: Timeout for API requests in seconds.
    """

    def __init__(self,
                 url: str,
                 forecastseries: UUID | str,
                 project: UUID | str | None = None,
                 timeout: int | None = None) -> None:
        self.url = url
        self._timeout = timeout
        self.logger = logging.getLogger(__name__)

        self._metadata = self._get_forecastseries(
            url, forecastseries, project)

        self._injectionplans = None
        self._modelconfigs = None
        self._forecasts = None

    def _get_forecastseries(self,
                            url: str,
                            forecastseries: UUID | str,
                            project: UUID | str | None = None):
        """
        Get a ForecastSeries.

        Either the ForecastSeries UUID must be provided, or both the
        ForecastSeries name and the project UUID or name.

        Args:
            url:            Base URL of the HERMES API.
            forecastseries: Name or oid of the ForecastSeries.
            project:        Name or oid of the Project.

        Returns:
            The ForecastSeries.
        """
        hermes = HermesClient(url=url, timeout=self._timeout)
        try:
            # If forecastseries UUID is provided, directly return it.
            if not isinstance(forecastseries, UUID):
                UUID(forecastseries)
            return hermes.get_forecastseries(forecastseries)
        except ValueError:
            if project is None:
                raise ValueError(
                    'Either ForecastSeries UUID must be provided, or both '
                    'the ForecastSeries name and the Project UUID or name.')

            fs_list = hermes.list_forecastseries(project)
            fs = next((fs for fs in fs_list
                       if fs['name'] == forecastseries), None)

            if fs is None:
                raise NotFound(
                    f'ForecastSeries with name "{forecastseries}" for Project '
                    f'"{project}" not found. Please provide a valid Project '
                    'and ForecastSeries name.')

            return fs

    @property
    def metadata(self) -> ForecastSeries:
        """
        General metadata of the ForecastSeries.
        """
        return ForecastSeries(**self._metadata)

    @property
    def modelsettings(self) -> dict:
        """
        Model settings which are passed to all models.
        """
        return self._metadata['model_settings'].copy()

    @property
    def injectionplans(self):
        """
        The InjectionPlans used for Forecasts.
        """
        if self._injectionplans is None:
            self._injectionplans = sorted(self._get_injectionplans(),
                                          key=lambda i: i['name'])

        return [InjectionPlanTemplate.model_validate(i)
                for i in self._injectionplans]

    def _get_injectionplans(self) -> dict:
        """
        Get all injection plans for the ForecastSeries.
        """

        request_url = f'{self.url}/v1/forecastseries/' \
            f'{self._metadata["oid"]}/injectionplans'

        data = self._get(request_url)

        return data

    @property
    def modelconfigs(self) -> list[ModelConfig]:
        """
        The ModelConfigs used for Forecasts.
        """
        if self._modelconfigs is None:
            self._modelconfigs = sorted(self._get_modelconfigs(),
                                        key=lambda m: m['name'])

        return [ModelConfig.model_validate(m)
                for m in self._modelconfigs]

    def _get_modelconfigs(self) -> dict:
        """
        Get all modelconfigs for the ForecastSeries.
        """

        request_url = f'{self.url}/v1/forecastseries/' \
            f'{self._metadata["oid"]}/modelconfigs'

        data = self._get(request_url)

        return data

    @property
    def forecasts(self) -> list[ForecastClient]:
        """
        Finished or still running Forecasts.
        """
        if self._forecasts is None:
            self._forecasts = \
                sorted([ForecastClient(self.url, f, self._timeout)
                        for f in self._get_forecasts()],
                       key=lambda f: f.metadata.starttime)

        return self._forecasts

    def _get_forecasts(self) -> dict:
        """
        Request all forecasts for the ForecastSeries.
        """

        request_url = f'{self.url}/v1/forecastseries/' \
            f'{self._metadata["oid"]}/forecasts'

        data = self._get(request_url)

        return data

    def get_forecast_by_time(self,
                             time: datetime,
                             method: Literal['nearest',
                                             'previous', 'next'] = 'nearest',
                             status: list[str] = ['COMPLETED']
                             ) -> ForecastClient | None:
        """
        Get a forecast by its starttime.

        Args:
            time:   The time to search for.
            method: The method to use for searching. Can be 'nearest',
                    'previous', or 'next'.
            status: The status of the forecast.

        Returns:
            The forecast that matches the time.
        """
        if self.forecasts in [None, []]:
            return None

        fc = [f for f in self.forecasts if f.metadata.status in status]

        if method == 'nearest':
            forecast = min(fc,
                           key=lambda f: abs(f.metadata.starttime - time))
        elif method == 'previous':
            forecast = max(
                (f for f in fc if f.metadata.starttime <= time),
                key=lambda f: f.metadata.starttime,
                default=None
            )
        elif method == 'next':
            forecast = min(
                (f for f in fc if f.metadata.starttime >= time),
                key=lambda f: f.metadata.starttime,
                default=None
            )
        else:
            raise ValueError(
                f"Invalid method '{method}'. "
                "Use 'nearest', 'previous', or 'next'."
            )
        return forecast
