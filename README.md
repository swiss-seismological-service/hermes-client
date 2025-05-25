![pypi](https://img.shields.io/pypi/v/hermes-client)
[![PyPI - License](https://img.shields.io/pypi/l/hermes-client)](https://pypi.org/project/hermes-client/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/hermes-client.svg)](https://pypi.org/project/hermes-client/)
[![test](https://github.com/swiss-seismological-service/hermes-client/actions/workflows/tests.yml/badge.svg)](https://github.com/swiss-seismological-service/hermes-client/actions/workflows/tests.yml)
[![codecov](https://codecov.io/github/swiss-seismological-service/hermes-client/graph/badge.svg?token=RVJFHYLBKA)](https://codecov.io/github/swiss-seismological-service/hermes-client)
[![Documentation Status](https://readthedocs.org/projects/hermes-client/badge/?version=latest)](https://hermes-client.readthedocs.io/en/latest/?badge=latest)

# HERMES Python Client

This Python client provides a simple interface to the HERMES API, allowing users to easily access and interact with the HERMES data.

## Installation
You can install the client using pip:

```bash
pip install hermes-client
```

Generally, the client is compatible with the respective `vMajor.minor` version of the HERMES webservice. For example, the `hermes-client` version `0.1.x` is compatible with the HERMES webservice version `0.1.x`.

## Usage
You will mainly interact with two client classes. The [HermesClient](https://hermes-client.readthedocs.io/stable/reference/hermes_client.html) as well as the [ForecastSeriesClient](https://hermes-client.readthedocs.io/stable/reference/forecastseries_client.html).
The former should mainly be used to explore the available Projects and Forecastseries, while the latter can be used to access the data linked to specific ForecastSeries, Forecasts and ModelRuns.

### Find the correct ForecastSeries
To find the correct ForecastSeries, you can use the `HermesClient` to search for ForecastSeries by name or other attributes. For example:

```python
from hermes_client import HermesClient
client = HermesClient(url="https://example.com/api/")

projects = client.list_projects()
projects
```

This will return a list of available projects.

```
[{'oid': 'c9d163c4-02ea-4d4d-9ef5-26e82c025c92',
 'name': 'project_induced',
 'starttime': '2022-04-21T00:00:00',
 'endtime': '2022-04-21T23:59:59',
 'description': 'This is a test project',
 'creationinfo': {'creationtime': '2025-05-22T16:51:41'}},
 ...
```

Likewise, you can list all ForecastSeries within a project:

```python
forecastseries = client.list_forecastseries(project="project_induced")
```

Which will again return a list of ForecastSeries
```python
[{'oid': 'c9d163c4-02ea-4d4d-9ef5-26e82c025c92',
 'name': 'forecastseries_induced',
 ...
 },
 ...
]
```

### Access ForecastSeries data
Once you have identified the correct ForecastSeries, you can use the `ForecastSeriesClient` to access the data. For example:

```python
from hermes_client import ForecastSeriesClient
client = ForecastSeriesClient(
    url="https://example.com/api/",
    forecastseries="c9d163c4-02ea-4d4d-9ef5-26e82c025c92"
)
client.forecasts
```

Which will return a list of [ForecastClient](https://hermes-client.readthedocs.io/stable/reference/forecast_client.html) objects, each allowing you to access the data for a specific forecast:

```
[Forecast(COMPLETED, 2022-04-21 15:00:00, 2022-04-21 18:00:00),
 Forecast(COMPLETED, 2022-04-21 16:00:00, 2022-04-21 18:00:00),
 Forecast(COMPLETED, 2022-04-21 17:00:00, 2022-04-21 18:00:00)]
```

You can then access the data for a specific forecast by using the `ForecastClient`:

```python
forecast = client.forecasts[0]

injectionplan_name = forecast.metadata.injectionplans[0]
model_name = forecast.metadata.modelconfigs[0]

results = forecast.get_results(injectionplan_name, model_name)
```

This will return a [ForecastGRRateGrid](https://seismostats.readthedocs.io/latest/reference/formats/forecastgrrategrid.html) object (or [ForecastCatalog](https://seismostats.readthedocs.io/latest/reference/formats/forecastcatalog.html), depending on the model result types).

## Further Information
For more information on the available methods and attributes, please refer to the [API reference](https://hermes-client.readthedocs.io/stable/reference/index.html).

The documentation will be extended in the future to include more examples and use cases - The API Reference should however give a good overview of the available methods and attributes.