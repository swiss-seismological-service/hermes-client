import logging
from uuid import UUID

from hydws.parser import BoreholeHydraulics
from seismostats import Catalog, ForecastCatalog, ForecastGRRateGrid

from hermes_client.base import BaseClient, NotFound
from hermes_client.hermes import HermesClient
from hermes_client.modelrun import ModelRunClient
from hermes_client.schemas import ForecastInfo
from hermes_client.utils import deduplicate_dict


class ForecastClient(BaseClient):
    '''
    Client to interact with Forecasts in the HERMES API.

    This object allows access to all the inputs of the Forecast,
    as well as the data linked to the ModelRuns of this specific
    Forecast.

    Usually automatically created by the
    :func:`~hermes_client.forecastseries.ForecastSeriesClient`,
    can however also be created directly using a Forecast UUID
    by using the :func:`~hermes_client.forecast.ForecastClient.from_oid`
    class method.

    Args:
        url: Base URL of the HERMES API.
        forecast: The Forecast metadata as a dictionary.
        timeout: Timeout for API requests in seconds.
    '''

    def __init__(self, url: str, forecast: dict, timeout: int | None = None):
        self._metadata = forecast
        self.url = url
        self._timeout = timeout
        self.logger = logging.getLogger(__name__)

        self._seismicityobservation = None
        self._injectionobservations = None

        self._modelruns = None

        self._extract_metadata()

    def __repr__(self):
        return f"Forecast({self.metadata.status}, " \
            f"{self.metadata.starttime}, {self.metadata.endtime})"

    @classmethod
    def from_oid(cls, url: str, oid: UUID | str):
        """
        Create a :func:`~hermes_client.forecast.ForecastClient`
        object from its oid.

        Args:
            url: Base URL of the HERMES API.
            oid: UUID of the Forecast.

        Returns:
            The Forecast object.
        """
        hermes = HermesClient(url=url)
        forecast = hermes._get(
            request_url=f'{url}/v1/forecasts/{oid}'
        )

        if not forecast:
            raise NotFound(f'Forecast with oid "{oid}" not found.')

        return cls(url, forecast)

    def _extract_metadata(self):
        """
        Build lists of InjectionPlans and ModelConfigs which are
        used in the model runs.
        """
        if 'modelruns' not in self._metadata or \
                not self._metadata['modelruns']:
            self._metadata['modelruns'] = []
        mcs = []
        ips = []
        for mr in self._metadata['modelruns']:
            if 'injectionplan' in mr:
                ips.append(mr['injectionplan'])
            if 'modelconfig' in mr:
                mcs.append(mr['modelconfig'])
        self._metadata['modelconfigs'] = deduplicate_dict(mcs)
        self._metadata['injectionplans'] = deduplicate_dict(ips)

    @property
    def metadata(self) -> ForecastInfo:
        """
        Metadata of the Forecast.
        """
        return ForecastInfo.model_validate(self._metadata)

    @property
    def modelruns(self) -> list[ModelRunClient]:
        """
        Model run data as :func:`~hermes_client.modelrun.ModelRunClient`
        objects.
        """
        if self._modelruns is None:
            self._modelruns = [ModelRunClient(self.url, m, self, self._timeout)
                               for m in self._metadata['modelruns']]

        return self._modelruns

    @property
    def injectionobservations(self) -> list[dict]:
        """
        InjectionObservations used in the Forecast.
        """
        if self._injectionobservations is None:
            ips = self._get_injectionobservations()

            if ips is not None:
                if len(ips) > 1:
                    raise NotImplementedError(
                        'Multiple injection observations are not yet '
                        'implemented.')
                self._injectionobservations = BoreholeHydraulics(ips[0])

        return self._injectionobservations

    def _get_injectionobservations(self) -> list[dict]:
        """
        Get all injection observations for the forecast.
        """
        request_url = f'{self.url}/v1/forecasts/' \
            f'{self._metadata["oid"]}/injectionobservations'

        data = self._get(request_url)

        return data

    @property
    def seismicityobservation(self) -> Catalog:
        """
        Seismicity observations use din the Forecast.
        """
        if self._seismicityobservation is None:
            so = self._get_seismicityobservation()
            if so is not None:
                so = Catalog.from_quakeml(so)
                self._seismicityobservation = so
        return self._seismicityobservation.copy()

    def _get_seismicityobservation(self) -> dict:
        """
        Get all seismicity observations for the forecast.
        """
        request_url = f'{self.url}/v1/forecasts/' \
            f'{self._metadata["oid"]}/seismicityobservation'

        data = self._get(request_url)

        return data

    @property
    def injectionplans(self) -> dict:
        """
        Injection plans used in the Forecast.
        """
        ips = {}
        for ip in self._metadata['injectionplans']:
            if 'hydraulics' not in ip:
                ip['hydraulics'] = BoreholeHydraulics(
                    self._get_injectionplan(ip['oid']))
            ips[ip['name']] = ip['hydraulics']
        return ips

    def _get_injectionplan(self, oid: UUID | str) -> dict:
        """
        Get all injection plans for the forecast.
        """
        request_url = f'{self.url}/v1/injectionplans/{str(oid)}'

        data = self._get(request_url)

        return data

    @property
    def modelconfigs(self) -> dict:
        """
        Model configs used in the Forecast.
        """
        mcs = {}
        for mc in self._metadata['modelconfigs']:
            if 'modelconfig' not in mc:
                mc['modelconfig'] = self._get_modelconfig(mc['oid'])
            mcs[mc['name']] = mc['modelconfig']
        return mcs.copy()

    def _get_modelconfig(self, oid: UUID | str) -> dict:
        """
        Get all model configs for the forecast.
        """
        request_url = f'{self.url}/v1/modelconfigs/{str(oid)}'

        data = self._get(request_url)

        return data

    def get_results(self,
                    modelconfig: str,
                    injectionplan: str | None = None) \
            -> list[ForecastCatalog] | list[ForecastGRRateGrid] | None:
        """
        Get the results for a model run as a Catalog or Grid object.

        Args:
            modelconfig:    The name of the ModelConfig for which
                            to get the results.
            injectionplan:  The name of the InjectionPlan for which
                            to get the results.

        Returns:
            The results for the model run.
            - For result_type 'GRID', for each timestep a
              ForecastGRRateGrid object is returned.
            - For result_type 'CATALOG', for each timestep and
              grid cell a ForecastCatalog object is returned.
        """

        if not self.modelruns:
            return None

        if injectionplan is not None:
            if not any(('injectionplan' in m._metadata for
                        m in self.modelruns)):
                raise ValueError('ModelRuns do not have injection plans.')

            run = [m for m in self.modelruns if 'injectionplan' in m._metadata
                   and m._metadata['injectionplan']['name'] == injectionplan]

        run = next((m for m in self.modelruns
                    if m._metadata['modelconfig']['name'] == modelconfig),
                   None)

        if run is None:
            raise ValueError(f'ModelRun with ModelConfig "{modelconfig}" '
                             f'and InjectionPlan "{injectionplan}" not found.')

        return run.get_results()
