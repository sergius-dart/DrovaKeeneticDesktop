from datetime import datetime
from typing import Callable
from uuid import uuid5

import pytest
import pytest_asyncio

from drova_desktop_keenetic.common.drova import (
    CLIENT_UUID_FAKE,
    PRODUCT_UUID_BG3,
    PRODUCT_UUID_DESKTOP,
    SESSION_UUID_FAKE,
    FakeDrova,
    SessionsEntity,
    StatusEnum,
)


@pytest_asyncio.fixture
async def fake_drova():
    server = FakeDrova()
    await server.start()
    yield server
    await server.close()


@pytest.fixture
def session_entity_desktop() -> Callable[[bool], SessionsEntity]:
    def generator(isnew: bool) -> SessionsEntity:
        return SessionsEntity(
            uuid=uuid5(SESSION_UUID_FAKE, "desktop") if isnew else SESSION_UUID_FAKE,
            product_id=PRODUCT_UUID_DESKTOP,
            client_id=CLIENT_UUID_FAKE,
            created_on=datetime.now(),
            status=StatusEnum.NEW,
            creator_ip="127.0.0.1",
        )

    return generator


@pytest.fixture
def session_entity_bg3() -> Callable[[bool], SessionsEntity]:
    def generator(isnew: bool) -> SessionsEntity:
        return SessionsEntity(
            uuid=uuid5(SESSION_UUID_FAKE, "bg3") if isnew else SESSION_UUID_FAKE,
            product_id=PRODUCT_UUID_BG3,
            client_id=CLIENT_UUID_FAKE,
            created_on=datetime.now(),
            status=StatusEnum.NEW,
            creator_ip="127.0.0.1",
        )

    return generator
