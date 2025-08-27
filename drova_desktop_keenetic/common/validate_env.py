import os
from drova_desktop_keenetic.common.contants import (
    SHADOW_DEFENDER_DRIVES,
    SHADOW_DEFENDER_PASSWORD,
    WINDOWS_HOST,
    WINDOWS_LOGIN,
)


def validate_env():
    assert not hasattr(os.environ, WINDOWS_HOST), "Please set WINDOWS_HOST in .env file"
    assert not hasattr(os.environ, WINDOWS_LOGIN), "Please set WINDOWS_LOGIN in .env file"

    assert not hasattr(os.environ, SHADOW_DEFENDER_PASSWORD), "Please set SHADOW_DEFENDER_PASSWORD in .env file"
    assert not hasattr(os.environ, SHADOW_DEFENDER_DRIVES), "Please set SHADOW_DEFENDER_DRIVES in .env file"


async def validate_creds():
    pass
