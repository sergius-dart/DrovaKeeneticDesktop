import asyncio
from logging import DEBUG, basicConfig
import logging
import os

from asyncssh import connect as connect_ssh

from drova_desktop_keenetic.common.after_disconnect import AfterDisconnect
from drova_desktop_keenetic.common.before_connect import BeforeConnect
from drova_desktop_keenetic.common.contants import (
    DROVA_SOCKET_LISTEN,
    WINDOWS_HOST,
    WINDOWS_LOGIN,
    WINDOWS_PASSWORD,
)
from drova_desktop_keenetic.common.drova_server_binary import DrovaBinaryProtocol, Socket
from drova_desktop_keenetic.common.helpers import CheckDesktop, WaitFinishOrAbort


logger = logging.getLogger(__name__)


class DrovaSocket:
    def __init__(
        self,
        drova_socket_listen: int = int(os.environ[DROVA_SOCKET_LISTEN]),
        windows_host: str = os.environ[WINDOWS_HOST],
        windows_login: str = os.environ[WINDOWS_LOGIN],
        windows_password: str = os.environ[WINDOWS_PASSWORD],
    ):
        self.drova_socket_listen = drova_socket_listen
        self.windows_host = windows_host
        self.windows_login = windows_login
        self.windows_password = windows_password

        self.server: asyncio.Server | None = None

    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    async def server_accept(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        logger.debug(f"Accept! to {self.windows_host}:7985")
        logger.debug(reader)
        logger.debug(writer)

        target_socket = await asyncio.open_connection(self.windows_host, 7985)
        drova_pass = DrovaBinaryProtocol(Socket(reader, writer), Socket(*target_socket))
        logger.info("Wait drova windows-server answer")
        if await drova_pass.wait_server_answered():
            logger.info("Server answered - connect and prepare windows host")
            self._run_server_acked()
        else:
            await drova_pass.clear()

    async def _run_server_acked(self):
        async with connect_ssh(
            host=self.windows_host,
            username=self.windows_login,
            password=self.windows_password,
            known_hosts=None,
        ) as conn:
            check_desktop = CheckDesktop(conn)
            is_desktop = await check_desktop.run()
            logger.info("Session is Desktop!")

            if is_desktop:
                logger.info("Start beforeConnect")
                before_connect = BeforeConnect(conn)
                await before_connect.run()

                logger.info("Wait finish session")
                wait_finish_session = WaitFinishOrAbort(conn)
                await wait_finish_session.run()

                logger.info("Clear shadow defender and restart")
                after_disconnect_client = AfterDisconnect(conn)
                await after_disconnect_client.run()

    async def _waitif_session_desktop_exists(self):
        async with connect_ssh(
            host=self.windows_host,
            username=self.windows_login,
            password=self.windows_password,
            known_hosts=None,
        ) as conn:
            check_desktop = CheckDesktop(conn)
            is_desktop = await check_desktop.run()
            if is_desktop:
                logger.info("Wait finish session")
                wait_finish_session = WaitFinishOrAbort(conn)
                await wait_finish_session.run()

                logger.info("Clear shadow defender and restart")
                after_disconnect_client = AfterDisconnect(conn)
                await after_disconnect_client.run()

    async def serve(self, wait_forever=False):
        await self._waitif_session_desktop_exists()

        self.server = await asyncio.start_server(self.server_accept, "0.0.0.0", self.drova_socket_listen, limit=1)

        addrs = ", ".join(str(sock.getsockname()) for sock in self.server.sockets)
        logger.info(f"Serving on {addrs}")

        if not wait_forever:
            await self.server.start_serving()
        else:
            await self.server.serve_forever()
