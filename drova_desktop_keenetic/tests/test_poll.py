import asyncio
import logging
from logging import DEBUG, basicConfig
from unittest import mock

import pytest
import pytest_asyncio

from drova_desktop_keenetic.common.drova_poll import DrovaPoll
from drova_desktop_keenetic.common.drova_server_binary import BLOCK_SIZE
from drova_desktop_keenetic.common.drova_socket import DrovaSocket

WAIT_NEW_DESKTOP_SESSION_RUN = "drova_desktop_keenetic.common.helpers.WaitNewDesktopSession.run"
WAIT_FINISH_OR_ABORT_RUN = "drova_desktop_keenetic.common.helpers.WaitFinishOrAbort.run"

CHECK_DESKTOP_RUN = "drova_desktop_keenetic.common.helpers.CheckDesktop.run"

BEFORE_CONNECT_RUN = "drova_desktop_keenetic.common.before_connect.BeforeConnect.run"
AFTER_DISCONNECT_RUN = "drova_desktop_keenetic.common.after_disconnect.AfterDisconnect.run"

DROVA_SOCKET_CONNECT_SSH = "drova_desktop_keenetic.common.drova_poll.connect_ssh"

logger = logging.getLogger(__name__)
basicConfig(level=DEBUG)


@pytest.mark.asyncio
async def test_poll_full(mocker):
    @mocker.patch(WAIT_NEW_DESKTOP_SESSION_RUN)
    @mocker.patch(WAIT_FINISH_OR_ABORT_RUN)
    @mocker.patch(BEFORE_CONNECT_RUN)
    @mocker.patch(AFTER_DISCONNECT_RUN)
    @mocker.patch(DROVA_SOCKET_CONNECT_SSH)
    async def _(self) -> bool:
        return True

    @mocker.patch(CHECK_DESKTOP_RUN)
    async def _(self) -> bool:
        return False

    drova_socket = DrovaPoll(windows_host="127.0.0.1")
    await drova_socket.serve()

    await drova_socket.stop()
