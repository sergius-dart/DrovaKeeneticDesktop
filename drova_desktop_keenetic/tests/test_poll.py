from datetime import datetime
from logging import DEBUG, basicConfig
from unittest.mock import AsyncMock

import pytest
from asyncssh import SSHCompletedProcess

from drova_desktop_keenetic.common.config import Config
from drova_desktop_keenetic.common.drova import (
    CLIENT_UUID_FAKE,
    PRODUCT_UUID_BG3,
    PRODUCT_UUID_DESKTOP,
    SESSION_UUID_FAKE,
    DrovaService,
    FakeDrova,
    ProductInfo,
    SessionsEntity,
    SessionsResponse,
    StatusEnum,
)
from drova_desktop_keenetic.common.drova_poll import DrovaPoll
from drova_desktop_keenetic.common.helpers import RebootRequired

basicConfig(level=DEBUG)


@pytest.mark.asyncio
async def test_poll_full(fake_drova: FakeDrova):
    ssh = AsyncMock()
    sftp = AsyncMock()

    patcher = AsyncMock()
    patcher.on_idle = AsyncMock()
    patcher.on_session_start = AsyncMock()
    patcher.on_session_active = AsyncMock()
    patcher.on_session_end = AsyncMock()

    config = Config(windows_host="127.0.0.1")
    drova_poll = DrovaPoll(config)
    drova_poll.ctx.ssh = ssh
    drova_poll.ctx.sftp = sftp
    drova_poll.drova_service = DrovaService(fake_drova.faked_host)
    drova_poll.drova_transition._patchers = [patcher]  # pylint: disable=W0212
    drova_poll.get_server_id = AsyncMock(return_value=str(SESSION_UUID_FAKE))
    drova_poll.get_auth_token = AsyncMock(return_value=str(SESSION_UUID_FAKE))

    # no session
    fake_drova.session = None
    await drova_poll.one_poll(ssh)
    patcher.on_idle.assert_not_awaited()
    patcher.on_session_start.assert_not_awaited()
    patcher.on_session_active.assert_not_awaited()
    patcher.on_session_end.assert_not_awaited()

    # start desktop session
    fake_drova.session = SessionsResponse(
        sessions=(
            SessionsEntity(
                uuid=SESSION_UUID_FAKE,
                product_id=PRODUCT_UUID_DESKTOP,
                client_id=CLIENT_UUID_FAKE,
                created_on=datetime.now(),
                status=StatusEnum.NEW,
                creator_ip="127.0.0.1",
            ),
        )
    )
    fake_drova.product = ProductInfo(product_id=PRODUCT_UUID_DESKTOP, use_default_desktop=True)
    await drova_poll.one_poll(ssh)
    patcher.on_idle.assert_not_awaited()
    patcher.on_session_start.assert_awaited_once()
    patcher.on_session_active.assert_not_awaited()
    patcher.on_session_end.assert_not_awaited()

    fake_drova.session.sessions[0].status = StatusEnum.HANDSHAKE
    await drova_poll.one_poll(ssh)
    patcher.on_idle.assert_not_awaited()
    patcher.on_session_start.assert_awaited_once()
    patcher.on_session_active.assert_not_awaited()
    patcher.on_session_end.assert_not_awaited()

    fake_drova.session.sessions[0].status = StatusEnum.ACTIVE
    await drova_poll.one_poll(ssh)
    patcher.on_idle.assert_not_awaited()
    patcher.on_session_start.assert_awaited_once()
    patcher.on_session_active.assert_awaited_once()
    patcher.on_session_end.assert_not_awaited()

    fake_drova.session.sessions[0].status = StatusEnum.ABORTED
    await drova_poll.one_poll(ssh)
    patcher.on_idle.assert_not_awaited()
    patcher.on_session_start.assert_awaited_once()
    patcher.on_session_active.assert_awaited_once()
    patcher.on_session_end.assert_awaited_once()

    # no session - close normal go to idle
    fake_drova.session = None
    await drova_poll.one_poll(ssh)
    patcher.on_idle.assert_awaited_once()
    patcher.on_session_start.assert_awaited_once()
    patcher.on_session_active.assert_awaited_once()
    patcher.on_session_end.assert_awaited_once()


