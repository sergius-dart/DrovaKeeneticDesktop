import logging
from abc import ABC, abstractmethod
from pathlib import Path, PureWindowsPath
from typing import Any

from aiofiles.tempfile import NamedTemporaryFile
from asyncssh import SFTPNoSuchFile

from drova_desktop_keenetic.common.commands import (
    TaskKill,
)
from drova_desktop_keenetic.common.config import Config
from drova_desktop_keenetic.common.context import SessionHandlerContext

logger = logging.getLogger(__name__)


class ISessionHandler(ABC):
    def __init__(self, config: Config):  # pylint: disable=W0613
        return

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
        assert ctx.ssh
        assert ctx.sftp
        async with NamedTemporaryFile("ab") as temp_file:
            await temp_file.close()
            await ctx.sftp.get(str(self.remote_file_location), str(temp_file.name))
            await self._patch(Path(str(temp_file.name)), ctx)
            await ctx.sftp.put(str(temp_file.name), str(self.remote_file_location))

    async def on_idle(self, ctx: SessionHandlerContext):
        pass

    async def on_session_start(self, ctx: SessionHandlerContext):
        assert ctx.ssh
        if self.TASKKILL_IMAGE:
            await ctx.ssh.run(str(TaskKill(image=self.TASKKILL_IMAGE)))
        try:
            return await self.patch(ctx)
        except SFTPNoSuchFile:
            logger.warning(f"Not found file to patch {self.NAME}: {self.remote_file_location}")
        except Exception:  # pylint: disable=W0718
            logger.exception(f"Error on apply patcher {self.NAME}")

    async def on_session_active(self, ctx: SessionHandlerContext):
        pass

    async def on_session_end(self, ctx: SessionHandlerContext):
        return None


def patcher(cls: Any) -> type[ISessionHandler]:
    if not issubclass(cls, ISessionHandler):
        raise RuntimeError("Please implement basic ISessionHandler/IPatch class")
    _ALL_PATCHES.append(cls)
    return cls


def make_patchers(config: Config) -> list[ISessionHandler]:
    return [patcher(config=config) for patcher in _ALL_PATCHES]


_ALL_PATCHES: list[type[ISessionHandler]] = []
