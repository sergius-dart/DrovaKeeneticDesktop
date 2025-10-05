import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from mslex import quote

from drova_desktop_keenetic.common.contants import WINDOWS_LOGIN, WINDOWS_PASSWORD


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
    detach: bool = True
    user: str = os.environ[WINDOWS_LOGIN]
    password: str = os.environ[WINDOWS_PASSWORD]

    def _build_command(self) -> str:
        command = ["psexec"]

        if self.interactive is not None:
            command += ["-i", str(self.interactive)]

        if self.accepteula:
            command += ["-accepteula"]

        if self.detach:
            command += ["-d"]

        if self.user:
            command += ["-u", quote(self.user)]

        if self.password:
            command += ["-p", quote(self.password)]

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
    actions: list[Literal["enter", "exit", "reboot", "commit", "list"]]
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
                case "list":
                    command += [f"/list"]
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


class RegValueType(StrEnum):
    REG_SZ = "REG_SZ"
    REG_MULTI_SZ = "REG_MULTI_SZ"
    REG_DWORD_BIG_ENDIAN = "REG_DWORD_BIG_ENDIAN"
    REG_DWORD = "REG_DWORD"
    REG_BINARY = "REG_BINARY"
    REG_DWORD_LITTLE_ENDIAN = "REG_DWORD_LITTLE_ENDIAN"
    REG_LINK = "REG_LINK"
    REG_FULL_RESOURCE_DESCRIPTOR = "REG_FULL_RESOURCE_DESCRIPTOR"
    REG_EXPAND_SZ = "REG_EXPAND_SZ"


@dataclass
class RegAdd(ICommandBuilder):

    reg_path: str
    value_name: str | None = None
    value_type: RegValueType | None = None
    value: str | int | bytes | None = None
    force = True

    def _build_command(self):
        args = ["reg", "add", quote(self.reg_path)]
        if self.force:
            args.append("/f")

        if self.value_name is not None:
            args.append("/v")
            args.append(quote(self.value_name))

        if self.value_type is not None:
            args.append("/t")
            args.append(self.value_type)

        if self.value is not None:
            args.append("/d")
            args.append(f"{self.value}")

        return " ".join(args)
