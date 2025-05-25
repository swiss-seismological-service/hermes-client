import logging
from uuid import UUID

from hermes_client.base import BaseClient, NotFound


class HermesClient(BaseClient):
    """
    Client for the HERMES API to browse Project
    and ForecastSeries metadata as raw JSON data.

    Args:
        url: Base URL of the HERMES API.
        timeout: Timeout for API requests in seconds.
    """

    def __init__(self,
                 url: str,
                 timeout: int | None = None):
        self.url = url
        self._timeout = timeout
        self.logger = logging.getLogger(__name__)

    def list_projects(self):
        """
        List all projects.

        Returns:
            projects: List of all projects.
        """
        request_url = f'{self.url}/v1/projects'
        data = self._get(request_url)

        return data

    def get_project_by_name(self, project_name: str):
        """
        Get a project by its name.

        Args:
            project_name: name of the project.
        Returns:
            project: The project JSON data.
        """
        request_url = f'{self.url}/v1/projects'
        data = self._get(request_url)
        project = next((p for p in data if p['name'] == project_name),
                       None)
        if project is None:
            raise NotFound(
                f'Project with name "{project_name}" not found. '
                'Please provide a valid project name.')
        return project

    def get_project(self, project_oid: UUID | str):
        """
        Get a project by its oid.

        Args:
            project_oid: oid of the project.
        Returns:
            project: Project JSON data.
        """
        request_url = f'{self.url}/v1/projects/{str(project_oid)}'

        try:
            project = self._get(request_url)
        except NotFound:
            raise NotFound(
                f'Project with oid "{project_oid}" not found. '
                'Please provide a valid UUID.')

        return project

    def list_forecastseries(self, project: UUID | str):
        """
        List all ForecastSeries of a project.

        Args:
            project: oid or name of the project.

        Returns:
            forecastseries: All ForecastSeries of the project.
        """

        try:
            if not isinstance(project, UUID):
                UUID(project)
        except ValueError:
            project = self.get_project_by_name(project)['oid']

        request_url = f'{self.url}/v1/projects/{str(project)}/forecastseries'

        try:
            data = self._get(request_url)
        except NotFound:
            raise NotFound(
                f'Project with oid "{project}" not found. '
                'Please provide a valid UUID.')

        return data

    def list_modelconfigs(self):
        """
        List all model configurations.

        Returns:
            configs: All model configurations.
        """
        request_url = f'{self.url}/v1/modelconfigs'
        data = self._get(request_url)

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
            forecastseries: The ForecastSeries JSON data.
        """
        project = self.get_project_by_name(project_name)['oid']

        request_url = f'{self.url}/v1/projects/{project}/forecastseries'
        data = self._get(request_url)
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
            forecastseries: The ForecastSeries JSON data.
        """
        request_url = f'{self.url}/v1/forecastseries/{str(forecastseries_oid)}'
        try:
            fs = self._get(request_url)
        except NotFound:
            raise NotFound(
                f'ForecastSeries with oid "{forecastseries_oid}" not found. '
                'Please provide a valid UUID.')
        return fs
