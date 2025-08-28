import asyncio
import os

from asyncssh import connect as connect_ssh

from drova_desktop_keenetic.common.after_disconnect import AfterDisconnect
from drova_desktop_keenetic.common.before_connect import BeforeConnect
from drova_desktop_keenetic.common.contants import (
    WINDOWS_HOST,
    WINDOWS_LOGIN,
    WINDOWS_PASSWORD,
)
from drova_desktop_keenetic.common.helpers import CheckDesktop, WaitFinishOrAbort


async def server_accept(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    target_reader, target_writer = await asyncio.open_connection(os.environ[WINDOWS_HOST], 7985)
    pass1 = asyncio.create_task(passthrough_socket(reader, target_writer))
    pass2 = asyncio.create_task(passthrough_socket(target_reader, writer))

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

        await asyncio.wait([pass1, pass2])
        writer.close()
        target_writer.close()
        await asyncio.gather(writer.wait_closed(), target_writer.wait_closed())

        if is_desktop:
            wait_finish_session = WaitFinishOrAbort(conn)
            await wait_finish_session.run()
            after_disconnect_client = AfterDisconnect(conn)
            await after_disconnect_client.run()


async def passthrough_socket(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    while data := await reader.read():
        writer.write(data)


async def main():
    server = await asyncio.start_server(server_accept, "0.0.0.0", 10)

    # addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    # print(f'Serving on {addrs}')

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
