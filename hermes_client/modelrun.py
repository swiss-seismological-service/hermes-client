import logging
from uuid import UUID

from hydws.parser import BoreholeHydraulics
from seismostats import ForecastCatalog, ForecastGRRateGrid

from hermes_client.base import BaseClient
from hermes_client.hermes import HermesClient
from hermes_client.schemas import ModelRunInfo
from hermes_client.utils import deserialize_rates


class ModelRunClient(BaseClient):
    """
    Client to interact with ModelRuns in the HERMES API.

    This object allows access to the metadata of the ModelRun,
    as well as the input data and the results of the ModelRun.

    Usually automatically created by the
    :func:`~hermes_client.forecast.ForecastClient`,
    can however also be created directly using a ModelRun UUID
    by using the :func:`hermes_client.forecast.ForecastClient.from_oid`
    class method.

    Args:
        url: Base URL of the HERMES API.
        modelrun: The ModelRun metadata as a dictionary.
        forecast_client: Optional ForecastClient to use for fetching
            injection plans and model configs.
        timeout: Timeout for API requests in seconds.
    """

    def __init__(self,
                 url: str,
                 modelrun: dict,
                 forecast_client: object | None = None,
                 timeout: int | None = None):
        self._metadata = modelrun
        self.url = url
        self._timeout = timeout
        self.logger = logging.getLogger(__name__)

        # if the reference to the forecast_client exists, we can
        # use it to get the injectionplan and modelconfig
        # instead of fetching them again from the API
        self._forecast_client = forecast_client
        self._injectionplan = None
        self._modelconfig = None
        self._results = None

    def __repr__(self):
        return \
            f"ModelRun({self.metadata.status}, " \
            f"modelconfig={self.metadata.modelconfig}, " \
            f"injectionplan={self.metadata.injectionplan})"

    @classmethod
    def from_oid(cls, url: str, oid: UUID | str):
        """
        Create a :func:`~hermes_client.modelrun.ModelRunClient`
        object from its oid.

        Args:
            url: Base URL of the HERMES API.
            oid: UUID of the ModelRun.
        """
        hermes = HermesClient(url=url)
        modelrun = hermes._get(
            f'{url}/v1/modelruns/{oid}')

        if not modelrun:
            raise ValueError(f'ModelRun with oid {oid} not found.')

        return cls(url, modelrun)

    @property
    def metadata(self) -> dict:
        """
        Metadata of the model run.
        """
        return ModelRunInfo.model_validate(self._metadata)

    @property
    def injectionplan(self) -> BoreholeHydraulics | None:
        """
        InjectionPlan of the ModelRun.
        """
        if self._forecast_client is not None:
            return self._forecast_client.injectionplans[
                self.metadata.injectionplan]

        if self._injectionplan is None:
            ip = self._get_injectionplan()
            self._injectionplan = BoreholeHydraulics(ip) if ip else None

        return self._injectionplan

    def _get_injectionplan(self) -> dict:
        """
        Get all injection plans for the forecast.
        """
        request_url = f'{self.url}/v1/modelruns/' \
            f'{self._metadata["oid"]}/injectionplan'

        data = self._get(request_url)

        return data

    @property
    def modelconfig(self) -> dict | None:
        """
        ModelConfig of the ModelRun.
        """
        if self._forecast_client is not None:
            return self._forecast_client.modelconfigs[
                self.metadata.modelconfig]

        if self._modelconfig is None:
            self._modelconfig = self._get_modelconfig()

        return self._modelconfig.copy()

    def _get_modelconfig(self) -> dict:
        """
        Get all model configs for the forecast.
        """
        request_url = f'{self.url}/v1/modelruns/' \
            f'{self._metadata["oid"]}/modelconfig'

        data = self._get(request_url)

        return data

    def get_results(self) \
            -> list[ForecastCatalog] | list[ForecastGRRateGrid] | None:
        """
        Get the results for the model run.

        Returns:
            A list of ForecastCatalog or ForecastGRRateGrid objects,
            or None if no results are available.
        """
        if self._results is not None:
            return self._results.copy()

        self._results = self._get_results()

        if self.modelconfig['result_type'] == 'GRID':
            self._results = deserialize_rates(self._results)
        elif self.modelconfig['result_type'] == 'CATALOG':
            raise NotImplementedError(
                'Catalog results are not yet implemented.')
        elif self.modelconfig['result_type'] == 'BINS':
            raise NotImplementedError(
                'MagnitudeBins results are not yet implemented.')

        return self._results.copy()

    def _get_results(self) -> bytes:
        """
        Get the results for the model run.
        """
        request_url = f'{self.url}/v1/modelruns/' \
            f'{self._metadata["oid"]}/results'

        data = self._get(request_url)

        return data
