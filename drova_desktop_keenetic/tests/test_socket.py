import asyncio
import logging
from logging import DEBUG, basicConfig

import pytest
import pytest_asyncio

from drova_desktop_keenetic.common.drova_server_binary import BLOCK_SIZE
from drova_desktop_keenetic.common.drova_socket import DrovaSocket

CHECK_DESKTOP_RUN = "drova_desktop_keenetic.common.helpers.CheckDesktop.run"
WAIT_FINISH_OR_ABORT_RUN = "drova_desktop_keenetic.common.helpers.WaitFinishOrAbort.run"

BEFORE_CONNECT_RUN = "drova_desktop_keenetic.common.before_connect.BeforeConnect.run"
AFTER_DISCONNECT_RUN = "drova_desktop_keenetic.common.after_disconnect.AfterDisconnect.run"

DROVA_SOCKET_CONNECT_SSH = "drova_desktop_keenetic.common.drova_socket.connect_ssh"

logger = logging.getLogger(__name__)
basicConfig(level=DEBUG)


@pytest_asyncio.fixture
async def prepare_server():
    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        logger.info("Fake-server! Read request")
        await reader.read(BLOCK_SIZE)
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
async def test_socket_full(prepare_server, mocker):

    @mocker.patch(CHECK_DESKTOP_RUN)
    @mocker.patch(WAIT_FINISH_OR_ABORT_RUN)
    @mocker.patch(BEFORE_CONNECT_RUN)
    @mocker.patch(AFTER_DISCONNECT_RUN)
    @mocker.patch(DROVA_SOCKET_CONNECT_SSH)
    async def _(self) -> bool:
        return True

    drova_socket = DrovaSocket(7990, windows_host="127.0.0.1")
    await drova_socket.serve()
    logger.info("Drova is served")
    await asyncio.sleep(0.1)
    reader, writer = await asyncio.open_connection(host="127.0.0.1", port=7990)
    logger.debug("Opened connection : ")
    logger.debug(reader)
    logger.debug(writer)

    await asyncio.sleep(0.1)
    logger.info("Write data!")
    writer.write(b"Hello world!")
    await writer.drain()
    logger.info("Wait data!")
    await reader.read(BLOCK_SIZE)
    logger.info("Clear!")
    writer.close()
    await writer.wait_closed()

    await drova_socket.stop()


@pytest.mark.asyncio
async def test_socket_server_run_as_desktop(prepare_server, mocker):
    @mocker.patch(CHECK_DESKTOP_RUN)
    @mocker.patch(BEFORE_CONNECT_RUN)
    @mocker.patch(AFTER_DISCONNECT_RUN)
    @mocker.patch(DROVA_SOCKET_CONNECT_SSH)
    async def _(self) -> bool:
        return True

    @mocker.patch(WAIT_FINISH_OR_ABORT_RUN)
    async def _(self) -> bool:
        await asyncio.sleep(0.5)
        return True

    drova_socket = DrovaSocket(7990, windows_host="127.0.0.1")
    await drova_socket.serve()

    await drova_socket.stop()
