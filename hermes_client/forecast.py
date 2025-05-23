import logging
from typing import Self
from uuid import UUID

from hydws.parser import BoreholeHydraulics
from seismostats import Catalog, ForecastCatalog, ForecastGRRateGrid

from hermes_client.base import BaseClient, NotFound
from hermes_client.hermes import HermesClient
from hermes_client.modelrun import ModelRunClient
from hermes_client.schemas import ForecastInfo
from hermes_client.utils import deduplicate_dict, deserialize_rates


class ForecastClient(BaseClient):
    def __init__(self, url: str, forecast: dict, timeout: int | None = None):
        self._metadata = forecast
        self.url = url
        self._timeout = timeout
        self.logger = logging.getLogger(__name__)

        self._seismicityobservation = None
        self._injectionobservations = None

        self._modelruns = None

        self.extract_metadata()

    def __repr__(self):
        return f"Forecast({self.metadata.status}, " \
            f"{self.metadata.starttime}, {self.metadata.endtime})"

    @classmethod
    def from_oid(cls, url: str, oid: UUID | str) -> Self:
        """
        Create a Forecast object from an oid.

        Args:
            url: Base URL of the HERMES API.
            oid: UUID or string representation of the Forecast oid.

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

    def extract_metadata(self):
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
        Get the metadata of the forecast.
        """
        return ForecastInfo.model_validate(self._metadata)

    @property
    def modelruns(self) -> list[ModelRunClient]:
        """
        List all model runs for a forecast.
        """
        if self._modelruns is None:
            self._modelruns = [ModelRunClient(self.url, m, self, self._timeout)
                               for m in self._metadata['modelruns']]

        return self._modelruns

    @property
    def injectionobservations(self) -> list[dict]:
        """
        Get the injection observations for a forecast.
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
        Get the seismicity observations for a forecast.
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
        Get all injection plans for the forecast.
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
        Get all model configs for the forecast.
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
        Get the results for a model run.

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
        if not self._metadata['modelruns']:
            return None

        run = self._metadata['modelruns']

        if injectionplan is not None:
            if not any(('injectionplan' in m for m in run)):
                raise ValueError('ModelRuns do not have injection plans.')

            run = [m for m in run if 'injectionplan' in m
                   and m['injectionplan']['name'] == injectionplan]

        run = next((m for m in run if m['modelconfig']['name'] == modelconfig),
                   None)

        if run is None:
            raise ValueError(f'ModelRun with ModelConfig "{modelconfig}" '
                             f'and InjectionPlan "{injectionplan}" not found.')

        return self._get_results(run['oid'])

    def _get_results(self, oid: UUID | str) \
            -> list[ForecastCatalog] | list[ForecastGRRateGrid] | None:
        """
        Get the results for a model run by its oid.

        Args:
            oid: The oid of the model run.
        Returns:
            The results for the model run.
        """

        run = next((m for m in self._metadata['modelruns']
                   if m['oid'] == oid), None)
        if run is None:
            raise ValueError(f'ModelRun with oid "{oid}" not found.')

        if 'results' not in run:
            run['results'] = self._get_modelrun_results(oid)

            if run['modelconfig']['result_type'] == 'GRID':
                run['results'] = deserialize_rates(run['results'])

            elif run['modelconfig']['result_type'] == 'CATALOG':
                raise NotImplementedError(
                    'Catalog results are not yet implemented.')

            elif run['modelconfig']['result_type'] == 'BINS':
                raise NotImplementedError(
                    'MagnitudeBins results are not yet implemented.')

        return run['results'].copy()

    def _get_modelrun_results(self, oid: UUID | str) -> dict:
        """
        Get the results for a model run.

        Args:
            oid: The oid of the model run.

        Returns:
            The results for the model run.
        """
        request_url = f'{self.url}/v1/modelruns/{str(oid)}/results'

        data = self._get(request_url)

        return data
