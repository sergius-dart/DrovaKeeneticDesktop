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
from drova_desktop_keenetic.common.helpers import CheckDesktop, WaitFinishOrAbort


logger = logging.getLogger(__name__)


async def server_accept(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):

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

        target_reader, target_writer = await asyncio.open_connection(os.environ[WINDOWS_HOST], 7985)
        pass1 = asyncio.create_task(passthrough_socket(reader, target_writer))
        pass2 = asyncio.create_task(passthrough_socket(target_reader, writer))
        logger.info("wait socket for close")

        await asyncio.wait([pass1, pass2], return_when=asyncio.FIRST_COMPLETED)
        writer.close()
        target_writer.close()
        await asyncio.gather(writer.wait_closed(), target_writer.wait_closed())

        logger.info("socket is closing")

        if is_desktop:
            wait_finish_session = WaitFinishOrAbort(conn)
            await wait_finish_session.run()
            after_disconnect_client = AfterDisconnect(conn)
            await after_disconnect_client.run()


async def passthrough_socket(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    while data := await reader.read():
        logger.debug(f"readed from socket -> {data}")
        writer.write(data)
        await writer.drain()


async def main():
    basicConfig(level=DEBUG)
    server = await asyncio.start_server(server_accept, "0.0.0.0", os.environ[DROVA_SOCKET_LISTEN])

    # addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    # print(f'Serving on {addrs}')

    async with server:
        await server.serve_forever()


def run_async_main():
    asyncio.run(main())


if __name__ == "__main__":
    run_async_main()
