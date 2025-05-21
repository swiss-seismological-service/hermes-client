import json
import logging
from abc import ABC, abstractmethod
from uuid import UUID

import requests
from hydws.parser import BoreholeHydraulics
from seismostats import Catalog

from hermes_client.utils import (NoContent, RequestsError, make_request,
                                 rates_to_seismostats)


class BaseClient(ABC):
    @abstractmethod
    def __init__(self):
        pass

    def _make_api_request(self, request_url: str, params: dict = {}):
        try:
            response = make_request(
                requests.get,
                request_url,
                params,
                self._timeout,
                nocontent_codes=(
                    204,
                    404))

        except NoContent:
            self.logger.warning('No data received.')
            return {}
        except RequestsError as err:
            self.logger.error(f"Request Error while fetching data ({err}).")
        except BaseException as err:
            self.logger.error(f"Error while fetching data {err}")
        else:
            self.logger.info('Data received.')
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return response


class HermesClient(BaseClient):
    def __init__(self,
                 url: str,
                 timeout: int = None):
        """
        Initialize Class.

        Args:
            url:        URL of the hermes webservice
            timeout:    after how long, contacting the webservice should
                        be aborted
        """
        self.url = f'{url}/v1'
        self._timeout = timeout
        self.logger = logging.getLogger(__name__)

    def list_projects(self):
        """
        List all projects.

        Returns:
            list: list of projects
        """
        request_url = f'{self.url}/projects'
        data = self._make_api_request(request_url)

        return data

    def list_forecastseries(self, project: UUID | str):
        """
        List all ForecastSeries for a project.

        Args:
            project: oid or name of the project.

        Returns:
            All ForecastSeries for the project.
        """

        try:
            if not isinstance(project, UUID):
                UUID(project)
        except ValueError:
            request_url = f'{self.url}/projects'
            data = self._make_api_request(request_url)
            project = next((p['oid'] for p in data if p['name'] == project),
                           None)

        request_url = f'{self.url}/projects/{str(project)}/forecastseries'
        data = self._make_api_request(request_url)

        return data

    def list_modelconfigs(self):
        """
        List all model configurations.

        Returns:
            list: list of model configurations
        """
        request_url = f'{self.url}/modelconfigs'
        data = self._make_api_request(request_url)

        return data


