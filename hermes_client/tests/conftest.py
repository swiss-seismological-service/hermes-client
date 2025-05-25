import json
import os
import uuid

import pytest
import responses

from hermes_client import HermesClient
from hermes_client.forecast import ForecastClient
from hermes_client.forecastseries import ForecastSeriesClient

url = "https://api.example.com"

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    'data')


def read_json(filename):
    with open(os.path.join(DATA, filename), 'r') as f:
        return json.load(f)


@pytest.fixture(scope="session")
def base_url():
    return url


@pytest.fixture(scope="session")
def proj2_ind_oid():
    return uuid.uuid4()


@pytest.fixture(scope="session")
def project_ind():
    return read_json('project.json')


@pytest.fixture(scope="session")
def fs_ind():
    return read_json('forecastseries.json')


@pytest.fixture(scope="session")
def forecast_ind():
    return read_json('forecasts.json')


@pytest.fixture(scope="session")
def injection_temp():
    return read_json('injectiontemplates.json')


@pytest.fixture(scope="session")
def modelconfigs():
    return read_json('modelconfigs.json')


@pytest.fixture(autouse=True)
def api_responses(base_url,
                  project_ind,
                  proj2_ind_oid,
                  fs_ind,
                  forecast_ind,
                  injection_temp,
                  modelconfigs):

    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        rsps.add(
            responses.GET,
            f"{base_url}/v1/projects",
            json=[project_ind],
            status=200
        )

        rsps.add(
            responses.GET,
            f"{base_url}/v1/projects/{project_ind['oid']}/forecastseries",
            json=[fs_ind],
            status=200
        )

        rsps.add(
            responses.GET,
            f"{base_url}/v1/projects/{proj2_ind_oid}/forecastseries",
            json=[],
            status=200
        )

        rsps.add(
            responses.GET,
            f"{base_url}/v1/forecastseries/{fs_ind['oid']}",
            json=fs_ind,
            status=200
        )

        rsps.add(
            responses.GET,
            f"{base_url}/v1/forecastseries/{fs_ind['oid']}/forecasts",
            json=forecast_ind,
            status=200
        )

        rsps.add(
            responses.GET,
            f"{base_url}/v1/forecastseries/{fs_ind['oid']}/modelconfigs",
            json=modelconfigs,
            status=200
        )

        rsps.add(
            responses.GET,
            f"{base_url}/v1/forecastseries/{fs_ind['oid']}/injectionplans",
            json=injection_temp,
            status=200
        )

        yield rsps


@pytest.fixture()
def hermes_client(base_url):
    yield HermesClient(url=base_url)


@pytest.fixture()
def fs_client(base_url, fs_ind):
    return ForecastSeriesClient(
        url=base_url,
        forecastseries=fs_ind['oid']
    )


@pytest.fixture()
def forecast_client(base_url, forecast_ind):
    yield ForecastClient.from_oid(
        url=base_url,
        oid=forecast_ind[0]['oid']
    )
