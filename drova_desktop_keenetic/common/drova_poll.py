import asyncio
import logging
from typing import OrderedDict

from asyncssh import SSHClientConnection
from asyncssh import connect as connect_ssh
from asyncssh.misc import ChannelOpenError
from expiringdict import ExpiringDict  # type: ignore

from drova_desktop_keenetic.common.commands import NotFoundAuthCode, RegQueryEsme
from drova_desktop_keenetic.common.config import Config
from drova_desktop_keenetic.common.context import SessionHandlerContext
from drova_desktop_keenetic.common.drive_protectors import ShadowDefender
from drova_desktop_keenetic.common.drova import (
    PRODUCT_UUID_DESKTOP,
    DrovaService,
    ProductInfo,
    SessionsEntity,
    StatusEnum,
)
from drova_desktop_keenetic.common.drova_session_transition import (
    DrovaSessionTransition,
)
from drova_desktop_keenetic.common.helpers import (
    RebootRequired,
)


class DrovaPoll:
    logger = logging.getLogger(__name__)

    def __init__(self, config: Config = Config()):
        self.stop_future = asyncio.get_event_loop().create_future()

        self.dict_store: OrderedDict[str, str] = ExpiringDict(max_len=100, max_age_seconds=60)
        self._dict_store_lock = asyncio.Lock()

        self.drova_service = DrovaService()
        self.ctx = SessionHandlerContext(config=config, ssh=None, sftp=None)
        self.drova_transition = DrovaSessionTransition(None, ShadowDefender())

    async def get_auth_token(self) -> str:
        async with self._dict_store_lock:
            if "auth_token" not in self.dict_store:
                await self.refresh_actual_tokens()
            return self.dict_store["auth_token"]

    async def get_server_id(self) -> str:
        async with self._dict_store_lock:
            if "server_id" not in self.dict_store:
                await self.refresh_actual_tokens()
            return self.dict_store["server_id"]

    async def refresh_actual_tokens(self) -> tuple[str, str]:
        if not self.ctx.ssh:
            self.logger.error("Bad configuration context")
            raise RebootRequired()

        complete_process = await self.ctx.ssh.run(str(RegQueryEsme()))
        stdout = b""

        if complete_process.exit_status or complete_process.returncode:
            raise RebootRequired()

        try:
            if isinstance(complete_process.stdout, str):
                stdout = complete_process.stdout.encode()
            self.dict_store["server_id"], self.dict_store["auth_token"] = RegQueryEsme.parse_auth_code(stdout=stdout)
        except NotFoundAuthCode as exc:
            raise RebootRequired from exc
        return self.dict_store["server_id"], self.dict_store["auth_token"]

    async def one_poll(self, conn: SSHClientConnection) -> None:
        if self.ctx.ssh != conn:
            self.ctx.sftp = None
        self.ctx.ssh = conn
        if not self.ctx.sftp:
            try:
                self.ctx.sftp = await conn.start_sftp_client()
            except Exception:  # pylint: disable=W0718
                self.logger.exception("Failed to create SFTP client")
                return

        session: SessionsEntity | None = await self.drova_service.get_latest_session(
            await self.get_server_id(), await self.get_auth_token()
        )
        if not session:
            await self.drova_transition.set_status(None, self.ctx)
            return

        product: ProductInfo = await self.drova_service.get_product_info(
            session.product_id, await self.get_auth_token()
        )

        self.ctx.session = session
        self.ctx.product = product

        if product.product_id == PRODUCT_UUID_DESKTOP or product.use_default_desktop:
            await self.drova_transition.set_status(session.status, self.ctx)

    async def polling(self) -> None:
        while not self.stop_future.done():
            try:
                async with connect_ssh(
                    host=self.ctx.config.windows_host,
                    username=self.ctx.config.windows_login,
                    password=self.ctx.config.windows_password,
                    known_hosts=None,
                    encoding="windows-1251",
                    keepalive_interval=30,
                    keepalive_count_max=3,
                    connect_timeout=10,
                ) as conn:
                    try:
                        while not self.stop_future.done():
                            await self.one_poll(conn)
                            await asyncio.sleep(1)
                    except RebootRequired:
                        self.logger.info("Reboot required received!")
                        # simply finished/aborted not start reboot - need active->finished
                        await self.drova_transition.set_status(StatusEnum.ACTIVE, self.ctx)
                        await self.drova_transition.set_status(StatusEnum.ABORTED, self.ctx)
                        await self.drova_transition.set_status(None, self.ctx)
                        # not return because tranition call reboot - and connection is closed automaticly
                        break

            except (ChannelOpenError, OSError):
                self.logger.info("Fail connect to windows - gaming or unavailable(reboot)")
            except Exception:  # pylint: disable=W0718
                self.logger.exception("We have error")

    async def stop(self) -> None:
        self.stop_future.set_result(True)

    async def serve(self, wait_forever: bool = False):
        if wait_forever:
            await self.polling()
        else:
            asyncio.create_task(self.polling())
