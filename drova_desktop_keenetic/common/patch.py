import logging
from abc import ABC, abstractmethod
from configparser import ConfigParser
from pathlib import Path, PureWindowsPath

from aiofiles.tempfile import NamedTemporaryFile
from asyncssh import SFTPClient

logger = logging.getLogger(__name__)


class IPatch(ABC):
    remote_file_location: PureWindowsPath

    def __init__(self, sftp: SFTPClient):
        self.sftp = sftp

    @abstractmethod
    async def _patch(self, file: Path): ...

    async def patch(self):
        async with NamedTemporaryFile("ab") as temp_file:
            f = await self.sftp.get(str(self.remote_file_location), temp_file.name):
            self._patch(f, Path(temp_file.name))
            await self.sftp.put(temp_file.name, str(self.remote_file_location))


class EpicGamesAuthDiscard(IPatch):
    logger = logger.getChild("EpicGamesAuthDiscard")

    remote_file_location = PureWindowsPath(r"AppData\Local\EpicGamesLauncher\Saved\Config\Windows\Game.ini")

    async def _patch(self, file: Path):
        config = ConfigParser()
        self.logger.info("read Game.ini")
        config.read_file(str(file), "Game.ini")

        config.remove_section("RememberMe")
        self.logger.info("Write without auth section")
        with open(file, "w") as f:
            config.write(f)


class SteamAuthDiscard(IPatch):
    logger = logger.getChild("SteamAuthDiscard")
    # remote_file_location = PureWindowsPath(r'c:\Program Files (x86)\Steam\config\config.vdf')
    remote_file_location = PureWindowsPath(r"c:\Program Files (x86)\Steam\config\loginusers.vdf")

    async def _patch(self, file: Path):
        with open(file, mode="w") as f:
            f.write(
                """"users"
{
}"""
            )
        # self.logger.info('Read config.vdf')
        # content_config = file.read().decode()

        # r = re.compile(r'(?P<header>"Authentication"\s+{\s+"RememberedMachineID"\s+{)(\s+"\w+"\s+"\S+)+(?P<end>\s+}\s+})')

        # r.sub('\1\3', content_config)
        # self.logger.info('Write without any authentificated')
        # file.write(content_config.encode())
