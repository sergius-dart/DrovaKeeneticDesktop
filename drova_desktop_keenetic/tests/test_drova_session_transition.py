from logging import DEBUG, basicConfig
from unittest.mock import AsyncMock

import pytest

from drova_desktop_keenetic.common.config import Config
from drova_desktop_keenetic.common.context import SessionHandlerContext
from drova_desktop_keenetic.common.drova import StatusEnum
from drova_desktop_keenetic.common.drova_session_transition import (
    DrovaSessionTransition,
)
from drova_desktop_keenetic.common.patch import ISessionHandler

basicConfig(level=DEBUG)


@pytest.fixture
def fake_protector():
    class FakeProtector(ISessionHandler):

        async def on_idle(self, ctx):
            return await super().on_idle(ctx)

        async def on_session_start(self, ctx):
            return await super().on_session_start(ctx)

        async def on_session_active(self, ctx):
            return await super().on_session_active(ctx)

        async def on_session_end(self, ctx):
            return await super().on_session_end(ctx)

    return FakeProtector(Config())


@pytest.mark.asyncio
async def test_drova_session_transition(mocker, fake_protector):

    ctx = SessionHandlerContext(config=None, ssh=None, sftp=None)
    patchers = [
        AsyncMock(),
        AsyncMock(),
    ]

    for p in patchers:
        p.on_idle = AsyncMock()
        p.on_session_start = AsyncMock()
        p.on_session_active = AsyncMock()
        p.on_session_end = AsyncMock()

    mocker.patch("drova_desktop_keenetic.common.drova_session_transition.make_patchers", return_value=patchers)

    session_manager = DrovaSessionTransition(None, fake_protector, Config())
    await session_manager.set_status(StatusEnum.NEW, ctx)

    for patch in patchers:
        patch.on_session_start.assert_awaited_once()

    # not call twice
    await session_manager.set_status(StatusEnum.HANDSHAKE, ctx)

    for patch in patchers:
        patch.on_session_start.assert_awaited_once()

    # go to active - call once
    await session_manager.set_status(StatusEnum.ACTIVE, ctx)

    for patch in patchers:
        patch.on_session_active.assert_awaited_once()

    # go to end - call once
    await session_manager.set_status(StatusEnum.FINISHED, ctx)

    for patch in patchers:
        patch.on_session_end.assert_awaited_once()

    # not call twice
    await session_manager.set_status(StatusEnum.ABORTED, ctx)

    for patch in patchers:
        patch.on_session_end.assert_awaited_once()


@pytest.mark.asyncio
async def test_drova_session_transition_active_from_aborted(mocker, fake_protector):
    ctx = SessionHandlerContext(config=None, ssh=None, sftp=None)
    patchers = [
        AsyncMock(),
        AsyncMock(),
    ]

    for p in patchers:
        p.on_idle = AsyncMock()
        p.on_session_start = AsyncMock()
        p.on_session_active = AsyncMock()
        p.on_session_end = AsyncMock()

    mocker.patch("drova_desktop_keenetic.common.drova_session_transition.make_patchers", return_value=patchers)

    session_manager = DrovaSessionTransition(StatusEnum.ACTIVE, fake_protector, Config())
    await session_manager.set_status(StatusEnum.HANDSHAKE, ctx)

    for patch in patchers:
        patch.on_session_start.assert_awaited_once()

    # not call twice
    await session_manager.set_status(StatusEnum.ABORTED, ctx)

    for patch in patchers:
        patch.on_session_end.assert_awaited_once()


@pytest.mark.asyncio
async def test_drova_session_transition_active(mocker, fake_protector):
    ctx = SessionHandlerContext(config=None, ssh=None, sftp=None)
    patchers = [
        AsyncMock(),
        AsyncMock(),
    ]

    for p in patchers:
        p.on_idle = AsyncMock()
        p.on_session_start = AsyncMock()
        p.on_session_active = AsyncMock()
        p.on_session_end = AsyncMock()

    mocker.patch("drova_desktop_keenetic.common.drova_session_transition.make_patchers", return_value=patchers)

    session_manager = DrovaSessionTransition(StatusEnum.ACTIVE, fake_protector, Config())
    await session_manager.set_status(None, ctx)

    for patch in patchers:
        patch.on_session_end.assert_awaited_once()

    # not call twice
    await session_manager.set_status(None, ctx)

    for patch in patchers:
        patch.on_idle.assert_awaited_once()
