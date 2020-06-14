""" Base class for a Noon space """

import asyncio
import logging
import typing
from .entity import NoonEntity
from .const import Guid
from .event import NoonEvent
from .exceptions import NoonInvalidParametersError, NoonInvalidJsonError
from typing import Any, Callable, Dict, Type

_LOGGER = logging.getLogger(__name__)

ATTR_LIGHTS_ON = "lightsOn"
ATTR_ACTIVE_SCENE = "activeScene"
SPACE_LIGHTS_STATE_ON = "true"
SPACE_LIGHTS_STATE_OFF = "false"
ATTR_LIGHTING_CONFIG_MODIFIED = "lightingConfigModified"


class NoonSpace(NoonEntity):
    
    class Event(NoonEvent):
        """Output events that can be generated.
        SCENE_CHANGED: The scene has changed.
            Params:
            scene: new scene guid (string)
        """
        SCENE_CHANGED = 1

        """
        LIGHTSON_CHANGED: The space lights have turned or off.
            Params:
            lightsOn: Lights are on (boolean)
        """
        LIGHTSON_CHANGED = 2

    @property
    def lights_on(self) -> bool:
        return self._lights_on

    async def set_lights_on(self, new_value: bool):
        assert isinstance(new_value, bool), 'Argument of wrong type!'
        value_changed = (self._lights_on != new_value)
        self._lights_on = new_value
        if value_changed:
            await self._dispatch_event(NoonSpace.Event.LIGHTSON_CHANGED, {ATTR_LIGHTS_ON: self._lights_on})

    @property
    def scenes(self) -> Dict:
        return self._scenes

    @property
    def active_scene_id(self) -> Guid:
        return self._active_scene_id

    async def set_active_scene_id(self, new_value: Guid):
        assert isinstance(new_value, Guid), 'Argument of wrong type!'
        value_changed = (self._active_scene_id != new_value)
        self._active_scene_id = new_value
        if value_changed:
            await self._dispatch_event(NoonSpace.Event.SCENE_CHANGED, {ATTR_ACTIVE_SCENE: self._active_scene_id})

    async def activate_scene(self):
        await self.set_scene(active=True)

    async def deactivate_scene(self):
        await self.set_scene(active=False)

    async def set_scene(self, active:bool=None, scene_id:Guid=None, scene_name:str=None):

        _LOGGER.debug("Set scene to {}".format(scene_id))

        """ (Re)authenticate if needed """
        await self._noon.authenticate()

        """ Replace variables """
        if active is None:
            active = self.lights_on
        
        """ Get the scene ID """
        target_scene_id = None
        target_scene = None

        if scene_id is None and scene_name is None:
            target_scene_id = self.active_scene_id
        if scene_id is not None:
            target_scene_id = scene_id
        elif scene_name is not None:
            for (this_scene_id, this_scene) in self._scenes.items():
                if this_scene.name == scene_name:
                    target_scene_id = this_scene_id
            if target_scene_id is None:
                raise NoonInvalidParametersError("Scene '{}' not found".format(scene_name))
        
        """ Get the scene """
        try:
            target_scene = self.scenes[target_scene_id]
        except KeyError:
            raise NoonInvalidParametersError("Scene id '{}' not found".format(target_scene_id))

        """ Send the command """
        _LOGGER.debug("Attempting to activate scene {} in space '{}', with active = {}".format(target_scene.name, self.name, active))
        actionUrl = "{}/api/action/space/scene".format(self._noon._endpoints["action"])
        async with self._noon.session.post(actionUrl, 
            headers={"Authorization": "Token {}".format(self._noon._token)}, 
            json={"space": self.guid, "activeScene": target_scene.guid, "on": active, "tid": 55555}, 
            raise_for_status=True) as raw_response:

            _LOGGER.debug("Got set_scene result {}: {}".format(raw_response.status, raw_response))

    def __init__(self, noon, guid, name, active_scene_id:Guid=None, lights_on:bool=None, lines:Dict={}, scenes:Dict={}):
        """Initialize the space."""
        self._active_scene_id = None
        self._lights_on = None
        self._lines = None
        self._scenes = None
        self._active_scene_id = active_scene_id
        self._lights_on = lights_on
        super().__init__(noon, guid, name)

    async def handle_update(self, changed_fields):
        """Handle an update from an event notification."""
        _LOGGER.debug("Asked to update with {}".format(changed_fields))
        for changed_field in changed_fields:
            if changed_field["name"] == ATTR_LIGHTS_ON:
                new_value = None
                if changed_field["value"] == SPACE_LIGHTS_STATE_ON or changed_field["value"] == True:
                    new_value = True
                elif changed_field["value"] == SPACE_LIGHTS_STATE_OFF or changed_field["value"] == False:
                    new_value = False
                else:
                    raise NoonInvalidParametersError("Invalid lightsOn value '{}'".format(changed_field["value"]))
                await self.set_lights_on(new_value)
            elif changed_field["name"] == ATTR_ACTIVE_SCENE:
                await self.set_active_scene_id(changed_field["value"]["guid"])
            elif changed_field["name"] == ATTR_LIGHTING_CONFIG_MODIFIED:
                pass
            else:
                _LOGGER.warn("Unhandled change to field '{}'".format(changed_field["name"]))

    @classmethod
    async def from_json(cls, noon, json):
        """Initialize a Noon Space from JSON"""

        from .scene import NoonScene
        from .line import NoonLine

        """Basics"""
        guid = json.get("guid", None)
        name = json.get("name", None)
        lights_on = json.get("lightsOn", None)
        active_scene_id = json.get("activeScene", {}).get("guid", None)

        if guid is None or name is None:
            _LOGGER.debug("Invalid JSON payload: {}".format(json))
            raise NoonInvalidJsonError
        new_space = NoonSpace(noon, guid, name, active_scene_id, lights_on)

        """Scenes"""
        scenes_map = {}
        for scene in json.get("scenes", []):
            this_scene = await NoonScene.from_json(noon, new_space, scene)
            scenes_map[this_scene.guid] = this_scene
        new_space._scenes = scenes_map

        """Lines"""
        lines_map = {}
        for line in json.get("lines", []):
            this_line = await NoonLine.from_json(noon, new_space, line)
            lines_map[this_line.guid] = this_line
        new_space._lines = lines_map
        
        return new_space