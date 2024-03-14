import json
import logging
from abc import ABC, abstractmethod

import requests
from hydws.parser import BoreholeHydraulics
from seismostats.seismicity.catalog import Catalog

from ramsis_client.utils import (NoContent, RequestsError, make_request,
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
            keys = [
                'id',
                'name',
                'description',
                'starttime',
                'endtime',
                'creationtime']

            for project in data:
                project['creationtime'] = \
                    project['creationinfo']['creationtime']

            data = [{k: d[k] for k in keys if k in d} for d in data]

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
            keys = [
                'id',
                'name',
                'starttime',
                'endtime',
                'creationtime',
                'forecastinterval',
                'status']

            for forecastseries in data:
                forecastseries['creationtime'] = \
                    forecastseries['creationinfo']['creationtime']

            data = [{k: d[k] for k in keys if k in d} for d in data]

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
            keys = [
                'id',
                'starttime',
                'endtime',
                'status']

            data = [{k: d[k] for k in keys if k in d} for d in data]

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


class ForecastClient(BaseClient):
    def __init__(self,
                 url: str,
                 project_id: int,
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
        self.project_id = project_id
        self.forecastseries_id = forecastseries_id

    def get_forecast_rates(self, forecast_id: int, models: list[str] = None,
                           injectionplans: list[str] = None):
        """
        Get forecast rates for a forecast.
        :param forecast_id: id of the forecast
        :return: forecast rates
        """
        params = {}
        if models:
            params['models'] = models
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

    def get_forecast_seismicity(self, forecast_id: int):
        """
        Get seismicity for a forecast.
        :param forecast_id: id of the forecast
        :return: seismicity
        """
        request_url = f'{self.url}/forecasts/{forecast_id}/seismiccatalog'

        data = self._make_api_request(request_url)

        return Catalog.from_quakeml(data)
