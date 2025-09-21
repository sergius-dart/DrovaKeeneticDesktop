from datetime import datetime
from enum import StrEnum
from ipaddress import IPv4Address
from pathlib import PureWindowsPath
from urllib.parse import urlencode, urlparse, urlunparse
from uuid import UUID

import aiohttp
from pydantic import BaseModel, ConfigDict

URL_SESSIONS = "https://services.drova.io/session-manager/sessions?"
URL_PRODUCT = "https://services.drova.io/server-manager/product/get/{product_id}"
UUID_DESKTOP = UUID("9fd0eb43-b2bb-4ce3-93b8-9df63f209098")


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
    sessions: list[SessionsEntity]


class ProductInfo(BaseModel):
    model_config = ConfigDict(extra="allow")  # todo add full
    product_id: UUID
    game_path: PureWindowsPath
    work_path: PureWindowsPath
    args: str
    use_default_desktop: bool
    title: str


async def get_latest_session(server_id: str, auth_token: str) -> SessionsEntity | None:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            URL_SESSIONS, data={"serveri_id": server_id}, headers={"X-Auth-Token": auth_token}
        ) as resp:
            sessions = SessionsResponse(**await resp.json())
            if not sessions.sessions:
                return None
            return sessions.sessions[0]


async def get_new_session(server_id: str, auth_token: str) -> SessionsEntity | None:
    query_params = f"state={StatusEnum.NEW.value}&state={StatusEnum.HANDSHAKE.value}"
    async with aiohttp.ClientSession() as session:
        async with session.get(
            URL_SESSIONS + query_params, data={"serveri_id": server_id}, headers={"X-Auth-Token": auth_token}
        ) as resp:
            sessions = SessionsResponse(**await resp.json())
            if not sessions.sessions:
                return None
            return sessions.sessions[0]


async def get_product_info(product_id: UUID, auth_token: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(URL_PRODUCT.format(product_id=product_id), headers={"X-Auth-Token": auth_token}) as resp:
            product_info = ProductInfo(**await resp.json())
            return product_info
