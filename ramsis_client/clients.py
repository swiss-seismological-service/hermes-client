import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime

import requests
from hydws.parser import BoreholeHydraulics
from seismostats.seismicity.catalog import Catalog

from ramsis_client.utils import (NoContent, RequestsError, make_request,
                                 parse_datetime, rates_to_seismostats)


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


PROJECT_FIELDS = [
    'id',
    'name',
    'description',
    'starttime',
    'endtime',
    'creationtime']

FORECASTSERIES_FIELDS = [
    'id',
    'name',
    'starttime',
    'endtime',
    'creationtime',
    'forecastinterval',
    'status']

FORECAST_FIELDS = [
    'id',
    'starttime',
    'endtime',
    'status',
    'modelruns']


class RamsisClient(BaseClient):
    def __init__(self,
                 url: str,
                 timeout: int = None) -> None:
        """
        Initialize Class.
        :param url:     URL of the ramsis webservice
        :param timeout: after how long, contacting the webservice should
                        be aborted
        """
        self.url = f'{url}/v1'
        self._timeout = timeout
        self.logger = logging.getLogger(__name__)

    def list_projects(self, details: bool = False):
        """
        List all projects.
        :return: list of projects
        """
        request_url = f'{self.url}/projects'
        data = self._make_api_request(request_url)

        if not details:
            for project in data:
                project['creationtime'] = \
                    project['creationinfo']['creationtime']

            data = [{k: d[k] for k in PROJECT_FIELDS if k in d} for d in data]

        return data

    def list_forecastseries(self, project_id: int, details: bool = False):
        """
        List all forecast series for a project.
        :param project_id: id of the project
        :return: list of forecast series
        """
        request_url = f'{self.url}/projects/{project_id}/forecastseries'
        data = self._make_api_request(request_url)

        if not details:
            for forecastseries in data:
                forecastseries['creationtime'] = \
                    forecastseries['creationinfo']['creationtime']

            data = [{k: d[k] for k in FORECASTSERIES_FIELDS if k in d}
                    for d in data]

        return data

    def list_forecasts(self, forecastseries_id: int, details: bool = False):
        """
        List all forecasts for a forecast series.
        :param forecastseries_id: id of the forecast series
        :return: list of forecasts
        """
        request_url = \
            f'{self.url}/forecastseries/{forecastseries_id}/forecasts'

        data = self._make_api_request(request_url)

        if not details:
            data = [{k: d[k] for k in FORECAST_FIELDS if k in d} for d in data]

        return data

    def list_modelruns(self, forecast_id: int):
        """
        List all forecast modelruns for a forecast.
        :param forecast_id: id of the forecast
        :return: list of forecast modelruns
        """
        request_url = f'{self.url}/forecasts/{forecast_id}'

        data = self._make_api_request(request_url)

        return data['modelruns'] if 'modelruns' in data else []


class ForecastSeriesClient(BaseClient):
    def __init__(self,
                 url: str,
                 forecastseries_id: int,
                 timeout: int = None) -> None:
        """
        Initialize Class.
        :param url:     URL of the ramsis webservice
        :param timeout: after how long, contacting the webservice should
                        be aborted
        """
        self.url = f'{url}/v1'
        self._timeout = timeout
        self.logger = logging.getLogger(__name__)
        self.forecastseries_id = forecastseries_id
        self.metadata = {}

        self._set_forecastseries_data()

    def _set_forecastseries_data(self):
        request_url = f'{self.url}/forecastseries/{self.forecastseries_id}'
        self.metadata = self._make_api_request(request_url)

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
        request_url = f'{self.url}/forecasts/{forecast_id}/seismiccatalog'

        data = self._make_api_request(request_url)

        return Catalog.from_quakeml(data, includequality=True)

    def get_forecast_injectionwells(self, forecast_id: int):
        """
        Get hydraulics for a forecast.
        :param forecast_id: id of the forecast
        :return: hydraulics
        """
        request_url = f'{self.url}/forecasts/{forecast_id}/injectionwells'

        data = self._make_api_request(request_url)

        data = [BoreholeHydraulics(d) for d in data]

        return data

    def get_forecast_info_at_time(self,
                                  datetime: datetime,
                                  details=False) -> dict:
        """
        Get forecast by time.

        Returns the most recent forecast that is valid at the given datetime.

        :param datetime: datetime of the forecast
        :return: forecast
        """

        request_url = \
            f'{self.url}/forecastseries/{self.forecastseries_id}/forecasts'

        data = self._make_api_request(request_url)

        data.sort(key=lambda x: parse_datetime(x['starttime']), reverse=True)

        forecast = next(
            (x for x in data if parse_datetime(
                x['starttime']) <= datetime), {})

        if not details:
            forecast = {k: forecast[k]
                        for k in FORECAST_FIELDS if k in forecast}

        return forecast

    def list_forecasts_info(self, details=False) -> list[dict]:
        """
        Get all forecasts for a forecast series.
        :return: list of forecasts
        """

        request_url = \
            f'{self.url}/forecastseries/{self.forecastseries_id}/forecasts'

        data = self._make_api_request(request_url)

        if not details:
            data = [{k: d[k] for k in FORECAST_FIELDS if k in d} for d in data]

        return data

    def list_modelruns_info(self, forecast_id: int) -> list[dict]:
        """
        List all forecast modelruns for a forecast.
        :param forecast_id: id of the forecast
        :return: list of forecast modelruns
        """
        request_url = f'{self.url}/forecasts/{forecast_id}'

        data = self._make_api_request(request_url)

        return data['modelruns'] if 'modelruns' in data else []

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
            rateforecasts = modelrun['rateforecasts']

            rategrids = []

            for rate in rateforecasts:
                gr_rategrid = rates_to_seismostats(
                    rate['rates'],
                    rate['starttime'],
                    rate['endtime'])
                rategrids.append(gr_rategrid)
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

        data = data['rateforecasts']
        rategrids = []
        for rate in data:
            gr_rategrid = rates_to_seismostats(
                rate['rates'],
                rate['starttime'],
                rate['endtime'])
            rategrids.append(gr_rategrid)
        return rategrids

    def get_modelrun_injectionplan(self, modelrun_id: int):
        """
        Get injection plan for a modelrun.
        :param modelrun_id: id of the modelrun
        :return: injection plan
        """
        request_url = f'{self.url}/modelruns/{modelrun_id}/rates'

        data = self._make_api_request(request_url)
        injectionplan_id = data['injectionplan_id']

        request_url = f'{self.url}/injectionplans/{injectionplan_id}'

        hydws_data = self._make_api_request(request_url)

        hyd = BoreholeHydraulics(hydws_data)

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
