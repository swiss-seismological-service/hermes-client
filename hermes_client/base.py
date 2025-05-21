import json
from abc import ABC, abstractmethod

import requests

from hermes_client.utils import logger


class RequestsError(requests.exceptions.RequestException):
    """Base request error ({})."""


class NoContent(RequestsError):
    """The request '{}' is returning no content ({})."""


class ClientError(RequestsError):
    """Response code not OK ({})."""


class NotFound(RequestsError):
    """The requested resource was not found ({})."""


def make_request(request, url, params={}, timeout=None,
                 nocontent_codes=(204,), **kwargs):
    """
    Make a normal request

    Args:
        request: Request object to be used
        url: URL
        params: Dictionary of query parameters
        timeout: Request timeout
        nocontent_codes: List of response codes that are considered
            "no content" (default: 204)
        kwargs: Additional keyword arguments to be passed to the request
            (e.g. headers, data, etc.)

    Returns:
        content of response

    Raises:
        NoContent: If the response code is in nocontent_codes
        ClientError: If the response code is not 200
        RequestsError: If there is a request exception
    """

    try:
        r = request(url, params=params, timeout=timeout, **kwargs)

        logger.debug(f'Making request to {url} with parameters {params}')

        if r.status_code in nocontent_codes:
            raise NoContent(r.url, r.status_code, response=r)

        r.raise_for_status()

        if r.status_code != 200:
            raise ClientError(r.status_code, response=r)

        return r.content

    except (NoContent, ClientError) as err:
        raise err

    except requests.exceptions.RequestException as err:
        raise RequestsError(err, response=err.response)


class BaseClient(ABC):
    @abstractmethod
    def __init__(self):
        pass

    def _make_api_request(self, request_url: str, params: dict = {}):
        try:
            response = make_request(
                requests.get,
                request_url,
                params,
                self._timeout,
                nocontent_codes=(204,))

        except NoContent:
            self.logger.warning('No data received.')
            return {}
        except RequestsError as err:
            self.logger.error(f"Request Error while fetching data ({err}).")
        except BaseException as err:
            self.logger.error(f"Error while fetching data {err}")
        else:
            self.logger.info('Data received.')
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return response
