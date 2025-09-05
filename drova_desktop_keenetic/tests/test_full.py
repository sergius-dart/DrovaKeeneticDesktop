import asyncio
from logging import DEBUG, basicConfig
import logging
import pytest
import pytest_asyncio
from unittest import mock
import asyncssh

from drova_desktop_keenetic.common.after_disconnect import AfterDisconnect
from drova_desktop_keenetic.common.before_connect import BeforeConnect
from drova_desktop_keenetic.common.contants import DROVA_SOCKET_LISTEN
from drova_desktop_keenetic.common.drova_socket import DrovaSocket
from drova_desktop_keenetic.common.helpers import CheckDesktop, WaitFinishOrAbort


logger = logging.getLogger(__name__)
basicConfig(level=DEBUG)


@pytest_asyncio.fixture
async def prepare_server():
    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        logger.info("Fake-server! Read request")
        await reader.read()
        await asyncio.sleep(1)
        logger.info("Write answer")
        writer.write(b"\x01")
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(handler, "127.0.0.1", 7985, limit=1)

    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    logger.info(f"Serving fixture on {addrs}")

    async with server:
        yield await server.start_serving()


@pytest.mark.asyncio
async def test_full(prepare_server):

    @mock.patch.object(CheckDesktop, CheckDesktop.run.__name__)
    @mock.patch.object(WaitFinishOrAbort, WaitFinishOrAbort.run.__name__)
    @mock.patch.object(BeforeConnect, BeforeConnect.run.__name__)
    @mock.patch.object(AfterDisconnect, AfterDisconnect.run.__name__)
    @mock.patch("asyncssh.connect")
    async def checkDesktopRun(self) -> bool:
        return True

    drova_socket = DrovaSocket(7990, windows_host="127.0.0.1")
    await drova_socket.serve()
    logger.info("Drova is served")
    await asyncio.sleep(0.1)
    reader, writer = await asyncio.open_connection(host="127.0.0.1", port=7990)
    await asyncio.sleep(0.1)
    logger.info("Write data!")
    writer.write(b"Hello world!")
    await writer.drain()
    logger.info("Wait data!")
    await reader.read()
    logger.info("Clear!")
    writer.close()
    await writer.wait_closed()

    await drova_socket.stop()
