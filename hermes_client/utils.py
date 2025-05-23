import io
from datetime import datetime

import pandas as pd
from seismostats import ForecastGRRateGrid


def deserialize_rates(rates: bytes) -> list[ForecastGRRateGrid]:
    """
    Convert rates from hermes to seismostats rate grid.

    Args:
        rates: List of rates from hermes.

    Returns:
        List of ForecastGRRateGrid objects.
    """
    rates = pd.read_csv(io.StringIO(rates.decode('utf-8')))

    rates['starttime'] = pd.to_datetime(rates['starttime'])
    rates['endtime'] = pd.to_datetime(rates['endtime'])
    rates = rates.rename(columns={'realization_id': 'grid_id'})

    if 'mc' not in rates.columns:
        rates['mc'] = pd.NA
    if 'a' not in rates.columns:
        rates['a'] = pd.NA
    if 'b' not in rates.columns:
        rates['b'] = pd.NA

    grouped = rates.groupby(['starttime', 'endtime'])

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


def deduplicate_dict(dict_list: list[dict]):
    seen = set()
    result = []
    for d in dict_list:
        t = tuple(sorted(d.items()))
        if t not in seen:
            seen.add(t)
            result.append(d)
    return result
