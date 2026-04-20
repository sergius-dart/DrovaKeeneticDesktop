import pytest_asyncio

from drova_desktop_keenetic.common.drova import FakeDrova


@pytest_asyncio.fixture
async def fake_drova():
    server = FakeDrova()
    await server.start()
    yield server
    await server.close()
