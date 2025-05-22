from datetime import datetime

import pandas as pd
from seismostats import ForecastGRRateGrid


def rates_to_seismostats(rates: list) -> ForecastGRRateGrid:
    """
    Convert rates from hermes to seismostats rate grid.

    Args:
        rates: List of rates from hermes.

    Returns:
        List of ForecastGRRateGrid objects.
    """
    df = pd.json_normalize(rates, sep='_')

    df.columns = df.columns.str.replace(
        "_value", "")

    df['starttime'] = pd.to_datetime(df['starttime'])
    df['endtime'] = pd.to_datetime(df['endtime'])
    df = df.rename(columns={'realization_id': 'grid_id'})

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


def deduplicate_dict(dict_list: list[dict]):
    seen = set()
    result = []
    for d in dict_list:
        t = tuple(sorted(d.items()))
        if t not in seen:
            seen.add(t)
            result.append(d)
    return result
