from logging import DEBUG, basicConfig
from unittest.mock import AsyncMock
from uuid import uuid5

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
async def test_drova_session_transition(mocker, fake_protector, session_entity_desktop):

    ctx = SessionHandlerContext(config=None, ssh=None, sftp=None, session=session_entity_desktop(True))
    ctx_next = ctx.model_copy()

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

    session_manager = DrovaSessionTransition(fake_protector, Config())
    ctx.session.status = StatusEnum.NEW
    await session_manager.update_ctx(ctx)

    for patch in patchers:
        patch.on_session_start.assert_awaited_once()

    # not call twice
    ctx_next.session.status = StatusEnum.HANDSHAKE
    await session_manager.update_ctx(ctx_next)

    for patch in patchers:
        patch.on_session_start.assert_awaited_once()

    # go to active - call once
    ctx.session.status = StatusEnum.ACTIVE
    await session_manager.update_ctx(ctx)

    for patch in patchers:
        patch.on_session_active.assert_awaited_once()

    # go to end - call once
    ctx_next.session.status = StatusEnum.FINISHED
    await session_manager.update_ctx(ctx_next)

    for patch in patchers:
        patch.on_session_end.assert_awaited_once()

    # not call twice
    ctx.session.status = StatusEnum.ABORTED
    await session_manager.update_ctx(ctx)

    for patch in patchers:
        patch.on_session_end.assert_awaited_once()


@pytest.mark.asyncio
async def test_drova_session_transition_active_from_aborted(mocker, fake_protector, session_entity_desktop):
    ctx = SessionHandlerContext(config=None, ssh=None, sftp=None, session=session_entity_desktop(True))
    ctx_next = ctx.model_copy()
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

    session_manager = DrovaSessionTransition(fake_protector, Config())
    ctx.session.status = StatusEnum.HANDSHAKE
    await session_manager.update_ctx(ctx)

    for patch in patchers:
        patch.on_session_start.assert_awaited_once()

    # not call twice
    ctx_next.session.status = StatusEnum.ABORTED
    await session_manager.update_ctx(ctx_next)

    for patch in patchers:
        patch.on_session_end.assert_awaited_once()


@pytest.mark.asyncio
async def test_drova_session_transition_active(mocker, fake_protector, session_entity_desktop):
    ctx = SessionHandlerContext(config=None, ssh=None, sftp=None, session=session_entity_desktop(True))
    ctx_next = ctx.model_copy()
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

    session_manager = DrovaSessionTransition(fake_protector, Config())
    session_manager._prev_ctx = ctx  # pylint: disable=W0212
    ctx_next.session.status = StatusEnum.FINISHED
    await session_manager.update_ctx(ctx_next)

    for patch in patchers:
        patch.on_session_end.assert_awaited_once()

    # not call twice
    ctx.session.status = StatusEnum.ACTIVE
    await session_manager.update_ctx(ctx)

    for patch in patchers:
        patch.on_session_start.assert_awaited_once()


@pytest.mark.asyncio
async def test_drova_session_transition_active_active_another(
    mocker, fake_protector, session_entity_desktop, session_entity_bg3
):
    ctx = SessionHandlerContext(config=None, ssh=None, sftp=None, session=session_entity_desktop(True))
    ctx_next = SessionHandlerContext(config=None, ssh=None, sftp=None, session=session_entity_bg3(True))
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

    session_manager = DrovaSessionTransition(fake_protector, Config())
    ctx.session.status = StatusEnum.FINISHED
    session_manager._prev_ctx = ctx  # pylint: disable=W0212
    ctx_next.session.status = StatusEnum.ACTIVE
    await session_manager.update_ctx(ctx_next)

    for patch in patchers:
        patch.on_session_start.assert_awaited_once()

    # not call twice
    ctx.session.uuid = uuid5(ctx.session.uuid, "NEW_SESSION")
    ctx.session.status = StatusEnum.ACTIVE
    await session_manager.update_ctx(ctx)

    for patch in patchers:
        patch.on_session_start.assert_awaited_once()
        patch.on_session_end.assert_awaited_once()
