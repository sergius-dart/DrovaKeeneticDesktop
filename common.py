import logging
import os
import re
from abc import ABC, abstractmethod
from configparser import ConfigParser
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from ipaddress import IPv4Address
from pathlib import PureWindowsPath
from time import sleep
from typing import Literal
from uuid import UUID

import requests
from dotenv import load_dotenv
from mslex import quote
from paramiko import AutoAddPolicy, SFTPClient, SFTPFile, SSHClient
from pydantic import BaseModel

load_dotenv()

logger = logging.getLogger(__name__)


class PsExecNotFoundExecutable(RuntimeError): ...


class NotFoundAuthCode(RuntimeError): ...


class DuplicateAuthCode(RuntimeError): ...


@dataclass(kw_only=True)
class ICommandBuilder(ABC):

    @abstractmethod
    def _build_command(self) -> str: ...

    def __str__(self) -> str:
        return self._build_command()


@dataclass
class PsExec(ICommandBuilder):
    interactive: int | None = 1
    accepteula: bool = True
    command: ICommandBuilder | str = ""

    def _build_command(self) -> str:
        command = ["psexec"]

        if self.interactive is not None:
            command += ["-i", str(self.interactive)]

        if self.accepteula:
            command += ["-accepteula"]

        command += [quote(str(self.command))]

        return " ".join(command)

    @staticmethod
    def parseStderrErrorCode(stderr: bytes) -> int:
        last_line = b""
        for line in stderr.split(b"\r\n"):
            if line:
                last_line = line

        r = re.compile(r"(?P<executable>\S*) exited on (?P<hostname>\S*) with error code (?P<exit_code>\d+)\.")

        print(last_line.decode("windows-1251"))
        if match := r.search(last_line.decode("windows-1251")):
            return int(match.group("exit_code") + "0")

        raise PsExecNotFoundExecutable()


@dataclass
class TaskKill(ICommandBuilder):
    image: str
    force: bool = True

    def _build_command(self) -> str:
        command = ["taskkill.exe"]

        if self.force:
            command += ["/f"]

        command += ["/IM", self.image]

        return " ".join(command)


@dataclass
class Steam(ICommandBuilder):
    def _build_command(self) -> str:
        return r"C:\Program Files (x86)\Steam\steam.exe"


@dataclass
class EpicGamesLauncher(ICommandBuilder):
    def _build_command(self) -> str:
        return r"C:\Program Files (x86)\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe"


@dataclass
class ShadowDefenderCLI(ICommandBuilder):
    password: str
    actions: list[Literal["enter", "exit", "reboot", "commit"]]
    drives: str | None = None

    def _build_command(self) -> str:
        command = [quote(r"C:\Program Files\Shadow Defender\CmdTool.exe")]
        command += [f'/pwd:"{self.password}"']
        for action in self.actions:
            match action:
                case "enter":
                    assert self.drives
                    command += [f"/enter:{self.drives}"]
                case "exit":
                    assert self.drives
                    command += [f"/exit:{self.drives}"]
                case "reboot":
                    command += ["/reboot"]
                case "commit":
                    assert self.drives
                    command += [f'/commit:"{drive}:\\"' for drive in self.drives.split("")]
        command += ["/now"]
        return " ".join(command)


@dataclass
class RegQueryEsme(ICommandBuilder):
    def _build_command(self) -> str:
        return " ".join(("reg", "query", r"HKEY_LOCAL_MACHINE\SOFTWARE\ITKey\Esme\servers", "/s", "/f", "auth_token"))

    @staticmethod
    def parseAuthCode(stdout: bytes) -> tuple[str, str]:
        r_auth_token = re.compile(r"auth_token\s+REG_SZ\s+(?P<auth_token>\S+)", re.MULTILINE)

        r_servers = re.compile(r"servers\\(?P<server_id>\S+)", re.MULTILINE)

        matches_auth_token = r_auth_token.findall(stdout.decode("windows-1251"))
        if not matches_auth_token:
            raise NotFoundAuthCode()

        if len(matches_auth_token) > 1:
            raise DuplicateAuthCode()

        matches_server_id = r_servers.search(stdout.decode("windows-1251"))
        if not matches_server_id:
            raise NotFoundAuthCode()

        return matches_server_id["server_id"], matches_auth_token[0]


class IPatch(ABC):
    remote_file_location: PureWindowsPath

    @abstractmethod
    def _patch(self, file: SFTPFile): ...

    def patch(self, sftp: SFTPClient):
        with sftp.file(str(self.remote_file_location), "r+") as f:
            self._patch(f)
            f.flush()


class EpicGamesAuthDiscard(IPatch):
    logger = logger.getChild("EpicGamesAuthDiscard")

    remote_file_location = PureWindowsPath(r"AppData\Local\EpicGamesLauncher\Saved\Config\Windows\Game.ini")

    def _patch(self, file: SFTPFile):
        config = ConfigParser()
        self.logger.info("read Game.ini")
        config.read_file(file, "Game.ini")

        config.remove_section("RememberMe")
        self.logger.info("Write without auth section")
        config.write(file)


