import logging
from abc import ABC, abstractmethod
from asyncio import sleep, wait
from configparser import ConfigParser
from pathlib import Path, PureWindowsPath
from typing import Generator

from aiofiles.tempfile import NamedTemporaryFile
from asyncssh import SFTPClient, SSHClientConnection
from pydantic import BaseModel
from asyncio import create_task

from drova_desktop_keenetic.common.commands import (
    PsExec,
    RegAdd,
    RegValueType,
)

logger = logging.getLogger(__name__)


class IPatch(ABC):
    NAME: str
    TASKKILL_IMAGE: str

    remote_file_location: PureWindowsPath

    def __init__(self, client: SSHClientConnection, sftp: SFTPClient):
        self.client = client
        self.sftp = sftp

    @abstractmethod
    async def _patch(self, file: Path) -> None: ...

    async def patch(self) -> None:
        async with NamedTemporaryFile("ab") as temp_file:
            await temp_file.close()
            await self.sftp.get(str(self.remote_file_location), str(temp_file.name))
            await self._patch(Path(str(temp_file.name)))
            await self.sftp.put(str(temp_file.name), str(self.remote_file_location))


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

    async def _patch(self, _: Path) -> None:
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

    async def _patch(self, _: Path) -> None:
        return None

    async def patch(self) -> None:
        for file in self.to_remove:
            if await self.sftp.exists(file):
                self.logger.info(f"Remove file {file}")
                await self.sftp.remove(PureWindowsPath(file))


class RegistryPatch(BaseModel):
    reg_directory: str
    value_name: str
    value_type: RegValueType
    value: str | int | bytes


class PatchWindowsSettings(IPatch):
    logger = logger.getChild("PatchWindowsSettings")
    NAME = "RegistryPatch"
    TASKKILL_IMAGE = "explorer.exe"

    disable_cmd = RegistryPatch(
        reg_directory=r"HKCU\Software\Policies\Microsoft\Windows\System",
        value_name="DisableCMD",
        value_type=RegValueType.REG_DWORD,
        value=2,
    )
    disable_task_mgr = RegistryPatch(
        reg_directory=r"HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System",
        value_name="DisableTaskMgr",
        value_type=RegValueType.REG_DWORD,
        value=1,
    )
    disable_vbscript = RegistryPatch(
        reg_directory=r"HKCU\Software\Policies\Microsoft\Windows Script Host",
        value_name="Enabled",
        value_type=RegValueType.REG_DWORD,
        value=0,
    )

    explorer_path = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer"
    disable_poweroff = RegistryPatch(
        reg_directory=explorer_path, value_name="NoClose", value_type=RegValueType.REG_DWORD, value=1
    )
    disable_logoff = RegistryPatch(
        reg_directory=explorer_path, value_name="StartMenuLogoff", value_type=RegValueType.REG_DWORD, value=1
    )
    disable_poweroff_login = RegistryPatch(
        reg_directory=explorer_path, value_name="ShutdownWithoutLogon", value_type=RegValueType.REG_DWORD, value=0
    )
    disable_logout = RegistryPatch(
        reg_directory=explorer_path, value_name="NoLogoff", value_type=RegValueType.REG_DWORD, value=0
    )

    disable_gpedit = RegistryPatch(
        reg_directory=r"HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System",
        value_name="DisableGpedit",
        value_type=RegValueType.REG_DWORD,
        value=1,
    )
    disable_fast_user_switch = RegistryPatch(
        reg_directory=r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System",
        value_name="HideFastUserSwitching",
        value_type=RegValueType.REG_DWORD,
        value=1,
    )
    disable_mmc = RegistryPatch(
        reg_directory=r"HKCU\Software\Policies\Microsoft\MMC",
        value_name="RestrictToPermittedSnapins",
        value_type=RegValueType.REG_DWORD,
        value=1,
    )

    disable_run_app = RegistryPatch(
        reg_directory=explorer_path,
        value_name="DisallowRun",
        value_type=RegValueType.REG_DWORD,
        value=1,
    )
    blocked_applications = (
        "regedit.exe",
        "powershell.exe",
        "powershell_ise.exe",
        "mmc.exe",
        "gpedit.msc",
        "perfmon.exe",
        "anydesk.exe",
        "rustdesk.exe",
        "ProcessHacker.exe",
        "procexp.exe",
        "autoruns.exe",
        "psexplorer.exe",
        "procexp.exe",
        "procexp64.exe",
        "procexp64a.exe",
        "soundpad.exe",
        "SoundpadService.exe",
    )

    def disable_application(self) -> Generator[RegistryPatch, None, None]:
        for app_index in range(len(self.blocked_applications)):
            app = self.blocked_applications[app_index]
            yield RegistryPatch(
                reg_directory=self.explorer_path, value_name=f"{app_index}", value_type=RegValueType.REG_SZ, value=app
            )

    def _get_patches(self):
        return (
            self.disable_cmd,
            self.disable_task_mgr,
            self.disable_vbscript,
            self.disable_poweroff,
            self.disable_logoff,
            self.disable_poweroff_login,
            self.disable_logout,
            self.disable_gpedit,
            self.disable_fast_user_switch,
            self.disable_mmc,
            self.disable_run_app,
            *self.disable_application(),
        )

    async def _apply_reg_patch(self, patch: RegistryPatch) -> None:
        self.logger.info(f"Run {str(RegAdd(patch.reg_directory))}")
        await self.client.run(str(RegAdd(patch.reg_directory)), check=True)
        self.logger.info(
            f"Run {str(RegAdd(patch.reg_directory, value_name=patch.value_name, value_type=patch.value_type, value=patch.value))}"
        )
        await self.client.run(
            str(
                RegAdd(patch.reg_directory, value_name=patch.value_name, value_type=patch.value_type, value=patch.value)
            ),
            check=True,
        )
        return None

    async def _patch(self, _: Path) -> None:
        return None

    async def patch(self) -> None:
        tasks = (create_task(self._apply_reg_patch(patch)) for patch in self._get_patches())
        await wait(tasks)

        await self.client.run("gpupdate /target:user /force", check=True)
        await sleep(1)
        await self.client.run(str(PsExec(command="explorer.exe")), check=False)


ALL_PATCHES = (EpicGamesAuthDiscard, SteamAuthDiscard, UbisoftAuthDiscard, WargamingAuthDiscard, PatchWindowsSettings)
