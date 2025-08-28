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


async def server_accept(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    target_reader, target_writer = await asyncio.open_connection(os.environ[WINDOWS_HOST], 7985)
    drova_pass = DrovaBinaryProtocol(Socket(reader, writer), Socket(target_reader, target_writer))
    if await drova_pass.wait_server_answered():
        async with connect_ssh(
            host=os.environ[WINDOWS_HOST],
            username=os.environ[WINDOWS_LOGIN],
            password=os.environ[WINDOWS_PASSWORD],
            known_hosts=None,
        ) as conn:
            check_desktop = CheckDesktop(conn)
            is_desktop = await check_desktop.run()
            if is_desktop:
                before_connect = BeforeConnect(conn)
                await before_connect.run()

            logger.info("socket is closing")

            if is_desktop:
                wait_finish_session = WaitFinishOrAbort(conn)
                await wait_finish_session.run()
                after_disconnect_client = AfterDisconnect(conn)
                await after_disconnect_client.run()


async def main():
    basicConfig(level=DEBUG)
    server = await asyncio.start_server(server_accept, "0.0.0.0", os.environ[DROVA_SOCKET_LISTEN], limit=1)

    # addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    # print(f'Serving on {addrs}')

    async with server:
        await server.serve_forever()


def run_async_main():
    asyncio.run(main())


if __name__ == "__main__":
    run_async_main()
