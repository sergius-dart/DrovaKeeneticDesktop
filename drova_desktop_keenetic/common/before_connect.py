import logging
import os
from asyncio import sleep

from asyncssh import SSHClientConnection

from drova_desktop_keenetic.common.commands import ShadowDefenderCLI, TaskKill
from drova_desktop_keenetic.common.contants import (
    SHADOW_DEFENDER_DRIVES,
    SHADOW_DEFENDER_PASSWORD,
)
from drova_desktop_keenetic.common.patch import EpicGamesAuthDiscard, SteamAuthDiscard

logger = logging.getLogger(__name__)


class BeforeConnect:
    logger = logger.getChild("BeforeConnect")

    def __init__(self, client: SSHClientConnection):
        self.client = client

    async def run(self) -> bool:

        self.logger.info("open sftp")
        try:
            async with self.client.start_sftp_client() as sftp:

                self.logger.info(f"start shadow")
                # start shadow mode
                await self.client.run(
                    str(
                        ShadowDefenderCLI(
                            password=os.environ[SHADOW_DEFENDER_PASSWORD],
                            actions=["enter"],
                            drives=os.environ[SHADOW_DEFENDER_DRIVES],
                        )
                    )
                )
                await sleep(0.4)

                self.logger.info(f"prepare steam")
                # prepare steam
                await self.client.run(str(TaskKill(image="steam.exe")))
                await sleep(0.1)
                steam = SteamAuthDiscard(sftp)
                await steam.patch()
                # client.run(str(PsExec(command=Steam()))) # todo autorestart steam launcher

                self.logger.info("prepare epic")
                # prepare epic
                await self.client.run(str(TaskKill(image="EpicGamesLauncher.exe")))
                await sleep(0.1)
                epic = EpicGamesAuthDiscard(sftp)
                await epic.patch()
                # client.run(str(PsExec(command=EpicGamesLauncher()))) # todo autorestart epic launcher
        except Exception:
            logger.exception("We have problem")
        return True
