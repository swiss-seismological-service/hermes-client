
from typing import Self
from uuid import UUID

from hermes_client.base import BaseClient, NotFound
from hermes_client.hermes import HermesClient
from hermes_client.schemas import EStatus, ForecastInfo


class ModelRun(BaseClient):
    def __init__(self, url: str, modelrun: dict):
        self._metadata = modelrun
        self.url = url

        self.oid = modelrun['oid']
        self.status = EStatus(modelrun['status'])

    def __repr__(self):
        return \
            f"ModelRun({self.status}, " \
            f"modelconfig={self._metadata['modelconfig']['name']} " \
            f"injectionplan={self._metadata['injectionplan']['name']})"


class Forecast(BaseClient):
    def __init__(self, url: str, forecast: dict):
        self._metadata = forecast
        self.url = url

        metadata = ForecastInfo.model_validate(forecast)
        self.oid = metadata.oid
        self.status = metadata.status
        self.starttime = metadata.starttime
        self.endtime = metadata.endtime
        self.creationinfo = metadata.creationinfo

        self._seismicityobservation = None
        self._injectionobservations = None

        self._modelruns = None

    def __repr__(self):
        return f"Forecast({self.status}, " \
            f"{self.starttime}, {self.endtime})"

    @property
    def modelruns(self) -> list[ModelRun]:
        """
        List all model runs for a forecast.
        :return: list of model runs
        """
        if self._modelruns is None:
            self._modelruns = [ModelRun(self.url, m)
                               for m in self._metadata['modelruns']]

        return self._modelruns

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
        forecast = hermes._make_api_request(
            request_url=f'{url}/v1/forecasts/{oid}',
            params={'oid': oid}
        )

        if not forecast:
            raise NotFound(f"Forecast with oid {oid} not found.")

        return cls(url, forecast)
