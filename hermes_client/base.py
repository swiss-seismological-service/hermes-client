import json
from abc import ABC, abstractmethod
from typing import Any

import requests
from requests import Response


class RequestsError(requests.exceptions.RequestException):
    """Base request error ({})."""


class NoContent(RequestsError):
    """The request '{}' is returning no content ({})."""


class ClientError(RequestsError):
    """Response code not OK ({})."""


class NotFound(RequestsError):
    """The requested resource was not found ({})."""


def make_request(
    method: str,
    url: str,
    params: dict[str, Any] | None = None,
    data: Any | None = None,
    json_data: Any | None = None,
    headers: dict[str, str] | None = None,
    timeout: float | None = None,
    nocontent_codes: tuple[int, ...] = (204,),
    logger: Any = None,
    **kwargs,
) -> bytes:
    try:
        if logger is not None:
            logger.debug(
                f"Sending {method} request to {url}, "
                f"params={params}, json={json_data}")

        response: Response = requests.request(
            method=method.upper(),
            url=url,
            params=params,
            data=data,
            json=json_data,
            headers=headers,
            timeout=timeout,
            **kwargs,
        )

        if response.status_code in nocontent_codes:
            raise NoContent(
                f"No content from {response.url} ({response.status_code})")

        if response.status_code == 404:
            raise NotFound(f"Resource not found at {response.url}")

        if not response.ok:
            raise ClientError(
                f"HTTP {response.status_code} error at {response.url}")

        return response.content

    except requests.exceptions.RequestException:
        raise
    except Exception as e:
        raise RequestsError(f"Request failed: {e}") from e


class BaseClient(ABC):
    @abstractmethod
    def __init__(self):
        pass

    def _request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        data: Any | None = None,
        json_data: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        try:
            raw = make_request(
                method=method,
                url=url,
                params=params,
                data=data,
                json_data=json_data,
                headers=headers,
                timeout=self._timeout,
                nocontent_codes=(204,),
                logger=self.logger,
            )
            self.logger.debug(f"{method.upper()} successful for {url}")

            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                self.logger.debug(
                    "Non-JSON response returned as raw content.")
                return raw

        except NoContent:
            self.logger.debug(f"No content received from {url}.")
            return {}

        except NotFound as err:
            self.logger.error(f"Not Found: {err}")
            raise

        except RequestsError as err:
            self.logger.error(f"Request failed: {err}")
            raise

        except Exception as err:
            self.logger.exception(
                f"Unexpected error during {method.upper()} "
                f"request to {url}: {err}")
            raise

    def _get(self,
             url: str,
             params: dict[str, Any] | None = None,
             headers: dict[str, str] | None = None) -> Any:
        return self._request("GET", url, params=params, headers=headers)

    def _post(self,
              url: str,
              json_data: Any | None = None,
              headers: dict[str, str] | None = None) -> Any:
        return self._request("POST", url, json_data=json_data, headers=headers)

    def _put(self,
             url: str,
             json_data: Any | None = None,
             headers: dict[str, str] | None = None) -> Any:
        return self._request("PUT", url, json_data=json_data, headers=headers)

    def _delete(self,
                url: str,
                params: dict[str, Any] | None = None,
                headers: dict[str, str] | None = None) -> Any:
        return self._request("DELETE", url, params=params, headers=headers)
