from asyncio import FIRST_COMPLETED, Future, StreamReader, StreamWriter, create_task, gather, get_running_loop, wait
from asyncio.exceptions import CancelledError
import logging
from typing import NamedTuple


logger = logging.getLogger(__name__)

BLOCK_SIZE = 4096


class Socket(NamedTuple):
    reader: StreamReader
    writer: StreamWriter


async def simple_passthrought(reader: StreamReader, writer: StreamWriter):
    while True:
        logger.debug("Wait data in simple ( from client to server )")
        if readed_bytes := await reader.read(BLOCK_SIZE):
            logger.debug(f"We readed {hex(readed_bytes)}")
            try:
                writer.write(readed_bytes)
                await writer.drain()
            except (ConnectionResetError, BrokenPipeError, OSError):
                logger.debug("We write to closed socket")
                return
        else:
            writer.close()
            await writer.wait_closed()
            logger.info("Stop reading")
            return


async def server_need_reply(reader: StreamReader, writer: StreamWriter, is_answered: Future):
    found_answer = False
    while True:
        logger.debug("Wait data in need_reply ( from server to client )")
        if readed_bytes := await reader.read(BLOCK_SIZE):
            logger.debug(f"We readed {hex(readed_bytes)}")
            if b"\x01" in readed_bytes and not found_answer:
                found_answer = True
                is_answered.set_result(True)
            try:
                writer.write(readed_bytes)
                await writer.drain()
            except (ConnectionResetError, BrokenPipeError, OSError):
                logger.debug("We write to closed socket")
                return
        else:
            writer.close()
            await writer.wait_closed()
            logger.info("Stop reading")
            return


class DrovaBinaryProtocol:
    def __init__(self, source_socket: Socket, target_socket: Socket):
        self.source_socket = source_socket
        self.target_socket = target_socket

        self.task_passthrought = create_task(simple_passthrought(self.source_socket.reader, self.target_socket.writer))
        self.future_is_answered = get_running_loop().create_future()
        self.task_wait_answer = create_task(
            server_need_reply(self.target_socket.reader, self.source_socket.writer, self.future_is_answered)
        )

    async def wait_server_answered(self) -> bool:
        # if some data sending before call
        if self.future_is_answered.done():
            return True

        try:
            await gather(self.task_passthrought, self.future_is_answered, self.task_wait_answer, return_exceptions=True)
            if self.future_is_answered.done():
                return True
        except CancelledError:
            pass
        return False

    async def clear(self):
        self.source_socket.writer.close()
        self.target_socket.writer.close()
        await self.source_socket.writer.wait_closed()
        await self.target_socket.writer.wait_closed()

        self.task_passthrought.cancel()
        self.task_wait_answer.cancel()
