import aiohttp
import pytest
import asyncio
import mock

from aiopynoon.line import ATTR_LINE_STATE, LINE_STATE_OFF, LINE_STATE_ON, NoonLine
from aiopynoon.space import ATTR_ACTIVE_SCENE, ATTR_LIGHTS_ON, NoonSpace
from aiopynoon import Noon

# Authenticate
async def test_authentication(noon):
    result = await noon.authenticate()
    assert result == True

# We should get endpoints
async def test_endpoints(noon):
    websocket_endpoint = noon._endpoints["notification-ws"]
    assert websocket_endpoint is not None

# ...and multiple spaces
async def test_spaces(noon):
    spaces = await noon.spaces
    assert len(spaces) > 0

# ...and multiple lines
async def test_lines(noon):
    lines = await noon.lines
    assert len(lines) > 0

# ...we should have multiple scenes in each space
async def test_scenes_exist(noon):
    spaces = await noon.spaces
    for space in spaces.values():
        assert len(space.scenes) > 0

# ...each space should have an active scene
async def test_active_scene(noon):
    spaces = await noon.spaces
    for space in spaces.values():
        assert space.active_scene_id is not None

# ...and we should have a valid value for lights on, or off
async def test_space_has_lights_on(noon):
    spaces = await noon.spaces
    for space in spaces.values():
        assert space.lights_on is not None

# Test opening the event stream
async def test_open_eventstream(noon):
    await noon.open_eventstream()
    seconds_remaining = 5
    while seconds_remaining > 0:
        await asyncio.sleep(1)
        if noon.event_stream_connected:
            seconds_remaining = 0
        else:
            seconds_remaining = seconds_remaining - 1
    assert noon.event_stream_connected == True, "Not connected to event stream"

# Test making a change to a line
async def test_line_change_1(noon):
    lines = await noon.lines
    first_line = next(iter(lines.values()))
    context = "Context"
    callback = mock.AsyncMock()
    first_line.subscribe(callback, context=context)
    original_line_state = first_line.line_state
    expected_update = None
    expected_state = None

    if original_line_state == LINE_STATE_ON:
        expected_update = {ATTR_LINE_STATE: LINE_STATE_OFF}
        expected_state = LINE_STATE_OFF
        await first_line.turn_off()
    elif original_line_state == LINE_STATE_OFF:
        expected_update = {ATTR_LINE_STATE: LINE_STATE_ON}
        expected_state = LINE_STATE_ON
        await first_line.turn_on()
    else:
        raise "Invalid line state {}".format(original_line_state)

    seconds_remaining = 10
    while seconds_remaining > 0:
        await asyncio.sleep(1)
        if callback.called:
            seconds_remaining = 0
        else:
            seconds_remaining = seconds_remaining - 1
    callback.assert_called()
    assert callback.call_args.args[1] == context, "Context not passed"
    assert callback.call_args.args[2] == NoonLine.Event.LINE_STATE_CHANGED, "Incorrect event type"
    assert callback.call_args.args[3] == expected_update, "Update incorrect"
    assert first_line.line_state == expected_state, "Line 'line_state' not correctly updated" 

# Test making the inverse change to a line
async def test_line_change_2(noon):
    lines = await noon.lines
    first_line = next(iter(lines.values()))
    context = "Context"
    callback = mock.AsyncMock()
    first_line.subscribe(callback, context=context)
    original_line_state = first_line.line_state
    expected_update = None
    expected_state = None

    if original_line_state == LINE_STATE_ON:
        expected_update = {ATTR_LINE_STATE: LINE_STATE_OFF}
        expected_state = LINE_STATE_OFF
        await first_line.turn_off()
    elif original_line_state == LINE_STATE_OFF:
        expected_update = {ATTR_LINE_STATE: LINE_STATE_ON}
        expected_state = LINE_STATE_ON
        await first_line.turn_on()
    else:
        raise "Invalid line state {}".format(original_line_state)

    seconds_remaining = 10
    while seconds_remaining > 0:
        await asyncio.sleep(1)
        if callback.called:
            seconds_remaining = 0
        else:
            seconds_remaining = seconds_remaining - 1
    callback.assert_called()
    assert callback.call_args.args[1] == context, "Context not passed"
    assert callback.call_args.args[2] == NoonLine.Event.LINE_STATE_CHANGED, "Incorrect event type"
    assert callback.call_args.args[3] == expected_update, "Update incorrect"
    assert first_line.line_state == expected_state, "Line 'line_state' not correctly updated" 


# Test toggling the lights in a space
async def test_space_toggle_lights_1(noon):
    spaces = await noon.spaces
    first_space = next(iter(spaces.values()))
    context = "Context"
    callback = mock.AsyncMock()
    first_space.subscribe(callback, context=context)
    original_space_lights_on = first_space.lights_on
    expected_update = {}
    expected_value = None
    if original_space_lights_on:
        expected_value = False
        expected_update={ATTR_LIGHTS_ON: expected_value}
        await first_space.deactivate_scene()
    else:
        expected_value = True
        expected_update={ATTR_LIGHTS_ON: expected_value}
        await first_space.activate_scene()

    seconds_remaining = 10
    while seconds_remaining > 0:
        await asyncio.sleep(1)
        if callback.called:
            seconds_remaining = 0
        else:
            seconds_remaining = seconds_remaining - 1
    callback.assert_called()
    assert callback.call_args.args[1] == context, "Context not passed"
    assert callback.call_args.args[2] == NoonSpace.Event.LIGHTSON_CHANGED, "Incorrect event type"
    assert callback.call_args.args[3] == expected_update, "Update incorrect"
    assert first_space.lights_on == expected_value, "Space 'lights_on' not correctly updated"


