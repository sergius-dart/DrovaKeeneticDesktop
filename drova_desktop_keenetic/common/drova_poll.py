import asyncio
import logging
import os
from logging import DEBUG, basicConfig

from asyncssh import connect as connect_ssh
from asyncssh.misc import ChannelOpenError

from drova_desktop_keenetic.common.after_disconnect import AfterDisconnect
from drova_desktop_keenetic.common.before_connect import BeforeConnect
from drova_desktop_keenetic.common.contants import (
    WINDOWS_HOST,
    WINDOWS_LOGIN,
    WINDOWS_PASSWORD,
)
from drova_desktop_keenetic.common.drova import get_new_session
from drova_desktop_keenetic.common.helpers import (
    CheckDesktop,
    WaitFinishOrAbort,
    WaitNewDesktopSession,
)

logger = logging.getLogger(__name__)


class DrovaPoll:
    def __init__(
        self,
        windows_host: str = os.environ[WINDOWS_HOST],
        windows_login: str = os.environ[WINDOWS_LOGIN],
        windows_password: str = os.environ[WINDOWS_PASSWORD],
    ):
        self.windows_host = windows_host
        self.windows_login = windows_login
        self.windows_password = windows_password

        self.stop_future = asyncio.get_event_loop().create_future()

    async def polling(self) -> None:
        while not self.stop_future.done():
            try:
                async with connect_ssh(
                    host=self.windows_host,
                    username=self.windows_login,
                    password=self.windows_password,
                    known_hosts=None,
                    encoding="windows-1251",
                ) as conn:
                    wait_new_desktop_session = WaitNewDesktopSession(conn)
                    is_desktop_session = await wait_new_desktop_session.run()
                    if is_desktop_session:
                        logger.info("Waited desktop - clear this")
                        before_connect = BeforeConnect(conn)
                        await before_connect.run()
                        logger.info("Wait finish session")
                        wait_finish_session = WaitFinishOrAbort(conn)
                        await wait_finish_session.run()

                        logger.info("Clear shadow defender and restart")
                        after_disconnect_client = AfterDisconnect(conn)
                        await after_disconnect_client.run()
            except (ChannelOpenError, OSError):
                logger.info("Fail connect to windows - gaming or unavailable(reboot)")

            await asyncio.sleep(1)

    async def stop(self) -> None:
        self.stop_future.set_result(True)

    async def _waitif_session_desktop_exists(self) -> None:
        async with connect_ssh(
            host=self.windows_host,
            username=self.windows_login,
            password=self.windows_password,
            known_hosts=None,
            encoding="windows-1251",
        ) as conn:
            check_desktop = CheckDesktop(conn)
            is_desktop = await check_desktop.run()
            if is_desktop:
                logger.info("Wait finish session")
                wait_finish_session = WaitFinishOrAbort(conn)
                await wait_finish_session.run()

                logger.info("Clear shadow defender and restart")
                after_disconnect_client = AfterDisconnect(conn)
                await after_disconnect_client.run()

    async def serve(self, wait_forever=False):
        await self._waitif_session_desktop_exists()

        if wait_forever:
            await self.polling()
        else:
            asyncio.create_task(self.polling())