@pytest.mark.asyncio
async def test_poll_active_to_none_from_finished(fake_drova: FakeDrova):
    ssh = AsyncMock()
    sftp = AsyncMock()

    patcher = AsyncMock()
    patcher.on_idle = AsyncMock()
    patcher.on_session_start = AsyncMock()
    patcher.on_session_active = AsyncMock()
    patcher.on_session_end = AsyncMock()

    config = Config(windows_host="127.0.0.1")
    drova_poll = DrovaPoll(config)
    drova_poll.ctx.ssh = ssh
    drova_poll.ctx.sftp = sftp
    drova_poll.drova_service = DrovaService(fake_drova.faked_host)
    drova_poll.drova_transition._patchers = [patcher]  # pylint: disable=W0212
    drova_poll.get_server_id = AsyncMock(return_value=str(SESSION_UUID_FAKE))
    drova_poll.get_auth_token = AsyncMock(return_value=str(SESSION_UUID_FAKE))

    # connect on  desktop session started
    fake_drova.session = SessionsResponse(
        sessions=(
            SessionsEntity(
                uuid=SESSION_UUID_FAKE,
                product_id=PRODUCT_UUID_DESKTOP,
                client_id=CLIENT_UUID_FAKE,
                created_on=datetime.now(),
                status=StatusEnum.ACTIVE,
                creator_ip="127.0.0.1",
            ),
        )
    )
    fake_drova.product = ProductInfo(product_id=PRODUCT_UUID_DESKTOP, use_default_desktop=True)
    await drova_poll.one_poll(ssh)
    patcher.on_idle.assert_not_awaited()
    patcher.on_session_start.assert_not_awaited()
    patcher.on_session_active.assert_awaited_once()
    patcher.on_session_end.assert_not_awaited()

    fake_drova.session.sessions[0].status = StatusEnum.FINISHED
    await drova_poll.one_poll(ssh)
    patcher.on_idle.assert_not_awaited()
    patcher.on_session_start.assert_not_awaited()
    patcher.on_session_active.assert_awaited_once()
    patcher.on_session_end.assert_awaited_once()

    # no session - idle
    fake_drova.session = None
    await drova_poll.one_poll(ssh)
    patcher.on_idle.assert_awaited_once()
    patcher.on_session_start.assert_not_awaited()
    patcher.on_session_active.assert_awaited_once()
    patcher.on_session_end.assert_awaited_once()


@pytest.mark.asyncio
async def test_poll_active_to_none(fake_drova: FakeDrova):
    ssh = AsyncMock()
    sftp = AsyncMock()

    patcher = AsyncMock()
    patcher.on_idle = AsyncMock()
    patcher.on_session_start = AsyncMock()
    patcher.on_session_active = AsyncMock()
    patcher.on_session_end = AsyncMock()

    config = Config(windows_host="127.0.0.1")
    drova_poll = DrovaPoll(config)
    drova_poll.ctx.ssh = ssh
    drova_poll.ctx.sftp = sftp
    drova_poll.drova_service = DrovaService(fake_drova.faked_host)
    drova_poll.drova_transition._patchers = [patcher]  # pylint: disable=W0212
    drova_poll.get_server_id = AsyncMock(return_value=str(SESSION_UUID_FAKE))
    drova_poll.get_auth_token = AsyncMock(return_value=str(SESSION_UUID_FAKE))

    # connect on  desktop session started
    fake_drova.session = SessionsResponse(
        sessions=(
            SessionsEntity(
                uuid=SESSION_UUID_FAKE,
                product_id=PRODUCT_UUID_DESKTOP,
                client_id=CLIENT_UUID_FAKE,
                created_on=datetime.now(),
                status=StatusEnum.ACTIVE,
                creator_ip="127.0.0.1",
            ),
        )
    )
    fake_drova.product = ProductInfo(product_id=PRODUCT_UUID_DESKTOP, use_default_desktop=True)
    await drova_poll.one_poll(ssh)
    patcher.on_idle.assert_not_awaited()
    patcher.on_session_start.assert_not_awaited()
    patcher.on_session_active.assert_awaited_once()
    patcher.on_session_end.assert_not_awaited()

    # no session - idle - need close
    fake_drova.session = None
    await drova_poll.one_poll(ssh)
    patcher.on_idle.assert_not_awaited()
    patcher.on_session_start.assert_not_awaited()
    patcher.on_session_active.assert_awaited_once()
    patcher.on_session_end.assert_awaited_once()

    # no session - idle
    fake_drova.session = None
    await drova_poll.one_poll(ssh)
    patcher.on_idle.assert_awaited_once()
    patcher.on_session_start.assert_not_awaited()
    patcher.on_session_active.assert_awaited_once()
    patcher.on_session_end.assert_awaited_once()


