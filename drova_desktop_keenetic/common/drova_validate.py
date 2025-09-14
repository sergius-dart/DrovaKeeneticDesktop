import os

from aiofiles.tempfile import NamedTemporaryFile
from asyncssh import SSHClientConnectionOptions
from asyncssh import connect as connect_ssh

from drova_desktop_keenetic.common.commands import ShadowDefenderCLI
from drova_desktop_keenetic.common.contants import (
    DROVA_SOCKET_LISTEN,
    SHADOW_DEFENDER_DRIVES,
    SHADOW_DEFENDER_PASSWORD,
    WINDOWS_HOST,
    WINDOWS_LOGIN,
    WINDOWS_PASSWORD,
)


def validate_env():
    assert not hasattr(os.environ, DROVA_SOCKET_LISTEN), "Please set DROVA_SOCKET_LISTEN in .env file"
    assert not hasattr(os.environ, WINDOWS_HOST), "Please set WINDOWS_HOST in .env file"
    assert not hasattr(os.environ, WINDOWS_LOGIN), "Please set WINDOWS_LOGIN in .env file"

    assert not hasattr(os.environ, SHADOW_DEFENDER_PASSWORD), "Please set SHADOW_DEFENDER_PASSWORD in .env file"
    assert not hasattr(os.environ, SHADOW_DEFENDER_DRIVES), "Please set SHADOW_DEFENDER_DRIVES in .env file"


async def validate_creds():
    async with connect_ssh(
        host=os.environ[WINDOWS_HOST],
        username=os.environ[WINDOWS_LOGIN],
        password=os.environ[WINDOWS_PASSWORD],
        known_hosts=None,
    ) as conn:
        print("Windows access complete!")
        result_defender = await conn.run(str(ShadowDefenderCLI(os.environ[SHADOW_DEFENDER_PASSWORD], "list")))
        assert "not correct" not in result_defender.stdout, "Bad Shadow Defender password!"
        print("Shadow Defender list is ok!")

        async with NamedTemporaryFile() as f:
            async with conn.start_sftp_client() as sftp:
                await sftp.get(r"C:\Windows\System32\drivers\etc\hosts", f.name)
                with open(f.name, "r") as local_f:
                    assert local_f.read()
                print("sftp open")