class SteamAuthDiscard(IPatch):
    logger = logger.getChild("SteamAuthDiscard")
    # remote_file_location = PureWindowsPath(r'c:\Program Files (x86)\Steam\config\config.vdf')
    remote_file_location = PureWindowsPath(r"c:\Program Files (x86)\Steam\config\loginusers.vdf")

    def _patch(self, file: SFTPFile):
        file.write(
            """"users"
{
}"""
        )
        # self.logger.info('Read config.vdf')
        # content_config = file.read().decode()

        # r = re.compile(r'(?P<header>"Authentication"\s+{\s+"RememberedMachineID"\s+{)(\s+"\w+"\s+"\S+)+(?P<end>\s+}\s+})')

        # r.sub('\1\3', content_config)
        # self.logger.info('Write without any authentificated')
        # file.write(content_config.encode())


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


class CheckDesktop:
    def exec(self, client: SSHClient) -> bool:
        _, stdout, _ = client.exec_command(str(RegQueryEsme()))
        serveri_id, auth_token = RegQueryEsme.parseAuthCode(stdout=stdout.read())

        req = requests.get(URL_SESSIONS, {"server_id": serveri_id}, headers={"X-Auth-Token": auth_token})
        resp = SessionsResponse(**req.json())

        if not resp.sessions:
            return False

        session = resp.sessions[0]
        if session.status in ("HANDSHAKE", "ACTIVE", "NEW"):
            return session.product_id == UUID_DESKTOP
        # by default, if session not is started (aborted/finished) return false
        return False


WINDOWS_HOST = "WINDOWS_HOST"
WINDOWS_LOGIN = "WINDOWS_LOGIN"
WINDOWS_PASSWORD = "WINDOWS_PASSWORD"

SHADOW_DEFENDER_PASSWORD = "SHADOW_DEFENDER_PASSWORD"
SHADOW_DEFENDER_DRIVES = "SHADOW_DEFENDER_DRIVES"


class BeforeConnect:
    logger = logger.getChild("BeforeConnect")

    def check_env(self) -> None:
        self.logger.info("check_env")
        assert not hasattr(os.environ, WINDOWS_HOST), "Please set WINDOWS_HOST in .env file"
        assert not hasattr(os.environ, WINDOWS_LOGIN), "Please set WINDOWS_LOGIN in .env file"

        assert not hasattr(os.environ, SHADOW_DEFENDER_PASSWORD), "Please set SHADOW_DEFENDER_PASSWORD in .env file"
        assert not hasattr(os.environ, SHADOW_DEFENDER_DRIVES), "Please set SHADOW_DEFENDER_DRIVES in .env file"

    def run(self) -> int:
        self.check_env()
        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())
        self.logger.info("connect to windows")
        client.connect(
            os.environ[WINDOWS_HOST], username=os.environ[WINDOWS_LOGIN], password=os.environ[WINDOWS_PASSWORD]
        )
        if not CheckDesktop().exec(client):
            return 1

        self.logger.info("open sftp")
        sftp = client.open_sftp()

        self.logger.info(f"start shadow")
        # start shadow mode
        client.exec_command(
            str(
                ShadowDefenderCLI(
                    password=os.environ[SHADOW_DEFENDER_PASSWORD],
                    actions=["enter"],
                    drives=os.environ[SHADOW_DEFENDER_DRIVES],
                )
            )
        )
        sleep(0.3)

        self.logger.info(f"prepare steam")
        # prepare steam
        client.exec_command(str(TaskKill(image="steam.exe")))
        sleep(0.1)
        steam = SteamAuthDiscard()
        steam.patch(sftp=sftp)
        # client.exec_command(str(PsExec(command=Steam()))) # todo autorestart steam launcher

        self.logger.info("prepare epic")
        # prepare epic
        client.exec_command(str(TaskKill(image="EpicGamesLauncher.exe")))
        sleep(0.1)
        epic = EpicGamesAuthDiscard()
        epic.patch(sftp=sftp)
        # client.exec_command(str(PsExec(command=EpicGamesLauncher()))) # todo autorestart epic launcher

        client.close()

        return 0


class AfterDisconnect:
    logger = logger.getChild("BeforeConnect")

    # todo move to base class maybe?
    def check_env(self) -> None:
        self.logger.info("check_env")
        assert not hasattr(os.environ, WINDOWS_HOST), "Please set WINDOWS_HOST in .env file"
        assert not hasattr(os.environ, WINDOWS_LOGIN), "Please set WINDOWS_LOGIN in .env file"

        assert not hasattr(os.environ, SHADOW_DEFENDER_PASSWORD), "Please set SHADOW_DEFENDER_PASSWORD in .env file"
        assert not hasattr(os.environ, SHADOW_DEFENDER_DRIVES), "Please set SHADOW_DEFENDER_DRIVES in .env file"

    def run(self) -> int:
        self.check_env()
        client = SSHClient()
        client.set_missing_host_key_policy(AutoAddPolicy())
        self.logger.info("connect to windows")
        client.connect(
            os.environ[WINDOWS_HOST], username=os.environ[WINDOWS_LOGIN], password=os.environ[WINDOWS_PASSWORD]
        )

        self.logger.info("exit from shadow and reboot")
        # exit shadow mode and reboot
        client.exec_command(
            str(
                ShadowDefenderCLI(
                    password=os.environ[SHADOW_DEFENDER_PASSWORD],
                    actions=["exit", "reboot"],
                    drives=os.environ[SHADOW_DEFENDER_DRIVES],
                )
            )
        )

        client.close()
        return 0
