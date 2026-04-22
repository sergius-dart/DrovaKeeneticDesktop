import logging
from datetime import datetime
from enum import StrEnum
from ipaddress import IPv4Address
from pathlib import PureWindowsPath
from uuid import UUID

import aiohttp
from aiohttp import web
from pydantic import UUID4, BaseModel, ConfigDict

SESSION_UUID_FAKE = UUID("e099d33f-51f3-4129-a3a6-b75d75885b45")
CLIENT_UUID_FAKE = UUID("fefca70b-0af8-463d-82bb-724edc1da927")
PRODUCT_UUID_DESKTOP = UUID("9fd0eb43-b2bb-4ce3-93b8-9df63f209098")
PRODUCT_UUID_BG3 = UUID("c8e78ede-6d9c-4a62-9897-87c735baa76b")


class StatusEnum(StrEnum):
    NEW = "NEW"
    HANDSHAKE = "HANDSHAKE"
    ACTIVE = "ACTIVE"

    ABORTED = "ABORTED"
    FINISHED = "FINISHED"


class SessionsEntity(BaseModel):
    uuid: UUID
    product_id: UUID
    client_id: UUID
    created_on: datetime
    finished_on: datetime | None = None
    status: StatusEnum
    creator_ip: IPv4Address
    abort_comment: str | None = None
    score: int | None = None
    score_reason: int | None = None
    score_text: str | None = None
    billing_type: str | None = None


class SessionsResponse(BaseModel):
    sessions: list[SessionsEntity] | None


class ProductInfo(BaseModel):
    model_config = ConfigDict(extra="allow")
    product_id: UUID
    game_path: PureWindowsPath = PureWindowsPath("C:/")
    work_path: PureWindowsPath = PureWindowsPath("C:/")
    args: str = ""
    use_default_desktop: bool = False
    title: str = "Test"


class DrovaService:
    logger = logging.getLogger(__file__)
    URL_SESSIONS = "{host}/session-manager/sessions?"
    URL_PRODUCT = "{host}/server-manager/product/get/{product_id}"

    def __init__(self, host: str = "https://services.drova.io"):
        self._host: str = host

    async def get_latest_session(self, server_id: str, auth_token: str) -> SessionsEntity | None:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                self.URL_SESSIONS.format(host=self._host),
                data={"server_id": server_id},
                headers={"X-Auth-Token": auth_token},
            ) as resp:
                sessions = SessionsResponse(**await resp.json())
                if not sessions.sessions:
                    return None
                return sessions.sessions[0]

    async def get_new_session(self, server_id: str, auth_token: str) -> SessionsEntity | None:
        query_params = f"state={StatusEnum.NEW.value}&state={StatusEnum.HANDSHAKE.value}"
        async with aiohttp.ClientSession() as session:
            async with session.get(
                self.URL_SESSIONS.format(host=self._host) + query_params,
                data={"server_id": server_id},
                headers={"X-Auth-Token": auth_token},
            ) as resp:
                sessions = SessionsResponse(**await resp.json())
                if not sessions.sessions:
                    return None
                return sessions.sessions[0]

    async def get_product_info(self, product_id: UUID4, auth_token: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                self.URL_PRODUCT.format(host=self._host, product_id=product_id), headers={"X-Auth-Token": auth_token}
            ) as resp:
                product_info = ProductInfo(**await resp.json())
                return product_info


class FakeDrova:
    def __init__(self):
        app = web.Application()
        app.router.add_get("/session-manager/sessions", self._get_session)
        app.router.add_get("/server-manager/product/get/{product_id}", self._get_product)

        self.app = app
        self._port = 8000
        self._host = "127.0.0.1"

        self._runner: web.AppRunner | None = None
        self._site: web.BaseSite | None = None

        self.session = SessionsResponse(
            sessions=(
                SessionsEntity(
                    uuid=SESSION_UUID_FAKE,
                    product_id=PRODUCT_UUID_BG3,
                    client_id=CLIENT_UUID_FAKE,
                    created_on=datetime.now(),
                    status=StatusEnum.NEW,
                    creator_ip="127.0.0.1",
                ),
            )
        )
        self.product = ProductInfo(product_id=PRODUCT_UUID_BG3)

    @property
    def faked_host(self):
        return f"http://{self._host}:{self._port}"

    async def start(self):
        self._runner = web.AppRunner(self.app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self._host, self._port)
        await self._site.start()

    async def close(self):
        await self._runner.cleanup()
        self._site = None
        self._runner = None

    async def _get_session(self, _: web.Request):
        if self.session:
            return web.json_response(self.session.model_dump(mode="json"))

        return web.json_response({"sessions": []})

    async def _get_product(self, _: web.Request):
        return web.json_response(self.product.model_dump(mode="json"))
