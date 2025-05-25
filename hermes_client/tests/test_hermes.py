from hermes_client import HermesClient


def test_projects(hermes_client: HermesClient):
    """
    Test the retrieval of projects from the Hermes API.
    """
    # Fetch projects
    projects = hermes_client.list_projects()

    assert isinstance(projects, list)
    assert projects[0]['oid'] == "c9d163c4-02ea-4d4d-9ef5-26e82c025c92"