# ...and back
async def test_space_toggle_lights_2(noon):
    spaces = await noon.spaces
    first_space = next(iter(spaces.values()))
    context = "Context"
    callback = mock.AsyncMock()
    first_space.subscribe(callback, context=context)
    original_space_lights_on = first_space.lights_on
    expected_update = {}
    expected_value = None
    if original_space_lights_on:
        expected_value = False
        expected_update={ATTR_LIGHTS_ON: expected_value}
        await first_space.deactivate_scene()
    else:
        expected_value = True
        expected_update={ATTR_LIGHTS_ON: expected_value}
        await first_space.activate_scene()

    seconds_remaining = 10
    while seconds_remaining > 0:
        await asyncio.sleep(1)
        if callback.called:
            seconds_remaining = 0
        else:
            seconds_remaining = seconds_remaining - 1
    callback.assert_called()
    assert callback.call_args.args[1] == context, "Context not passed"
    assert callback.call_args.args[2] == NoonSpace.Event.LIGHTSON_CHANGED, "Incorrect event type"
    assert callback.call_args.args[3] == expected_update, "Update incorrect"
    assert first_space.lights_on == expected_value, "Space 'lights_on' not correctly updated"


# Test changing the scene in a space by ID
async def test_space_change_scene_by_id(noon):
    spaces = await noon.spaces
    first_space = next(iter(spaces.values()))
    context = "Context"
    callback = mock.AsyncMock()
    first_space.subscribe(callback, context=context)
    current_scene_id = first_space.active_scene_id
    target_scene_id = None
    for scene_id, scene_name in first_space.scenes.items():
        if scene_id != current_scene_id and target_scene_id is None:
            target_scene_id = scene_id

    assert target_scene_id is not None, "Failed to get a secondary scene in space '{}'".format(first_space.name)
    assert first_space.active_scene_id != target_scene_id, "Test error: target scene is already active"

    await first_space.set_scene(scene_id=target_scene_id)

    seconds_remaining = 10
    while seconds_remaining > 0:
        await asyncio.sleep(1)
        if callback.called:
            seconds_remaining = 0
        else:
            seconds_remaining = seconds_remaining - 1
    callback.assert_called()
    assert callback.call_args.args[1] == context, "Context not passed"
    assert callback.call_args.args[2] == NoonSpace.Event.SCENE_CHANGED, "Incorrect event type"
    assert callback.call_args.args[3] == {ATTR_ACTIVE_SCENE: target_scene_id}, "Update incorrect"
    assert first_space.active_scene_id == target_scene_id, "Failed to correctly 'update active_scene_id'"


# Test changing the scene in a space by name
async def test_space_change_scene_by_name(noon):
    spaces = await noon.spaces
    first_space = next(iter(spaces.values()))
    context = "Context"
    callback = mock.AsyncMock()
    first_space.subscribe(callback, context=context)
    current_scene_name = first_space.scenes[first_space.active_scene_id]
    target_scene_name = None
    target_scene_id = None

    for scene_id, scene_name in first_space.scenes.items():
        if scene_name != current_scene_name and target_scene_name is None:
            target_scene_name = scene_name
            target_scene_id = scene_id

    assert target_scene_name is not None, "Failed to get a secondary scene in space '{}'".format(first_space.name)
    assert first_space.active_scene_id != target_scene_id, "Test error: target scene is already active"

    await first_space.set_scene(scene_name=target_scene_name)

    seconds_remaining = 10
    while seconds_remaining > 0:
        await asyncio.sleep(1)
        if callback.called:
            seconds_remaining = 0
        else:
            seconds_remaining = seconds_remaining - 1
    callback.assert_called()
    assert callback.call_args.args[1] == context, "Context not passed"
    assert callback.call_args.args[2] == NoonSpace.Event.SCENE_CHANGED, "Incorrect event type"
    assert callback.call_args.args[3] == {ATTR_ACTIVE_SCENE: target_scene_id}, "Update incorrect"
    assert first_space.active_scene_id == target_scene_id, "Failed to correctly 'update active_scene_id'"


# Test closing the event stream
async def test_close_eventstream(noon):
    await noon.close_eventstream()
    seconds_remaining = 5
    while seconds_remaining > 0:
        await asyncio.sleep(1)
        if not noon.event_stream_connected:
            seconds_remaining = 0
        else:
            seconds_remaining = seconds_remaining - 1
    assert noon.event_stream_connected == False, "Still connected to event stream"
        


@pytest.fixture(scope="session")
async def noon(loop):
    async with aiohttp.ClientSession() as session:
        noon = Noon(session, "__username__", "__password__")
        yield noon
        if noon.event_stream_connected:
            await noon.close_eventstream()
            await asyncio.sleep(2)

@pytest.fixture(scope="session")
def loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()