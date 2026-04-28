import os
from dataclasses import dataclass

from drova_desktop_keenetic.common.constants import (
    DROVA_SERVICE_HOST,
    OBS_REMOTE_URL,
    SHADOW_DEFENDER_PASSWORD,
    WINDOWS_HOST,
    WINDOWS_LOGIN,
    WINDOWS_PASSWORD,
)


@dataclass
class Config:
    windows_host: str = os.getenv(WINDOWS_HOST, "localhost")
    windows_login: str = os.getenv(WINDOWS_LOGIN, "Administrator")
    windows_password: str = os.getenv(WINDOWS_PASSWORD, "VeryStrongPasword")

    shadow_defender_password: str = os.getenv(SHADOW_DEFENDER_PASSWORD, "VeryStrongPassword")

    obs_remote_url: str | None = os.getenv(OBS_REMOTE_URL)

    drova_service_host: str = os.getenv(DROVA_SERVICE_HOST, "https://services.drova.io")
