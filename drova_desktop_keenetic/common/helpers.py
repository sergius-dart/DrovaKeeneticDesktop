import logging
from asyncio import sleep

from async_property import async_property
from asyncssh import SSHClientConnection
from expiringdict import ExpiringDict

from drova_desktop_keenetic.common.commands import NotFoundAuthCode, RegQueryEsme
from drova_desktop_keenetic.common.drova import (
    UUID_DESKTOP,
    SessionsEntity,
    StatusEnum,
    get_latest_session,
    get_product_info,
)

logger = logging.getLogger(__name__)


class RebootRequired(RuntimeError): ...


class BaseDrovaMerchantWindows:
    logger = logger.getChild("BaseDrovaMerchantWindows")

    def __init__(self, client: SSHClientConnection):
        self.client = client
        self.dict_store = ExpiringDict(max_len=100, max_age_seconds=60)

    @async_property
    async def auth_token(self):
        if "auth_token" not in self.dict_store:
            await self.refresh_actual_tokens()
        return self.dict_store["auth_token"]

    @async_property
    async def server_id(self):
        if "server_id" not in self.dict_store:
            await self.refresh_actual_tokens()
        return self.dict_store["server_id"]

    async def refresh_actual_tokens(self) -> tuple[str, str]:
        complete_process = await self.client.run(str(RegQueryEsme()))
        stdout = b""

        if complete_process.exit_status or complete_process.returncode:
            raise RebootRequired()

        try:
            if isinstance(complete_process.stdout, str):
                stdout = complete_process.stdout.encode()
            self.dict_store["server_id"], self.dict_store["auth_token"] = RegQueryEsme.parseAuthCode(stdout=stdout)
        except NotFoundAuthCode:
            raise RebootRequired
        return self.dict_store["server_id"], self.dict_store["auth_token"]

    async def check_desktop_session(self, session: SessionsEntity) -> bool:
        self.logger.info(f"Check session product_id =  {session.product_id}")
        if session.product_id == UUID_DESKTOP:
            return True
        # check alloed only on desktop
        product_info = await get_product_info(session.product_id, auth_token=await self.auth_token)
        self.logger.info(f"product_info : {product_info}")
        return product_info.use_default_desktop


class CheckDesktop(BaseDrovaMerchantWindows):
    logger = logger.getChild("CheckDesktop")

    async def run(self) -> bool:

        self.logger.info(f"Start read latest session with token {await self.auth_token}")
        session = await get_latest_session(await self.server_id, await self.auth_token)
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

            session = await get_latest_session(await self.server_id, await self.auth_token)
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

            session = await get_latest_session(await self.server_id, await self.auth_token)
            if not session:
                return False

            if session.status in (StatusEnum.HANDSHAKE, StatusEnum.NEW):
                return await self.check_desktop_session(session)
