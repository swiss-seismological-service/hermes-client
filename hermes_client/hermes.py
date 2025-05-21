import logging
from uuid import UUID

from hermes_client.base import BaseClient, NotFound


class HermesClient(BaseClient):
    def __init__(self,
                 url: str,
                 timeout: int = None):
        """
        Initialize Class.

        Args:
            url:        URL of the hermes webservice
            timeout:    after how long, contacting the webservice should
                        be aborted
        """
        self.url = url
        self._timeout = timeout
        self.logger = logging.getLogger(__name__)

    def list_projects(self):
        """
        List all projects.

        Returns:
            list: list of projects
        """
        request_url = f'{self.url}/v1/projects'
        data = self._make_api_request(request_url)

        return data

    def get_project_by_name(self, project_name: str):
        """
        Get a project by name.

        Args:
            project_name: name of the project.
        Returns:
            The project.
        """
        request_url = f'{self.url}/v1/projects'
        data = self._make_api_request(request_url)
        project = next((p for p in data if p['name'] == project_name),
                       None)
        if project is None:
            raise NotFound(
                f'Project with name "{project_name}" not found. '
                'Please provide a valid project name.')
        return project

    def get_project(self, project_oid: UUID | str):
        """
        Get a project by oid.

        Args:
            project_oid: oid of the project.
        Returns:
            The project.
        """
        request_url = f'{self.url}/v1/projects/{str(project_oid)}'
        project = self._make_api_request(request_url)
        if project is None:
            raise NotFound(
                f'Project with oid "{project_oid}" not found. '
                'Please provide a valid UUID.')
        return project

    def list_forecastseries(self, project: UUID | str):
        """
        List all ForecastSeries for a project.

        Args:
            project: oid or name of the project.

        Returns:
            All ForecastSeries for the project.
        """

        try:
            if not isinstance(project, UUID):
                UUID(project)
        except ValueError:
            project = self.get_project_by_name(project)['oid']

        request_url = f'{self.url}/v1/projects/{str(project)}/forecastseries'
        data = self._make_api_request(request_url)

        return data

    def list_modelconfigs(self):
        """
        List all model configurations.

        Returns:
            list: list of model configurations
        """
        request_url = f'{self.url}/v1/modelconfigs'
        data = self._make_api_request(request_url)

        return data

    def get_forecastseries_by_name(self,
                                   project_name: str,
                                   forecastseries_name: str):
        """
        Get a ForecastSeries by name.

        Args:
            project_name: name of the project.
            forecastseries_name: name of the forecast series.
        Returns:
            The ForecastSeries.
        """
        project = self.get_project_by_name(project_name)['oid']

        request_url = f'{self.url}/v1/projects/{project}/forecastseries'
        data = self._make_api_request(request_url)
        fs = next(
            (fs for fs in data if fs['name'] == forecastseries_name),
            None)
        if fs is None:
            raise NotFound(
                f'ForecastSeries with name "{forecastseries_name}" not found. '
                'Please provide a valid ForecastSeries name.')
        return fs

    def get_forecastseries(self,
                           forecastseries_oid: UUID | str):
        """
        Get a ForecastSeries by oid.

        Args:
            forecastseries_oid: oid of the forecast series.
        Returns:
            The ForecastSeries.
        """
        request_url = f'{self.url}/v1/forecastseries/{str(forecastseries_oid)}'
        fs = self._make_api_request(request_url)
        if fs is None:
            raise NotFound(
                f'ForecastSeries with oid "{forecastseries_oid}" not found. '
                'Please provide a valid UUID.')
        return fs
