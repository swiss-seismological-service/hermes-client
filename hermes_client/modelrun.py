import logging
from uuid import UUID

from hydws.parser import BoreholeHydraulics

from hermes_client.base import BaseClient
from hermes_client.schemas import ModelRunInfo


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
        raise NotImplementedError

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
            print('fetching')
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
            mc = self._get_modelconfig()
            self._modelconfig = mc if mc else None

        return self._modelconfig.copy()

    @property
    def _get_modelconfig(self) -> dict:
        """
        Get all model configs for the forecast.
        """
        request_url = f'{self.url}/v1/modelruns/' \
            f'{self._metadata["oid"]}/modelconfig'

        data = self._get(request_url)

        return data
