from asyncio import FIRST_COMPLETED, Future, StreamReader, StreamWriter, create_task, get_running_loop, wait
from typing import NamedTuple


class Socket(NamedTuple):
    reader: StreamReader
    writer: StreamWriter


async def simple_passthrought(reader: StreamReader, writer: StreamWriter):
    task_read = create_task(reader.read())
    task_closed = create_task(writer.wait_closed())
    while await wait((task_read, task_closed), return_when=FIRST_COMPLETED):
        if task_read.done():
            writer.write(task_read.result())
            await writer.drain()
        if task_closed.done():
            return


async def server_need_reply(reader: StreamReader, writer: StreamWriter, is_answered: Future):
    task_read = create_task(reader.read())
    task_closed = create_task(writer.wait_closed())
    found_answer = False
    while await wait((task_read, task_closed), return_when=FIRST_COMPLETED):
        if task_read.done():
            readed_bytes = task_read.result()
            if b"\x01" in readed_bytes and not found_answer:
                found_answer = True
                is_answered.set_result(True)
            writer.write(readed_bytes)
            await writer.drain()
        if task_closed.done():
            return


class DrovaBinaryProtocol:
    def __init__(self, source_socket: Socket, target_socket: Socket):
        self.source_socket = source_socket
        self.target_socket = target_socket

    async def wait_server_answered(self) -> bool:
        task_passthrought = create_task(simple_passthrought(self.source_socket.reader, self.target_socket.writer))
        future_is_answered = get_running_loop().create_future()
        task_wait_answer = create_task(
            server_need_reply(self.target_socket.reader, self.source_socket.writer, future_is_answered)
        )

        await wait((task_passthrought, future_is_answered, task_wait_answer), return_when=FIRST_COMPLETED)
        if future_is_answered.done():
            return True
        return False
