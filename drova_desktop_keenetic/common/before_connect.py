import logging
import os
from asyncio import sleep

from asyncssh import SSHClientConnection

from drova_desktop_keenetic.common.commands import ShadowDefenderCLI, TaskKill
from drova_desktop_keenetic.common.contants import (
    SHADOW_DEFENDER_DRIVES,
    SHADOW_DEFENDER_PASSWORD,
)
from drova_desktop_keenetic.common.patch import SessionHandlerContext, make_patchers

logger = logging.getLogger(__name__)


class BeforeConnect:
    logger = logger.getChild("BeforeConnect")

    def __init__(self, client: SSHClientConnection):
        self.client = client

    async def run(self) -> bool:
        patchers = make_patchers()

        self.logger.info("open sftp")
        try:
            async with self.client.start_sftp_client() as sftp:
                ctx = SessionHandlerContext(ssh=self.client, sftp=sftp, config=None)
                self.logger.info("start shadow")
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

                for patch in patchers:
                    self.logger.info(f"prepare {patch.NAME}")
                    if patch.TASKKILL_IMAGE:
                        await self.client.run(str(TaskKill(image=patch.TASKKILL_IMAGE)))
                    await sleep(0.2)
                    try:
                        await patch.on_session_start(ctx)
                    except Exception:  # pylint: disable=W0718
                        logger.exception(f"Problem with patch apply - {patch.NAME} skipped!")

        except Exception:  # pylint: disable=W0718
            logger.exception("We have problem")
        return True
