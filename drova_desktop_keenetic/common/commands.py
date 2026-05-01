import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import PureWindowsPath
from typing import Literal

from mslex import quote

from drova_desktop_keenetic.common.constants import WINDOWS_LOGIN, WINDOWS_PASSWORD


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
    command: ICommandBuilder | str = ""
    interactive: int | None = field(kw_only=True, default=1)
    accepteula: bool = True
    detach: bool = True
    user: str = os.environ[WINDOWS_LOGIN]
    password: str = os.environ[WINDOWS_PASSWORD]
    working_directory: PureWindowsPath | None = None

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

        if self.working_directory:
            command += ["-w", quote(str(self.working_directory))]

        command += [str(self.command)]
        return " ".join(command)

    @staticmethod
    def parse_stderr_errror_code(stderr: str) -> int:
        last_line = ""
        for line in stderr.split("\r\n"):
            if line:
                last_line = line

        r = re.compile(r"(?P<executable>\S*) exited on (?P<hostname>\S*) with error code (?P<exit_code>\d+)\.")

        if match := r.search(last_line):
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
    now: bool = True

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
                    command += ["/list"]
        if self.now:
            command += ["/now"]
        return " ".join(command)


@dataclass
class RegQueryEsme(ICommandBuilder):
    def _build_command(self) -> str:
        return " ".join(("reg", "query", r"HKEY_LOCAL_MACHINE\SOFTWARE\ITKey\Esme\servers", "/s", "/f", "auth_token"))

    @staticmethod
    def parse_auth_code(stdout: str) -> tuple[str, str]:
        r_auth_token = re.compile(r"auth_token\s+REG_SZ\s+(?P<auth_token>\S+)", re.MULTILINE)

        r_servers = re.compile(r"servers\\(?P<server_id>\S+)", re.MULTILINE)

        matches_auth_token = r_auth_token.findall(stdout)
        if not matches_auth_token:
            raise NotFoundAuthCode()

        if len(matches_auth_token) > 1:
            raise DuplicateAuthCode()

        matches_server_id = r_servers.search(stdout)
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
            args.append(str(self.value))

        return " ".join(args)


class RegKeyAction(ICommandBuilder):  # pylint: disable=R0903
    pass


class RegDelActionRemoveValue(RegKeyAction):  # pylint: disable=R0903
    value_name: str

    def _build_command(self):
        return f"/v {self.value_name}"


class RegDelActionRemoveDefault(RegKeyAction):  # pylint: disable=R0903
    def _build_command(self):
        return "/ve"


class RegDelActionRemoveAllValues(RegKeyAction):  # pylint: disable=R0903
    def _build_command(self):
        return "/va"


@dataclass
class RegDel(ICommandBuilder):
    key: str
    action: RegKeyAction

    def _build_command(self):
        return " ".join(("reg", "delete", quote(self.key), "/f", str(self.action)))


@dataclass
class WmicGetLocalDrives(ICommandBuilder):
    def _build_command(self):
        return "wmic logicaldisk where drivetype=3 get name"

    @staticmethod
    def parse(output: bytes | str | None) -> list[str]:
        if not output:
            return []
        realoutput: str | None = None
        if isinstance(output, bytes):
            realoutput = output.decode()
        elif isinstance(output, str):
            realoutput = output
        assert realoutput
        result: list[str] = []
        for line in realoutput.split("\n")[1:]:
            if not line:
                continue
            result.append(line[0])
        return result


@dataclass
class Shutdown(ICommandBuilder):
    actions: Literal["reboot", "shutdown"]
    timeout: int = 10

    def _build_command(self):
        command = ["shutdown"]
        match self.actions:
            case "reboot":
                command.append("/r")
            case "shutdown":
                command.append("/s")
        command.append("/t")
        command.append(str(self.timeout))

        return " ".join(command)


@dataclass
class ObsStartStreaming(ICommandBuilder):
    OBS_PATH = PureWindowsPath(r"C:\Program Files\obs-studio\bin\64bit\obs64.exe")
    profile: str
    collection: str
    scene: str

    def _build_command(self):
        return " ".join(
            (
                quote(str(self.OBS_PATH)),
                "--profile",
                self.profile,
                "--collection",
                self.collection,
                "--scene",
                self.scene,
                "--startstreaming",
                "--minimize-to-tray",
            )
        )
