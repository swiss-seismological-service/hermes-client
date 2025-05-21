import logging
from uuid import UUID

from hydws.parser import BoreholeHydraulics
from seismostats import Catalog

from hermes_client.base import BaseClient, NotFound
from hermes_client.hermes import HermesClient
from hermes_client.schemas import ForecastSeries
from hermes_client.utils import rates_to_seismostats


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
                 forecastseries: UUID | str | None = None,
                 project: UUID | str | None = None,
                 timeout: int = None) -> None:
        self.url = f'{url}/v1'
        self._timeout = timeout
        self.logger = logging.getLogger(__name__)

        self._metadata = self._get_forecastseries_data(
            url, forecastseries, project)

    def _get_forecastseries_data(self,
                                 url: str,
                                 forecastseries: UUID | str | None = None,
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
            if fs_list is None:
                raise NotFound(
                    f'No ForecastSeries found for Project "{project}". '
                    'Please provide a valid Project name or UUID.')

            fs = next((fs for fs in fs_list
                       if fs['name'] == forecastseries), None)

            if fs is None:
                raise NotFound(
                    f'ForecastSeries with name "{forecastseries}" for Project '
                    f'"{project}" not found. Please provide a valid Project '
                    'and ForecastSeries name.')

            return fs

    @property
    def metadata(self):
        """
        Get the metadata of the ForecastSeries.
        """
        return ForecastSeries(**self._metadata)

    @property
    def injectionplans(self):
        """
        List all injection plans for a forecast series.
        :return: list of injection plans
        """
        return self._metadata['injectionplans']

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
        return self._metadata['modelconfigs']

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
