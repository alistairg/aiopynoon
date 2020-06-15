""" Base class for a Noon line. """

from .entity import NoonEntity
import asyncio
from typing import Dict
import logging

from .const import Guid
from .entity import NoonEntity
from .event import NoonEvent
from .exceptions import NoonInvalidJsonError

_LOGGER = logging.getLogger(__name__)
LINE_STATE_ON = "on"
LINE_STATE_OFF = "off"
ATTR_LINE_STATE = "lineState"
ATTR_DIM_LEVEL = "dimmingLevel"

class NoonLine(NoonEntity):

    class Event(NoonEvent):
        """Output events that can be generated.
        DIM_LEVEL_CHANGED: The dim level of this line has changed.
            Params:
            dimLevel: New dim level percent (integer)
        """
        DIM_LEVEL_CHANGED = 1

        """
        LINE_STATE_CHANGED: The line lights have turned or off.
            Params:
            lineState: Line State (string - 'on' or 'off')
        """
        LINE_STATE_CHANGED = 2

    @property
    def line_state(self) -> str:
        return self._line_state

    async def set_line_state(self, value:str):

        value_changed = (self._line_state != value)
        self._line_state = value
        if value_changed:
            await self._dispatch_event(NoonLine.Event.LINE_STATE_CHANGED, {ATTR_LINE_STATE: self._line_state})
    
    @property
    def parent_space(self):
        return self._parent_space

    @property
    def dimming_level(self) -> int:
        return self._dimming_level

    async def set_dimming_level(self, value: int):
        value_changed = (self._dimming_level != value)
        self._dimming_level = value
        if value_changed:
            await self._dispatch_event(NoonLine.Event.DIM_LEVEL_CHANGED, {ATTR_DIM_LEVEL: self._dimming_level})

    async def set_brightness(self, brightness_level: int, transition_time:int=None):

        """ (Re)authenticate if needed """
        await self._noon.authenticate()

        """ Send the command """
        _LOGGER.debug("Setting brightness to {}% with transition time {}s".format(brightness_level, transition_time))
        actionUrl = "{}/api/action/line/lightLevel".format(self._noon._endpoints["action"])
        json = {"line": self.guid, "lightLevel": brightness_level, "tid": 55555}
        if transition_time is not None:
            json["transitionTime"] = transition_time
        async with self._noon.session.post(actionUrl, headers={"Authorization": "Token {}".format(self._noon._token)}, json=json, raise_for_status=True) as raw_response:
            _LOGGER.debug("Got set_brightness result {}: {}".format(raw_response.status, raw_response))
    

    async def turn_on(self):
        
        await self.set_brightness(100)

    async def turn_off(self):
        
        await self.set_brightness(0)

    def __init__(self, noon, parent_space, guid: Guid, name: str, dimming_level: int=None, line_state: bool=None):
        
        super().__init__(noon, guid, name)

        """Initializes the Line."""
        self._line_state = None
        self._dimming_level = None
        self._parent_space = parent_space
        self._line_state = line_state
        self._dimming_level = dimming_level

    async def handle_update(self, changed_fields):
        """Handle an update from an event notification."""
        _LOGGER.debug("Asked to update with {}".format(changed_fields))
        for changed_field in changed_fields:
            if changed_field["name"] == ATTR_LINE_STATE:
                await self.set_line_state(changed_field["value"])
            elif changed_field["name"] == ATTR_DIM_LEVEL:
                await self.set_dimming_level(changed_field["value"])
            else:
                _LOGGER.warn("Unhandled change to field '{}'".format(changed_field["name"]))

    @classmethod
    async def from_json(cls, noon, space, json):
        """Construct a Line from a JSON payload."""

        # Sanity - should be parsed
        assert isinstance(json, Dict), "JSON is not parsed - expected a Dict but got {}".format(type(json))

        """Basics"""
        guid = json.get("guid", None)
        name = json.get("displayName", "Unknown")

        if guid is None:
            _LOGGER.debug("Invalid JSON payload: {}".format(json))
            raise NoonInvalidJsonError
        line_state = json.get("lineState", None)
        dimming_level = json.get("dimmingLevel", None)
        new_line = NoonLine(noon, space, guid, name, dimming_level, line_state)

        return new_line

    def __str__(self):
        """Returns a pretty-printed string for this object."""
        return 'Line name: "%s" lights on: %s, dim level: "%s"' % (
            self.name, self._line_state, self._dimming_level)

    def __repr__(self):
        """Returns a stringified representation of this object."""
        return str({'name': self.name, 'dimmingLevel': self._dimming_level,
                    'lightsOn': self._line_state, 'id': self._guid})