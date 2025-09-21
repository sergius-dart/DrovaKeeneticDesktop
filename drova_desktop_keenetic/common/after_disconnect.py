import logging
import os
from asyncio import sleep

from asyncssh import SSHClientConnection

from drova_desktop_keenetic.common.commands import ShadowDefenderCLI
from drova_desktop_keenetic.common.contants import (
    SHADOW_DEFENDER_DRIVES,
    SHADOW_DEFENDER_PASSWORD,
)

logger = logging.getLogger(__name__)


class AfterDisconnect:
    logger = logger.getChild("BeforeConnect")

    def __init__(self, client: SSHClientConnection):
        self.client = client

    async def run(self) -> bool:
        self.logger.info("exit from shadow and reboot")
        await sleep(5)
        # exit shadow mode and reboot
        await self.client.run(
            str(
                ShadowDefenderCLI(
                    password=os.environ[SHADOW_DEFENDER_PASSWORD],
                    actions=["exit", "reboot"],
                    drives=os.environ[SHADOW_DEFENDER_DRIVES],
                )
            )
        )

        return True
