import pytest

from hermes_client import HermesClient
from hermes_client.base import NotFound


def test_projects(hermes_client: HermesClient):
    """
    Test the retrieval of projects from the Hermes API.
    """
    # Fetch projects
    projects = hermes_client.list_projects()

    assert isinstance(projects, list)
    assert projects[0]['oid'] == "c9d163c4-02ea-4d4d-9ef5-26e82c025c92"


def test_get_project_by_name(hermes_client: HermesClient, project_ind):
    """
    Test getting a project by its name.
    """
    project = hermes_client.get_project_by_name(project_ind['name'])

    assert isinstance(project, dict)
    assert project['oid'] == project_ind['oid']

    with pytest.raises(NotFound):
        hermes_client.get_project_by_name("nonexistent_project")


def test_get_project_by_oid(hermes_client: HermesClient,
                            project_ind,
                            proj2_ind_oid):
    """
    Test getting a project by its OID.
    """
    project = hermes_client.get_project(project_ind['oid'])

    assert isinstance(project, dict)
    assert project['oid'] == project_ind['oid']

    with pytest.raises(NotFound):
        hermes_client.get_project(proj2_ind_oid)


def test_list_forecastseries(hermes_client: HermesClient,
                             project_ind,
                             fs_ind):
    """
    Test listing forecast series for a project.
    """
    forecast_series = hermes_client.list_forecastseries(project_ind['oid'])

    assert isinstance(forecast_series, list)
    assert forecast_series[0]['oid'] == fs_ind['oid']


def test_get_forecastseries_by_name(hermes_client: HermesClient,
                                    project_ind,
                                    fs_ind):
    """
    Test getting a forecast series by name.
    """
    forecast_series = hermes_client.get_forecastseries_by_name(
        project_ind['name'], fs_ind['name'])

    assert isinstance(forecast_series, dict)
    assert forecast_series['oid'] == fs_ind['oid']

    with pytest.raises(NotFound):
        hermes_client.get_forecastseries_by_name(
            "nonexistent_project", "nonexistent_fs")


def test_get_forecastseries_by_oid(hermes_client: HermesClient,
                                   proj2_ind_oid,
                                   fs_ind):
    """
    Test getting a forecast series by OID.
    """
    forecast_series = hermes_client.get_forecastseries(fs_ind['oid'])

    assert isinstance(forecast_series, dict)
    assert forecast_series['oid'] == fs_ind['oid']

    with pytest.raises(NotFound):
        hermes_client.get_forecastseries(proj2_ind_oid)
