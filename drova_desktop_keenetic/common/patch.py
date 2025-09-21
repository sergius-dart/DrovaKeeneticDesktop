import logging
from abc import ABC, abstractmethod
from configparser import ConfigParser
from pathlib import Path, PureWindowsPath

from aiofiles.tempfile import NamedTemporaryFile
from asyncssh import SFTPClient

logger = logging.getLogger(__name__)


class IPatch(ABC):
    NAME: str
    TASKKILL_IMAGE: str

    remote_file_location: PureWindowsPath

    def __init__(self, sftp: SFTPClient):
        self.sftp = sftp

    @abstractmethod
    async def _patch(self, file: Path) -> None: ...

    async def patch(self) -> None:
        async with NamedTemporaryFile("ab") as temp_file:
            await temp_file.close()
            await self.sftp.get(str(self.remote_file_location), temp_file.name)
            await self._patch(Path(temp_file.name))
            await self.sftp.put(temp_file.name, str(self.remote_file_location))


class EpicGamesAuthDiscard(IPatch):
    logger = logger.getChild("EpicGamesAuthDiscard")
    NAME = "epicgames"
    TASKKILL_IMAGE = "EpicGamesLauncher.exe"

    remote_file_location = PureWindowsPath(r"AppData\Local\EpicGamesLauncher\Saved\Config\Windows\GameUserSettings.ini")

    async def _patch(self, file: Path) -> None:
        config = ConfigParser(strict=False)
        self.logger.info("read GameUserSettings.ini")
        config.read(file, encoding="UTF-8")

        config.remove_section("RememberMe")
        config.remove_section("Offline")
        self.logger.info("Write without auth section")
        with open(file, "w") as f:
            config.write(f)


class SteamAuthDiscard(IPatch):
    logger = logger.getChild("SteamAuthDiscard")
    NAME = "steam"
    TASKKILL_IMAGE = "steam.exe"
    # remote_file_location = PureWindowsPath(r'c:\Program Files (x86)\Steam\config\config.vdf')
    remote_file_location = PureWindowsPath(r"c:\Program Files (x86)\Steam\config\loginusers.vdf")

    async def _patch(self, file: Path) -> None:
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


class UbisoftAuthDiscard(IPatch):
    logger = logger.getChild("UbisoftAuthDiscard")
    NAME = "ubisoft"
    TASKKILL_IMAGE = "upc.exe"

    to_remove = (
        r"AppData\Local\Ubisoft Game Launcher\ConnectSecureStorage.dat",
        r"AppData\Local\Ubisoft Game Launcher\user.dat",
    )

    def _patch(self, _: Path) -> None:
        return None

    async def patch(self) -> None:
        for file in self.to_remove:
            if await self.sftp.exists(file):
                self.logger.info(f"Remove file {file}")
                await self.sftp.remove(PureWindowsPath(file))


class WargamingAuthDiscard(IPatch):
    logger = logger.getChild("WargamingAuthDiscard")
    NAME = "wargaming"
    TASKKILL_IMAGE = "wgc.exe"

    to_remove = (r"AppData\Roaming\Wargaming.net\GameCenter\user_info.xml",)

    def _patch(self, _: Path) -> None:
        return None

    async def patch(self) -> None:
        for file in self.to_remove:
            if await self.sftp.exists(file):
                self.logger.info(f"Remove file {file}")
                await self.sftp.remove(PureWindowsPath(file))


ALL_PATCHES = (EpicGamesAuthDiscard, SteamAuthDiscard, UbisoftAuthDiscard, WargamingAuthDiscard)
