import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from aiofiles.tempfile import NamedTemporaryFile
from asyncssh import SFTPClient, SSHClientConnection

from drova_desktop_keenetic.common.commands import (
    TaskKill,
)

logger = logging.getLogger(__name__)

_ALL_PATCHES = []


@dataclass
class SessionHandlerContext:
    ssh: SSHClientConnection
    sftp: SFTPClient


class ISessionHandler(ABC):
    @abstractmethod
    async def on_idle(self, ctx: SessionHandlerContext):
        pass

    @abstractmethod
    async def on_session_start(self, ctx: SessionHandlerContext):
        pass

    @abstractmethod
    async def on_session_active(self, ctx: SessionHandlerContext):
        pass

    @abstractmethod
    async def on_session_end(self, ctx: SessionHandlerContext):
        pass


class IPatch(ISessionHandler):
    NAME: str
    TASKKILL_IMAGE: str

    remote_file_location: PureWindowsPath

    @abstractmethod
    async def _patch(self, file: Path, ctx: SessionHandlerContext) -> None: ...

    async def patch(self, ctx: SessionHandlerContext) -> None:
        async with NamedTemporaryFile("ab") as temp_file:
            await temp_file.close()
            await ctx.sftp.get(str(self.remote_file_location), str(temp_file.name))
            await self._patch(Path(str(temp_file.name)), ctx)
            await ctx.sftp.put(str(temp_file.name), str(self.remote_file_location))

    async def on_idle(self, ctx: SessionHandlerContext):
        pass

    async def on_session_start(self, ctx: SessionHandlerContext):
        if self.TASKKILL_IMAGE:
            await ctx.ssh.run(str(TaskKill(image=self.TASKKILL_IMAGE)))
        return await self.patch(ctx)

    async def on_session_active(self, ctx: SessionHandlerContext):
        pass

    async def on_session_end(self, ctx: SessionHandlerContext):
        return None


def patcher(cls: type[ISessionHandler]) -> type[ISessionHandler]:
    if not issubclass(cls, ISessionHandler):
        raise RuntimeError("Please implement basic ISessionHandler/IPatch class")
    _ALL_PATCHES.append(cls)
    return cls


def make_patchers() -> list[ISessionHandler]:
    return [patcher() for patcher in _ALL_PATCHES]
