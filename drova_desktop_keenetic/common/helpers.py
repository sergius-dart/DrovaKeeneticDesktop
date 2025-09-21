import logging
from asyncio import sleep

from asyncssh import SSHClientConnection

from drova_desktop_keenetic.common.commands import RegQueryEsme
from drova_desktop_keenetic.common.drova import (
    UUID_DESKTOP,
    SessionsEntity,
    StatusEnum,
    get_latest_session,
    get_product_info,
)

logger = logging.getLogger(__name__)


class BaseDrovaMerchantWindows:
    logger = logger.getChild("BaseDrovaMerchantWindows")

    def __init__(self, client: SSHClientConnection):
        self.client = client
        self.auth_token: str | None = None
        self.server_id: str | None = None

    async def get_actual_tokens(self) -> tuple[str, str]:
        complete_process = await self.client.run(str(RegQueryEsme()))
        stdout = b""
        if isinstance(complete_process.stdout, str):
            stdout = complete_process.stdout.encode()

        self.server_id, self.auth_token = RegQueryEsme.parseAuthCode(stdout=stdout)
        return self.server_id, self.auth_token

    async def check_desktop_session(self, session: SessionsEntity) -> bool:
        _, auth_token = await self.get_actual_tokens()
        self.logger.info(f"Check session product_id =  {session.product_id}")
        if session.product_id == UUID_DESKTOP:
            return True
        # check alloed only on desktop
        product_info = await get_product_info(session.product_id, auth_token=auth_token)
        self.logger.info(f"product_info : {product_info}")
        return product_info.use_default_desktop


class CheckDesktop(BaseDrovaMerchantWindows):
    logger = logger.getChild("CheckDesktop")

    async def run(self) -> bool:
        await self.get_actual_tokens()

        self.logger.info(f"Start read latest session with token {self.auth_token}")
        session = await get_latest_session(self.server_id, self.auth_token)
        self.logger.debug(f"Session : {session}")

        if not session:
            return False

        if session.status in (StatusEnum.HANDSHAKE, StatusEnum.ACTIVE, StatusEnum.NEW):
            return await self.check_desktop_session(session)
        # by default, if session not is started (aborted/finished) return false
        return False


class WaitFinishOrAbort(BaseDrovaMerchantWindows):
    logger = logger.getChild("CheckDesktop")

    async def run(self) -> bool:
        while True:
            complete_process = await self.client.run(str(RegQueryEsme()))
            stdout = b""
            if isinstance(complete_process.stdout, str):
                stdout = complete_process.stdout.encode()
            serveri_id, auth_token = RegQueryEsme.parseAuthCode(stdout=stdout)

            session = await get_latest_session(serveri_id, auth_token)
            if not session:
                return False
            # wait close current session
            if session.status in (StatusEnum.ABORTED, StatusEnum.FINISHED):
                return True
            await sleep(1)


class WaitNewDesktopSession(BaseDrovaMerchantWindows):
    logger = logger.getChild("WaitNewSession")

    async def run(self) -> bool:
        while True:
            complete_process = await self.client.run(str(RegQueryEsme()))
            stdout = b""
            if isinstance(complete_process.stdout, str):
                stdout = complete_process.stdout.encode()
            serveri_id, auth_token = RegQueryEsme.parseAuthCode(stdout=stdout)

            session = await get_latest_session(serveri_id, auth_token)
            if not session:
                return False

            if session.status in (StatusEnum.HANDSHAKE, StatusEnum.NEW):
                return await self.check_desktop_session(session)
