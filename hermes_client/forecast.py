
from typing import Self
from uuid import UUID

from hermes_client.base import BaseClient, NotFound
from hermes_client.hermes import HermesClient
from hermes_client.modelrun import ModelRunClient
from hermes_client.schemas import ForecastInfo
from hermes_client.utils import deduplicate_dict


class ForecastClient(BaseClient):
    def __init__(self, url: str, forecast: dict, timeout: int | None = None):
        self._metadata = forecast
        self.url = url
        self._timeout = timeout

        self._seismicityobservation = None
        self._injectionobservations = None

        self._modelruns = None

        self.extract_metadata()

    def __repr__(self):
        return f"Forecast({self.metadata.status}, " \
            f"{self.metadata.starttime}, {self.metadata.endtime})"

    def extract_metadata(self):
        """
        Build lists of InjectionPlans and ModelConfigs which are
        used in the model runs.
        """
        if 'modelruns' not in self._metadata or \
                not self._metadata['modelruns']:
            return None
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
