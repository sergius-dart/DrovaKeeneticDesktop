import logging
import os
from asyncio import sleep

from asyncssh import SSHClientConnection

from drova_desktop_keenetic.common.commands import ShadowDefenderCLI, TaskKill
from drova_desktop_keenetic.common.contants import (
    SHADOW_DEFENDER_DRIVES,
    SHADOW_DEFENDER_PASSWORD,
)
from drova_desktop_keenetic.common.patch import ALL_PATCHES

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
                await sleep(2)

                for path in ALL_PATCHES:
                    self.logger.info(f"prepare {path.NAME}")
                    if path.TASKKILL_IMAGE:
                        await self.client.run(str(TaskKill(image=path.TASKKILL_IMAGE)))
                    await sleep(0.2)
                    pather = path(self.client, sftp)
                    await pather.patch()

        except Exception:
            logger.exception("We have problem")
        return True