@pytest.mark.asyncio
async def test_poll_full_not_a_desktop(fake_drova: FakeDrova):
    ssh = AsyncMock()
    sftp = AsyncMock()

    patcher = AsyncMock()
    patcher.on_idle = AsyncMock()
    patcher.on_session_start = AsyncMock()
    patcher.on_session_active = AsyncMock()
    patcher.on_session_end = AsyncMock()

    config = Config(windows_host="127.0.0.1")
    drova_poll = DrovaPoll(config)
    drova_poll.ctx.ssh = ssh
    drova_poll.ctx.sftp = sftp
    drova_poll.drova_service = DrovaService(fake_drova.faked_host)
    drova_poll.drova_transition._patchers = [patcher]  # pylint: disable=W0212
    drova_poll.get_server_id = AsyncMock(return_value=str(SESSION_UUID_FAKE))
    drova_poll.get_auth_token = AsyncMock(return_value=str(SESSION_UUID_FAKE))

    # no session
    fake_drova.session = None
    await drova_poll.one_poll(ssh)
    patcher.on_idle.assert_not_awaited()
    patcher.on_session_start.assert_not_awaited()
    patcher.on_session_active.assert_not_awaited()
    patcher.on_session_end.assert_not_awaited()

    # connect on  desktop session started
    fake_drova.session = SessionsResponse(
        sessions=(
            SessionsEntity(
                uuid=SESSION_UUID_FAKE,
                product_id=PRODUCT_UUID_DESKTOP,
                client_id=CLIENT_UUID_FAKE,
                created_on=datetime.now(),
                status=StatusEnum.NEW,
                creator_ip="127.0.0.1",
            ),
        )
    )
    fake_drova.product = ProductInfo(product_id=PRODUCT_UUID_BG3, use_default_desktop=False)

    await drova_poll.one_poll(ssh)
    patcher.on_idle.assert_not_awaited()
    patcher.on_session_start.assert_not_awaited()
    patcher.on_session_active.assert_not_awaited()
    patcher.on_session_end.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_tokens_failure(fake_drova: FakeDrova):
    ssh = AsyncMock()
    sftp = AsyncMock()

    patcher = AsyncMock()
    patcher.on_idle = AsyncMock()
    patcher.on_session_start = AsyncMock()
    patcher.on_session_active = AsyncMock()
    patcher.on_session_end = AsyncMock()

    config = Config(windows_host="127.0.0.1")
    drova_poll = DrovaPoll(config)
    drova_poll.ctx.ssh = ssh
    drova_poll.ctx.sftp = sftp
    drova_poll.drova_service = DrovaService(fake_drova.faked_host)
    drova_poll.drova_transition._patchers = []  # pylint: disable=W0212

    with pytest.raises(RebootRequired):
        result = SSHCompletedProcess(
            returncode=0,
            stdout=r"""
    HKEY_LOCAL_MACHINE\SOFTWARE\ITKey\Esme\servers\85dd80c4-adc1-1111-1111-111111111111
    """,
        )

        ssh.run = AsyncMock(return_value=result)

        await drova_poll.refresh_actual_tokens()

        assert drova_poll.ctx.ssh.run.call_count == 1


@pytest.mark.asyncio
async def test_refresh_tokens(fake_drova: FakeDrova):
    ssh = AsyncMock()
    sftp = AsyncMock()

    patcher = AsyncMock()
    patcher.on_idle = AsyncMock()
    patcher.on_session_start = AsyncMock()
    patcher.on_session_active = AsyncMock()
    patcher.on_session_end = AsyncMock()

    config = Config(windows_host="127.0.0.1")
    drova_poll = DrovaPoll(config)
    drova_poll.ctx.ssh = ssh
    drova_poll.ctx.sftp = sftp
    drova_poll.drova_service = DrovaService(fake_drova.faked_host)
    drova_poll.drova_transition._patchers = []  # pylint: disable=W0212

    result = SSHCompletedProcess(
        returncode=0,
        stdout=r"""
HKEY_LOCAL_MACHINE\SOFTWARE\ITKey\Esme\servers\85dd80c4-adc1-1111-1111-111111111111
auth_token    REG_SZ    7a8b78f4-103d-1111-1111-111111111111
""",
    )

    ssh.run = AsyncMock(return_value=result)

    await drova_poll.refresh_actual_tokens()

    assert drova_poll.ctx.ssh.run.call_count == 1
