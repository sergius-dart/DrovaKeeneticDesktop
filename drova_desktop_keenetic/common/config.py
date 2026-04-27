import os
from dataclasses import dataclass


@dataclass
class Config:
    windows_host: str = os.getenv("WINDOWS_HOST", "localhost")
    windows_login: str = os.getenv("WINDOWS_LOGIN", "Administrator")
    windows_password: str = os.getenv("WINDOWS_PASSWORD", "VeryStrongPasword")

    shadow_defender_password: str = os.getenv("SHADOW_DEFENDER_PASSWORD", "VeryStrongPassword")
