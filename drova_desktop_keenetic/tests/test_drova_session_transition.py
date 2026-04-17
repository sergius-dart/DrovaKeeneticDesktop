from unittest.mock import AsyncMock

import pytest

from drova_desktop_keenetic.common.drova import StatusEnum
from drova_desktop_keenetic.common.drova_session_transition import (
    DrovaSessionTransition,
)


@pytest.mark.asyncio
async def test_drova_session_transition(mocker):

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

    session_manager = DrovaSessionTransition(None)
    await session_manager.set_status(StatusEnum.NEW)

    for patch in patchers:
        patch.on_session_start.assert_awaited_once()

    # not call twice
    await session_manager.set_status(StatusEnum.HANDSHAKE)

    for patch in patchers:
        patch.on_session_start.assert_awaited_once()

    # go to active - call once
    await session_manager.set_status(StatusEnum.ACTIVE)

    for patch in patchers:
        patch.on_session_active.assert_awaited_once()

    # go to end - call once
    await session_manager.set_status(StatusEnum.FINISHED)

    for patch in patchers:
        patch.on_session_end.assert_awaited_once()

    # not call twice
    await session_manager.set_status(StatusEnum.ABORTED)

    for patch in patchers:
        patch.on_session_end.assert_awaited_once()


@pytest.mark.asyncio
async def test_drova_session_transition_active(mocker):

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

    session_manager = DrovaSessionTransition(StatusEnum.ACTIVE)
    await session_manager.set_status(StatusEnum.HANDSHAKE)

    for patch in patchers:
        patch.on_session_start.assert_awaited_once()

    # not call twice
    await session_manager.set_status(StatusEnum.ABORTED)

    for patch in patchers:
        patch.on_session_end.assert_awaited_once()
