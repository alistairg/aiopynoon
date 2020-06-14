"""Base type for Noon entities"""

import asyncio
import logging

from .exceptions import NoonInvalidJsonError
from typing import Callable, Dict, Any
from .const import Guid
from .event import NoonEvent

NoonEventHandler = Callable[['NoonEntity', Any, 'NoonEvent', Dict], None]

_LOGGER = logging.getLogger(__name__)

class NoonEntity(object):

    @property 
    def name(self):
        """Returns the entity name (e.g. Pendant)."""
        return self._name

    @property 
    def guid(self) -> Guid:
        """Returns the entity unique ID (GUID from Noon)."""
        return self._guid

    def __init__(self, noon, guid: Guid, name: str):
        """Initializes the base class with common, basic data."""
        self._noon = noon
        self._name = name
        self._guid = guid
        self._subscribers = []
        noon._registerEntity(self)

    async def _dispatch_event(self, event: NoonEvent, params: Dict):
        """Dispatches the specified event to all the subscribers."""
        _LOGGER.debug("Sending notifications!")
        for handler, context in self._subscribers:
            _LOGGER.debug("...notification sent.")
            try:
                await handler(self, context, event, params)
            except:
                _LOGGER.exception("Exception handling update for {}".format(self.name))

    def subscribe(self, handler: NoonEventHandler, context):
        """Subscribes to events from this entity.
        handler: A callable object that takes the following arguments (in order)
                obj: the NoonEntity object that generated the event
                context: user-supplied (to subscribe()) context object
                event: the LutronEvent that was generated.
                params: a dict of event-specific parameters
        context: User-supplied, opaque object that will be passed to handler.
        """
        _LOGGER.debug("Added update subscriber for {}".format(self.name))
        self._subscribers.append((handler, context))

    def unsubscribe_all(self):
        """Remove all subscribers."""
        self._subscribers.clear()

    def unsubscribe(self, handler, context):
        """Remove a specific handler."""
        self._subscribers.remove((handler, context))
    
    async def handle_update(self, changed_fields):
        """The handle_update callback is invoked when an event is received
        for the this entity.
        """
        raise NotImplementedError

    @classmethod
    async def from_json(cls, noon, json):
        """Subclasses must override this method"""
        raise NoonInvalidJsonError