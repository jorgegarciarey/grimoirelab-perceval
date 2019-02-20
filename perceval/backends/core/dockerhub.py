# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2019 Bitergia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, 51 Franklin Street, Fifth Floor, Boston, MA 02110-1335, USA.
#
# Authors:
#     Santiago Dueñas <sduenas@bitergia.com>
#

import json
import logging

from grimoirelab_toolkit.datetime import datetime_utcnow
from grimoirelab_toolkit.uris import urijoin

from ...backend import (Backend,
                        BackendCommand,
                        BackendCommandArgumentParser)
from ...client import HttpClient

CATEGORY_DOCKERHUB_DATA = "dockerhub-data"

DOCKERHUB_URL = "https://hub.docker.com/"
DOCKERHUB_API_URL = urijoin(DOCKERHUB_URL, 'v2')

DOCKER_OWNER = 'library'
DOCKER_SHORTCUT_OWNER = '_'

logger = logging.getLogger(__name__)


class DockerHub(Backend):
    """DockerHub backend for Perceval.

    This class retrieves data from a repository stored
    in the Docker Hub site. To initialize this class owner
    and repositories where data will be fetched must be provided.
    The origin of the data will be built with both parameters.

    Shortcut `_` owner for official Docker repositories will
    be replaced by its long name: `library`.

    :param owner: DockerHub owner
    :param repository: DockerHub repository owned by `owner`
    :param tag: label used to mark the data
    :param archive: archive to store/retrieve items
    """
    version = '0.4.2'

    CATEGORIES = [CATEGORY_DOCKERHUB_DATA]

    def __init__(self, owner, repository, tag=None, archive=None):
        if owner == DOCKER_SHORTCUT_OWNER:
            owner = DOCKER_OWNER

        origin = urijoin(DOCKERHUB_URL, owner, repository)

        super().__init__(origin, tag=tag, archive=archive)
        self.owner = owner
        self.repository = repository
        self.client = None

    def fetch(self, category=CATEGORY_DOCKERHUB_DATA):
        """Fetch data from a Docker Hub repository.

        The method retrieves, from a repository stored in Docker Hub,
        its data which includes number of pulls, stars, description,
        among other data.

        :param category: the category of items to fetch

        :returns: a generator of data
        """
        kwargs = {}
        items = super().fetch(category, **kwargs)

        return items

    def fetch_items(self, category, **kwargs):
        """Fetch the Dockher Hub items

        :param category: the category of items to fetch
        :param kwargs: backend arguments

        :returns: a generator of items
        """
        logger.info("Fetching data from '%s' repository of '%s' owner",
                    self.repository, self.owner)

        raw_data = self.client.repository(self.owner, self.repository)
        fetched_on = datetime_utcnow().timestamp()

        data = self.parse_json(raw_data)
        data['fetched_on'] = fetched_on
        yield data

        logger.info("Fetch process completed")

    @classmethod
    def has_archiving(cls):
        """Returns whether it supports archiving items on the fetch process.

        :returns: this backend supports items archive
        """
        return True

    @classmethod
    def has_resuming(cls):
        """Returns whether it supports to resume the fetch process.

        :returns: this backend supports items resuming
        """
        return True

    @staticmethod
    def metadata_id(item):
        """Extracts the identifier from a Docker Hub item."""

        return str(item['fetched_on'])

    @staticmethod
    def metadata_updated_on(item):
        """Extracts and coverts the update time from a Docker Hub item.

        The timestamp is extracted from 'fetched_on' field. This field
        is not part of the data provided by Docker Hub. It is added
        by this backend.

        :param item: item generated by the backend

        :returns: a UNIX timestamp
        """
        return item['fetched_on']

    @staticmethod
    def metadata_category(item):
        """Extracts the category from a Docker Hub item.

        This backend only generates one type of item which is
        'dockerhub-data'.
        """
        return CATEGORY_DOCKERHUB_DATA

    @staticmethod
    def parse_json(raw_json):
        """Parse a Docker Hub JSON stream.

        The method parses a JSON stream and returns a
        dict with the parsed data.

        :param raw_json: JSON string to parse

        :returns: a dict with the parsed data
        """
        result = json.loads(raw_json)
        return result

    def _init_client(self, from_archive=False):
        """Init client"""

        return DockerHubClient(archive=self.archive, from_archive=from_archive)


class DockerHubClient(HttpClient):
    """DockerHub API client.

    Client for fetching information from the DockerHub server
    using its REST API v2.

    :param archive: an archive to store/read fetched data
    :param from_archive: it tells whether to write/read the archive
    """
    RREPOSITORY = 'repositories'

    def __init__(self, archive=None, from_archive=False):
        super().__init__(DOCKERHUB_API_URL, archive=archive, from_archive=from_archive)

    def repository(self, owner, repository):
        """Fetch information about a repository."""

        url = urijoin(self.base_url, self.RREPOSITORY, owner, repository)

        logger.debug("DockerHub client requests: %s", url)

        response = self.fetch(url)

        return response.text


class DockerHubCommand(BackendCommand):
    """Class to run DockerHub backend from the command line."""

    BACKEND = DockerHub

    @staticmethod
    def setup_cmd_parser():
        """Returns the DockerHub argument parser."""

        parser = BackendCommandArgumentParser(archive=True)

        # Required arguments
        parser.parser.add_argument('owner',
                                   help="Docker Hub owner")
        parser.parser.add_argument('repository',
                                   help="Docker Hub repository")

        return parser
