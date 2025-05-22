
from typing import Self
from uuid import UUID

from hermes_client.base import BaseClient, NotFound
from hermes_client.hermes import HermesClient
from hermes_client.modelrun import ModelRunClient
from hermes_client.schemas import ForecastInfo


class ForecastClient(BaseClient):
    def __init__(self, url: str, forecast: dict, timeout: int):
        self._metadata = forecast
        self.url = url
        self._timeout = timeout

        self._seismicityobservation = None
        self._injectionobservations = None

        self._modelruns = None

    def __repr__(self):
        return f"Forecast({self.metadata.status}, " \
            f"{self.metadata.starttime}, {self.metadata.endtime})"

    @property
    def metadata(self) -> ForecastInfo:
        """
        Get the metadata of the forecast.
        :return: ForecastInfo object
        """
        return ForecastInfo.model_validate(self._metadata)

    @property
    def modelruns(self) -> list[ModelRunClient]:
        """
        List all model runs for a forecast.
        :return: list of model runs
        """
        if self._modelruns is None:
            self._modelruns = [ModelRunClient(self.url, m, self._timeout)
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
        forecast = hermes._get(
            request_url=f'{url}/v1/forecasts/{oid}'
        )

        if not forecast:
            raise NotFound(f'Forecast with oid "{oid}" not found.')

        return cls(url, forecast)
