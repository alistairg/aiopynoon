import logging
import asyncio
from asyncio import CancelledError
from aiohttp import ClientSession, WSMsgType, ClientTimeout, WSServerHandshakeError
import json
import datetime
import traceback
import typing
from .const import (
    LOGIN_URL,
    DEX_URL,
    Guid
)
from .space import NoonSpace
from .line import NoonLine
from .entity import NoonEntity
from .scene import NoonScene
from .exceptions import (
    NoonAuthenticationError,
    NoonUnknownError,
    NoonProtocolError,
    NoonDuplicateIdError
)

_LOGGER = logging.getLogger(__name__)



class Noon(object):
    """Base object for Noon Home."""

    @property
    async def spaces(self) -> typing.Dict[Guid, NoonSpace]:
        if self._spaces is None:
            await self._refreshDevices()
        return self._spaces

    @property
    async def lines(self) -> typing.Dict[Guid, NoonLine]: 
        if self._lines is None:
            await self._refreshDevices()
        return self._lines

    @property
    def session(self) -> ClientSession:
        return self._session

    @property
    def event_stream_connected(self) -> bool:
        return self._event_stream_connected

    @property
    def event_stream_error(self) -> str:
        return self._event_stream_error

    def __init__(self, session, username, password):
        """Create a PyNoone object.

        :param username: Noon username
        :param password: Noon password

        :returns PyNoon base object
        
        """
    
        # Properties
        self._spaces = None
        self._lines = None
        self._scenes = None
        self._all_entities = {}
        self._endpoints = {}
        self._event_stream_connected = False
        self._event_stream_error = None

        # Store credentials
        self._username = username
        self._password = password
        self._token = None
        self._token_expires = None

        # AIOHTTP
        self._session = session
        self._websocket_task = None

    
    async def authenticate(self) -> bool:
        """Authenticate with Noon and store the authentication token."""

        """Reuse token if we have one."""
        if self._token is not None and self._token_expires > datetime.datetime.now():
            _LOGGER.debug("Using cached token, which should still be valid")
            return True

        """ Authenticate user, and get tokens """
        _LOGGER.debug("No valid token or token expired. Authenticating...")
        payload = {
            "email": self._username,
            "password": self._password
        }
        async with self.session.post(LOGIN_URL, json=payload) as login_response:
            parsed_response = await login_response.json()
            _LOGGER.debug("Response: {}".format(parsed_response))

            # Invalid response from noon
            if not isinstance(parsed_response, dict):
                _LOGGER.error("Response from authentication was not a dictionary")
                raise NoonProtocolError

            # Single error from noon
            if "error" in parsed_response.keys():
                raise NoonAuthenticationError

            # Errors from Noon
            if parsed_response.get("errors") is not None:
                _LOGGER.error("Multiple authentication errors from Noon - {}".format(parsed_response["errors"]))
                raise NoonUnknownError

            # Must have a token and lifetime
            try:
                self._token = parsed_response["token"]
                self._token_expires = datetime.datetime.now() + datetime.timedelta(seconds = (parsed_response["lifetime"]-30))
                _LOGGER.debug("Got token from Noon. Expires at {}".format(self._token_expires))
            except KeyError:
                _LOGGER.error("Failed to get token or lifetime from {}".format(parsed_response))
                raise NoonUnknownError

            # Get endpoints if needed
            await self._refreshEndpoints()

            # Success
            return True



    async def open_eventstream(self, event_loop=None):
        """Create a background task for the event stream."""
        if event_loop is None:
            _LOGGER.debug("Using main asyncio event loop")
            event_loop = asyncio.get_running_loop()
        assert self._websocket_task is None or self._websocket_task.cancelled(), "Already running an event stream task"
        self._websocket_task = event_loop.create_task(self._internal_eventstream())


    async def close_eventstream(self):
        """Close the event stream background task."""
        if self._websocket_task is not None and not self._websocket_task.cancelled():
            _LOGGER.debug("Canceling websocket task")
            self._websocket_task.cancel()

    async def _internal_eventstream(self):
        """Loop for connecting to the Noon notification stream."""
        keep_looping = True
        while keep_looping:
            try:
                await self.authenticate()
                timeout = ClientTimeout(total=8, connect=20, sock_connect=20, sock_read=8)
                event_stream_url = "{}/api/notifications".format(self._endpoints["notification-ws"])
                _LOGGER.debug("Connecting to notification stream...")
                async with self.session.ws_connect(event_stream_url, timeout=timeout, heartbeat=60, headers={"Authorization": "Token {}".format(self._token)}) as ws:
                    _LOGGER.debug("Connected to notification stream")
                    self._event_stream_connected = True
                    self._event_stream_error = None
                    async for msg in ws:
                        if msg.type == WSMsgType.TEXT:
                            _LOGGER.debug("Got websocket message: {}".format(msg.data))
                            parsed_data = json.loads(msg.data)
                            changes = parsed_data["data"].get("changes", [])
                            for change in changes:
                                await self._handle_change(change)
                        elif msg.type == WSMsgType.CLOSED:
                            _LOGGER.error("Socket closed")
                            raise NoonProtocolError("Notification stream closed unexpectedly")
                        elif msg.type == WSMsgType.ERROR:
                            _LOGGER.error("Websocket error")
                            raise NoonProtocolError("Unknown error on notification stream")
            except CancelledError:
                _LOGGER.debug("Loop canceled.")
                self._event_stream_error = "Canceled"
                keep_looping = False
            except WSServerHandshakeError:
                _LOGGER.error("Loop Fatal: Handshake error")
                self._event_stream_error = "Handshake Error"
                keep_looping = False
            except Exception:
                _LOGGER.exception("Loop Fatal: Generic exception during event loop")
                self._event_stream_error = "Unknown exception - {}".format(traceback.format_exc())
                keep_looping = False
            finally:
                _LOGGER.debug("Event stream is disconnected.")
                self._event_stream_connected = False

    async def _handle_change(self, change):
        """Process a change notification."""

        guid = change.get("guid", None)
        if guid is None:
            _LOGGER.error("Cannot process change - no GUID in {}".format(change))
            return

        affected_entity = self._all_entities.get(guid, None)
        if affected_entity is None:
            _LOGGER.debug("UNEXPECTED: Got change notification for {}, but not an expected entity! ({}".format(guid, change))
            return

        _LOGGER.debug("Got change notification for '{}' - {}".format(affected_entity.name, change))
        changed_fields = change.get("fields", [])
        return await affected_entity.handle_update(changed_fields)

    def get_entity(self, entity_id: Guid) -> NoonEntity:
        return self._all_entities.get(entity_id, None)

    async def _refreshEndpoints(self):
        """Update the noon endpoints for this account"""
        
        if len(self._endpoints) > 0:
            return

        await self.authenticate()
        async with self.session.get(DEX_URL, headers={
            "Authorization": "Token {}".format(self._token)
        }) as login_response:
            parsed_response = await login_response.json()

            # Must be a dictionary
            if not isinstance(parsed_response, dict):
                _LOGGER.error("Response from get endpoints was not a dictionary - {}".format(parsed_response))
                raise NoonProtocolError

            # Store
            try:
                self._endpoints = parsed_response["endpoints"]
            except KeyError:
                _LOGGER.error("Unexpected endpoints response {}".format(parsed_response))
                raise NoonUnknownError

    def _registerEntity(self, entity: NoonEntity):

        """ EVERYTHING """
        self._all_entities[entity.guid] = entity

        """ SPACE """
        if isinstance(entity, NoonSpace):
            existingEntity = self._spaces.get(entity.guid, None)
            if existingEntity is not None:
                if entity.name != existingEntity.name and False:
                    _LOGGER.error("New space '{}' has same ID as existing space '{}'".format(entity.name, existingEntity.name))
                    raise NoonDuplicateIdError
                else:
                    return
            else:
                self._spaces[entity.guid] = entity	

        """ LINE """
        if isinstance(entity, NoonLine):
            existingEntity = self._lines.get(entity.guid, None)
            if existingEntity is not None:
                if entity.name != existingEntity.name and False:
                    _LOGGER.error("New line '{}' has same ID as existing line '{}'".format(entity.name, existingEntity.name))
                    raise NoonDuplicateIdError
                else:
                    return
            else:
                self._lines[entity.guid] = entity	

        """ SCENE """
        if isinstance(entity, NoonScene):
            existingEntity = self._scenes.get(entity.guid, None)
            if existingEntity is not None:
                if entity.name != existingEntity.name and False:
                    _LOGGER.error("New scene '{}' has same ID as existing scene '{}'".format(entity.name, existingEntity.name))
                    raise NoonDuplicateIdError
                else:
                    return
            else:
                self._scenes[entity.guid] = entity	

    async def _refreshDevices(self):
        """Load the devices (spaces/lines) on this account."""

        # Reset cache
        self._spaces = {}
        self._scenes = {}
        self._lines = {}

        # Authenticate if needed
        await self.authenticate()

        # Load the device details
        url = "{}/api/query".format(self._endpoints["query"])
        headers = {
            "Authorization": "Token {}".format(self._token),
            "Content-Type": "application/graphql"
        }
        data = "{spaces {guid name lightsOn activeScene{guid name} lines{guid lineState displayName dimmingLevel multiwayMaster { guid }} scenes{name guid}}}"
        async with self.session.post(url, headers=headers, data=data) as discovery_response:
            parsed_response = await discovery_response.json()

            # Must be a dictionary
            if not isinstance(parsed_response, dict):
                _LOGGER.error("Response from discovery was not a dictionary - {}".format(parsed_response))
                raise NoonProtocolError

            # Parse spaces
            for space in parsed_response["spaces"]:
                this_space = await NoonSpace.from_json(self, space)
                _LOGGER.debug("Discovered space {}".format(this_space.name))