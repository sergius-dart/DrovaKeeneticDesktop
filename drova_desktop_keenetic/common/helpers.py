import logging
from asyncio import sleep

from asyncssh import SSHClientConnection

from drova_desktop_keenetic.common.commands import RegQueryEsme
from drova_desktop_keenetic.common.drova import (
    UUID_DESKTOP,
    StatusEnum,
    get_latest_session,
)

logger = logging.getLogger(__name__)


class CheckDesktop:
    logger = logger.getChild("CheckDesktop")

    def __init__(self, client: SSHClientConnection):
        self.client = client

    async def run(self) -> bool:
        complete_process = await self.client.run(str(RegQueryEsme()))
        stdout = b""
        if isinstance(complete_process.stdout, str):
            stdout = complete_process.stdout.encode()

        serveri_id, auth_token = RegQueryEsme.parseAuthCode(stdout=stdout)

        self.logger.info(f"Start read latest session with token {auth_token}")
        session = await get_latest_session(serveri_id, auth_token)
        self.logger.debug("Session : ", session)

        if not session:
            return False

        if session.status in (StatusEnum.HANDSHAKE, StatusEnum.ACTIVE, StatusEnum.NEW):
            return session.product_id == UUID_DESKTOP
        # by default, if session not is started (aborted/finished) return false
        return False


class WaitFinishOrAbort:
    logger = logger.getChild("CheckDesktop")

    def __init__(self, client: SSHClientConnection):
        self.client = client

    async def run(self) -> bool:
        complete_process = await self.client.run(str(RegQueryEsme()))
        stdout = b""
        if isinstance(complete_process.stdout, str):
            stdout = complete_process.stdout.encode()
        serveri_id, auth_token = RegQueryEsme.parseAuthCode(stdout=stdout)

        while True:
            session = await get_latest_session(serveri_id, auth_token)
            if not session:
                return False
            # wait close current session
            if session.status in (StatusEnum.ABORTED, StatusEnum.FINISHED):
                return True
            await sleep(1)
