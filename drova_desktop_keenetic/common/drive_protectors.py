import logging
from enum import Enum

from drova_desktop_keenetic.common.commands import (
    ShadowDefenderCLI,
    Shutdown,
    WmicGetLocalDrives,
)
from drova_desktop_keenetic.common.patch import ISessionHandler, SessionHandlerContext


class ShadowDefender(ISessionHandler):
    logger = logging.getLogger(__file__)

    async def on_idle(self, ctx: SessionHandlerContext):
        return None

    async def on_session_start(self, ctx: SessionHandlerContext):
        assert ctx.ssh
        detect_drives = WmicGetLocalDrives()
        drives_result = await ctx.ssh.run(str(detect_drives))
        drives = "C"
        if drives_result.returncode != 0:
            self.logger.error("Error on drive getter - using ONLY C")
        else:
            drives = "".join(WmicGetLocalDrives.parse(drives_result.stdout))  # pyright: ignore[reportArgumentType]

        cmd_protect = ShadowDefenderCLI(password=ctx.config.shadow_defender_password, actions=["enter"], drives=drives)

        await ctx.ssh.run(str(cmd_protect))

        # exit from shadow on next boot
        cmd_unlock_not_now = ShadowDefenderCLI(
            password=ctx.config.shadow_defender_password, actions=["exit"], drives=drives, now=False
        )
        await ctx.ssh.run(str(cmd_unlock_not_now))

    async def on_session_active(self, ctx: SessionHandlerContext):
        return None

    async def on_session_end(self, ctx: SessionHandlerContext):
        assert ctx.ssh
        await ctx.ssh.run(str(Shutdown(actions="reboot")))


class PatcherTypeEnum(Enum):
    SHADOW_DEFENDER = ShadowDefender
