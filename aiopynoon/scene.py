""" Base class for a Noon scene. """

from .entity import NoonEntity
import asyncio
from typing import Dict
import logging

from .const import Guid

from .exceptions import (
    NoonInvalidParametersError,
    NoonInvalidJsonError
)

_LOGGER = logging.getLogger(__name__)

class NoonScene(NoonEntity):

    @property
    def parent_space(self):
        return self._parent_space

    def __init__(self, noon, parent_space, guid: Guid, name: str):
        
        """Initializes the Space."""
        self._parent_space = parent_space
        super().__init__(noon, guid, name)

    @classmethod
    async def from_json(cls, noon, space, json):

        """Basics"""
        guid = json.get("guid", None)
        name = json.get("name", None)

        if guid is None or name is None:
            _LOGGER.debug("Invalid JSON payload: {}".format(json))
            raise NoonInvalidJsonError
        newScene = NoonScene(noon, space, guid, name)

        return newScene

    def __str__(self):
        """Returns a pretty-printed string for this object."""
        return 'Scene name: "%s" id: "%s"' % (
            self._name, self._guid)

    def __repr__(self):
        """Returns a stringified representation of this object."""
        return str({'name': self._name, 'id': self._guid})