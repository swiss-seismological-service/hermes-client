import logging
from datetime import datetime

import pandas as pd
import requests
from seismostats.seismicity.rategrid import ForecastGRRateGrid

logger = logging.getLogger(__name__)


class RequestsError(requests.exceptions.RequestException):
    """Base request error ({})."""


class NoContent(RequestsError):
    """The request '{}' is returning no content ({})."""


class ClientError(RequestsError):
    """Response code not OK ({})."""


def make_request(request, url, params={}, timeout=None,
                 nocontent_codes=(204,), **kwargs):
    """
    Make a normal request

    :param request: Request object to be used
    :type request: :py:class:`requests.Request`
    :param str url: URL
    :params dict params: Dictionary of query parameters
    :param timeout: Request timeout
    :type timeout: None or int or tuple

    :return: content of response
    :rtype: string
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


def rates_to_seismostats(rates: list) -> ForecastGRRateGrid:
    """
    Convert rates from ramsis to seismostats rate grid.

    :param rates: rates from ramsis
    :return: seismostats rate grid
    """
    df = pd.json_normalize(rates, sep='_')

    df.columns = df.columns.str.replace(
        "_value", "")

    df['starttime'] = pd.to_datetime(df['starttime'])
    df['endtime'] = pd.to_datetime(df['endtime'])

    if 'mc' not in df.columns:
        df['mc'] = pd.NA
    if 'a' not in df.columns:
        df['a'] = pd.NA
    if 'b' not in df.columns:
        df['b'] = pd.NA

    grouped = df.groupby(['starttime', 'endtime'])

    grids = []
    for times, group in grouped:
        new_df = ForecastGRRateGrid(
            group.drop(columns=['starttime', 'endtime']),
            starttime=times[0],
            endtime=times[1])
        grids.append(new_df)

    return grids


def parse_datetime(date: str):
    try:
        return datetime.strptime(date, '%Y-%m-%dT%H:%M:%S.%fZ')
    except BaseException:
        return datetime.strptime(date, '%Y-%m-%dT%H:%M:%S')
