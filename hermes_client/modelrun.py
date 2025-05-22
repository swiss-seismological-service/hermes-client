from hermes_client.base import BaseClient
from hermes_client.schemas import ModelRunInfo


class ModelRunClient(BaseClient):
    def __init__(self,
                 url: str,
                 modelrun: dict,
                 forecast_client: object | None = None,
                 timeout: int | None = None):
        self._metadata = modelrun
        self.url = url
        self._timeout = timeout

        self._forecast_client = forecast_client

    def __repr__(self):
        return \
            f"ModelRun({self.metadata.status}, " \
            f"modelconfig={self.metadata.modelconfig}, " \
            f"injectionplan={self.metadata.injectionplan})"

    @property
    def metadata(self) -> dict:
        """
        Metadata of the model run.
        """
        return ModelRunInfo.model_validate(self._metadata)
