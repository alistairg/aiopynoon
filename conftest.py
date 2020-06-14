import pytest
import asyncio
from aiopynoon import Noon
import aiohttp

# Add parameters for username and password
def pytest_addoption(parser):
    parser.addoption(
        "--username", action="store", default=None, help="Noon Username"
    )
    parser.addoption(
        "--password", action="store", default=None, help="Noon Password"
    )

@pytest.fixture(scope="session")
def username(request):
    return request.config.getoption("--username")

@pytest.fixture(scope="session")
def password(request):
    return request.config.getoption("--password")

@pytest.fixture(scope="session")
async def noon(loop, username, password):
    assert username is not None, "No username provided using --username option"
    assert password is not None, "No password provided using --password option"
    async with aiohttp.ClientSession() as session:
        noon = Noon(session, username, password)
        yield noon
        if noon.event_stream_connected:
            await noon.close_eventstream()
            await asyncio.sleep(2)

@pytest.fixture(scope="session")
def loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()