class ForecastSeriesClient(BaseClient):
    def __init__(self,
                 url: str,
                 forecastseries: UUID | str | None = None,
                 project: UUID | str | None = None,
                 timeout: int = None) -> None:
        """
        Initialize Class.
        :param url:     URL of the hermes webservice
        :param timeout: after how long, contacting the webservice should
                        be aborted
        """
        self.url = f'{url}/v1'
        self._timeout = timeout
        self.logger = logging.getLogger(__name__)

        self.metadata = self._get_forecastseries_data(forecastseries, project)

    def _get_forecastseries_data(self,
                                 forecastseries: UUID | str | None = None,
                                 project: UUID | str | None = None):
        """
        Get a ForecastSeries.

        Either the ForecastSeries UUID must be provided, or both the
        ForecastSeries name and the project UUID or name.

        Args:
            forecastseries: oid or name of the forecast series.
            project:        oid or name of the project.

        Returns:
            The ForecastSeries.
        """
        try:
            # If forecastseries UUID is provided, directly return it.
            if not isinstance(forecastseries, UUID):
                UUID(forecastseries)
            request_url = f'{self.url}/forecastseries/{str(forecastseries)}'
            fs = self._make_api_request(request_url)
            if len(fs.keys()) == 0:
                raise ValueError(
                    'ForecastSeries not found. Please provide a valid '
                    'ForecastSeries name or UUID.')
            return fs
        except ValueError:
            if project is None:
                raise ValueError(
                    'Either ForecastSeries UUID must be provided, or both '
                    'the ForecastSeries name and the project UUID or name.')
            try:
                if not isinstance(project, UUID):
                    UUID(project)
                request_url = \
                    f'{self.url}/projects/{str(project)}/forecastseries'
                data = self._make_api_request(request_url)
                fs = next(
                    (fs for fs in data if fs['name'] == forecastseries),
                    None)
                return fs
            except ValueError:
                request_url = f'{self.url}/projects'
                data = self._make_api_request(request_url)
                project = next(
                    (p['oid'] for p in data if p['name'] == project),
                    None)
                if project is None:
                    raise ValueError(
                        'Project not found. Please provide a valid project '
                        'name or UUID.')
                request_url = \
                    f'{self.url}/projects/{str(project)}/forecastseries'
                data = self._make_api_request(request_url)
                fs = next(
                    (fs for fs in data if fs['name'] == forecastseries),
                    None)
                if fs is None:
                    raise ValueError(
                        'ForecastSeries not found. Please provide a valid '
                        'ForecastSeries name or UUID.')
                return fs

    @property
    def injectionplans(self):
        """
        List all injection plans for a forecast series.
        :return: list of injection plans
        """
        return self.metadata['injectionplans']

    def list_injectionplans(self):
        """
        List all injection plans for a forecast series.
        :return: list of injection plans
        """

        request_url = f'{self.url}/forecastseries/' \
            f'{self.forecastseries_id}/injectionplans'

        data = self._make_api_request(request_url)

        for injectionplan in data:
            injectionplan['borehole_hydraulics'] = \
                BoreholeHydraulics(injectionplan['borehole_hydraulics'])
            if 'oid' in injectionplan:
                injectionplan['id'] = injectionplan.pop('oid')
        return data

    @property
    def modelconfigs(self):
        """
        List all models for a forecast series.
        :return: list of models
        """
        return self.metadata['modelconfigs']

    def list_modelconfigs(self):
        """
        List all modelconfigs for a forecast series.
        :return: list of modelconfigs
        """

        request_url = f'{self.url}/forecastseries/' \
            f'{self.forecastseries_id}/modelconfigs'

        data = self._make_api_request(request_url)

        return data

    def get_forecast_seismicity(self, forecast_id: int):
        """
        Get seismicity for a forecast.
        :param forecast_id: id of the forecast
        :return: seismicity
        """
        request_url = \
            f'{self.url}/forecasts/{forecast_id}/seismicityobservations'

        data = self._make_api_request(request_url)

        return Catalog.from_quakeml(data, include_quality=True)

    def get_forecast_injectionwells(self, forecast_id: int):
        """
        Get hydraulics for a forecast.
        :param forecast_id: id of the forecast
        :return: hydraulics
        """
        request_url = \
            f'{self.url}/forecasts/{forecast_id}/injectionobservations'

        data = self._make_api_request(request_url)

        data = [BoreholeHydraulics(d) for d in data]

        return data

    # def list_forecasts_info(self, details=False) -> list[dict]:
    #     """
    #     Get all forecasts for a forecast series.
    #     :return: list of forecasts
    #     """

    #     request_url = \
    #         f'{self.url}/forecastseries/{self.forecastseries_id}/forecasts'

    #     data = self._make_api_request(request_url)

    #     if not details:
    #         data = [
    #             {k: d[k] for k in FORECAST_FIELDS if k in d} for d in data]

    #     for forecast in data:
    #         if 'oid' in forecast:
    #             forecast['id'] = forecast.pop('oid')

    #     return data

    def list_modelruns_info(self, forecast_id: int) -> list[dict]:
        """
        List all forecast modelruns for a forecast.
        :param forecast_id: id of the forecast
        :return: list of forecast modelruns
        """
        request_url = f'{self.url}/forecasts/{forecast_id}'

        data = self._make_api_request(request_url)

        modelruns = data['modelruns'] if 'modelruns' in data else []
        for mr in modelruns:
            for key in ('injectionplan_oid', 'modelconfig_oid', 'oid'):
                if key in mr:
                    mr[key.replace('oid', 'id')] = mr.pop(key)

        return modelruns

    def list_forecast_rates(self,
                            forecast_id: int,
                            modelconfigs: list[str] = None,
                            injectionplans: list[str] = None):
        """
        Get forecast rates for a forecast.
        :param forecast_id: id of the forecast
        :return: forecast rates
        """
        params = {}

        if modelconfigs:
            params['modelconfigs'] = modelconfigs
        if injectionplans:
            params['injectionplans'] = injectionplans

        request_url = f'{self.url}/forecasts/{forecast_id}/rates'
        data = self._make_api_request(request_url, params=params)

        for modelrun in data:
            rategrids = rates_to_seismostats(modelrun['rateforecasts'])

            modelrun['rateforecasts'] = rategrids

        return data

    def get_modelrun_rates(self, modelrun_id: int):
        """
        Get rates for a modelrun.
        :param modelrun_id: id of the modelrun
        :return: rates
        """
        request_url = f'{self.url}/modelruns/{modelrun_id}/rates'
        data = self._make_api_request(request_url)

        return rates_to_seismostats(data['rateforecasts'])

    def get_modelrun_injectionplan(self, modelrun_id: int):
        """
        Get injection plan for a modelrun.
        :param modelrun_id: id of the modelrun
        :return: injection plan
        """
        request_url = f'{self.url}/modelruns/{modelrun_id}/rates'

        data = self._make_api_request(request_url)
        injectionplan_id = data['injectionplan_oid']

        request_url = f'{self.url}/injectionplans/{injectionplan_id}'

        hydws_data = self._make_api_request(request_url)

        hyd = BoreholeHydraulics(hydws_data[0])

        return hyd

    def get_modelrun_modelconfig(self, modelrun_id: int):
        """
        Get model configuration for a modelrun.
        :param modelrun_id: id of the modelrun
        :return: model configuration
        """
        request_url = f'{self.url}/modelruns/{modelrun_id}/modelconfig'

        data = self._make_api_request(request_url)

        return data
