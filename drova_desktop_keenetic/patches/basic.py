import logging
from asyncio import create_task, sleep, wait
from configparser import ConfigParser
from pathlib import Path, PureWindowsPath
from typing import Generator

from asyncssh import ChannelOpenError, ProcessError
from pydantic import BaseModel

from drova_desktop_keenetic.common.commands import (
    PsExec,
    RegAdd,
    RegValueType,
    TaskKill,
)
from drova_desktop_keenetic.common.patch import (
    IPatch,
    ISessionHandler,
    SessionHandlerContext,
    patcher,
)

logger = logging.getLogger(__name__)


@patcher
class EpicGamesAuthDiscard(IPatch):
    logger = logger.getChild("EpicGamesAuthDiscard")
    NAME = "epicgames"
    TASKKILL_IMAGE = "EpicGamesLauncher.exe"

    remote_file_location = PureWindowsPath(
        r"AppData\Local\EpicGamesLauncher\Saved\Config\WindowsEditor\GameUserSettings.ini"
    )

    async def _patch(self, file: Path, ctx: SessionHandlerContext) -> None:
        config = ConfigParser(strict=False)
        self.logger.info("read GameUserSettings.ini")
        config.read(file, encoding="UTF-8")

        config.remove_section("RememberMe")
        config.remove_section("Offline")
        self.logger.info("Write without auth section")
        with open(file, "w", encoding="utf8") as f:
            config.write(f)
        for file_dat in await ctx.sftp.glob(self.remote_file_location.parent / "*.dat"):
            self.logger.info("Remove file %s", file_dat)
            await ctx.sftp.remove(file_dat)


@patcher
class SteamAuthDiscard(IPatch):
    logger = logger.getChild("SteamAuthDiscard")
    NAME = "steam"
    TASKKILL_IMAGE = "steam.exe"
    # remote_file_location = PureWindowsPath(r'c:\Program Files (x86)\Steam\config\config.vdf')
    remote_file_location = PureWindowsPath(r"c:\Program Files (x86)\Steam\config\loginusers.vdf")

    async def _patch(self, file: Path, ctx: SessionHandlerContext) -> None:
        with open(file, mode="w", encoding="utf8") as f:
            f.write(
                """"users"
{
}"""
            )


@patcher
class UbisoftAuthDiscard(ISessionHandler):
    logger = logger.getChild("UbisoftAuthDiscard")
    NAME = "ubisoft"
    TASKKILL_IMAGE = "upc.exe"

    to_remove = (
        r"AppData\Local\Ubisoft Game Launcher\ConnectSecureStorage.dat",
        r"AppData\Local\Ubisoft Game Launcher\user.dat",
    )

    async def on_idle(self, ctx):
        return await super().on_idle(ctx)

    async def on_session_start(self, ctx: SessionHandlerContext) -> None:
        if self.TASKKILL_IMAGE:
            await ctx.ssh.run(str(TaskKill(image=self.TASKKILL_IMAGE)))

        for file in self.to_remove:
            if await ctx.sftp.exists(file):
                self.logger.info(f"Remove file {file}")
                await ctx.sftp.remove(PureWindowsPath(file))

    async def on_session_active(self, ctx):
        return await super().on_session_active(ctx)

    async def on_session_end(self, ctx):
        return await super().on_session_end(ctx)


@patcher
class WargamingAuthDiscard(ISessionHandler):
    logger = logger.getChild("WargamingAuthDiscard")
    NAME = "wargaming"
    TASKKILL_IMAGE = "wgc.exe"

    to_remove = (r"AppData\Roaming\Wargaming.net\GameCenter\user_info.xml",)

    async def on_idle(self, ctx):
        return await super().on_idle(ctx)

    async def on_session_start(self, ctx: SessionHandlerContext) -> None:
        if self.TASKKILL_IMAGE:
            await ctx.ssh.run(str(TaskKill(image=self.TASKKILL_IMAGE)))

        for file in self.to_remove:
            if await ctx.sftp.exists(file):
                self.logger.info(f"Remove file {file}")
                await ctx.sftp.remove(PureWindowsPath(file))

    async def on_session_active(self, ctx):
        return await super().on_session_active(ctx)

    async def on_session_end(self, ctx):
        return await super().on_session_end(ctx)


class RegistryPatch(BaseModel):
    reg_directory: str
    value_name: str
    value_type: RegValueType
    value: str | int | bytes


@patcher
class PatchWindowsSettings(ISessionHandler):
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
    disallow_run_path = rf"{explorer_path}\DisallowRun"
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
        for app_index, app in enumerate(self.blocked_applications):
            yield RegistryPatch(
                reg_directory=self.disallow_run_path,
                value_name=f"{app_index}",
                value_type=RegValueType.REG_SZ,
                value=app,
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

    async def _apply_reg_patch(self, ctx: SessionHandlerContext, patch: RegistryPatch) -> None:
        try:
            self.logger.info(f"Run {str(RegAdd(patch.reg_directory))}")
            await ctx.ssh.run(str(RegAdd(patch.reg_directory)), check=True)
            command_patch = RegAdd(
                patch.reg_directory, value_name=patch.value_name, value_type=patch.value_type, value=patch.value
            )
            self.logger.info(f"Run {str(command_patch)}")  # pylint: disable=C0301
            await ctx.ssh.run(
                str(command_patch),
                check=True,
            )
        except ChannelOpenError:
            self.logger.exception(f"Bad settings ssh - don't apply {str(command_patch)}")

        except ProcessError as e:
            self.logger.error(
                f"Command : r{str(command_patch)}:"
                f" return code {e.returncode}. "
                f"stdout: {e.stdout!r}, stderr: {e.stderr!r}"
            )

    async def on_idle(self, ctx):
        return await super().on_idle(ctx)

    async def on_session_start(self, ctx: SessionHandlerContext) -> None:
        tasks = [create_task(self._apply_reg_patch(ctx, patch)) for patch in self._get_patches()]
        await wait(tasks)

        await ctx.ssh.run("gpupdate /target:user /force", check=True)
        await sleep(1)
        await ctx.ssh.run(str(PsExec(command="explorer.exe")), check=False)

    async def on_session_active(self, ctx):
        return await super().on_session_active(ctx)

    async def on_session_end(self, ctx):
        return await super().on_session_end(ctx)
