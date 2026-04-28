import os

from aiofiles.tempfile import NamedTemporaryFile
from asyncssh import connect as connect_ssh

from drova_desktop_keenetic.common.commands import PsExec, ShadowDefenderCLI
from drova_desktop_keenetic.common.constants import (
    SHADOW_DEFENDER_PASSWORD,
    WINDOWS_HOST,
    WINDOWS_LOGIN,
    WINDOWS_PASSWORD,
)
from drova_desktop_keenetic.common.helpers import to_str


def validate_env():
    assert not hasattr(os.environ, WINDOWS_HOST), "Please set WINDOWS_HOST in .env file"
    assert not hasattr(os.environ, WINDOWS_LOGIN), "Please set WINDOWS_LOGIN in .env file"

    assert not hasattr(os.environ, SHADOW_DEFENDER_PASSWORD), "Please set SHADOW_DEFENDER_PASSWORD in .env file"


async def validate_creds():
    async with connect_ssh(
        host=os.environ[WINDOWS_HOST],
        username=os.environ[WINDOWS_LOGIN],
        password=os.environ[WINDOWS_PASSWORD],
        known_hosts=None,
        encoding="windows-1251",
    ) as conn:
        print("Windows access complete!")
        result_defender = await conn.run(
            str(ShadowDefenderCLI(password=os.environ[SHADOW_DEFENDER_PASSWORD], actions=["list"]))
        )
        assert "not correct" not in to_str(result_defender.stdout, "windows-1251"), "Bad Shadow Defender password!"
        print("Shadow Defender list is ok!")

        async with NamedTemporaryFile() as f:
            async with conn.start_sftp_client() as sftp:
                await sftp.get(r"C:\Windows\System32\drivers\etc\hosts", str(f.name))
                with open(f.name, "r", encoding="utf8") as local_f:
                    assert local_f.read()
                print("sftp open")

        result_psexec = await conn.run(str(PsExec(r"cmd /c 'echo 1'", detach=False)))
        PsExec.parse_stderr_errror_code(to_str(result_psexec.stderr, "windows-1251"))
