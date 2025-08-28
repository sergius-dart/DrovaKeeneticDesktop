from datetime import datetime
from enum import StrEnum
from ipaddress import IPv4Address
from uuid import UUID

from pydantic import BaseModel

URL_SESSIONS = "https://services.drova.io/session-manager/sessions"
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


async def get_latest_session(serveri_id: str, auth_token: str) -> SessionsEntity | None:
    pass
