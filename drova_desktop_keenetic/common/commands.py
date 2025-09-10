import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

from mslex import quote


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
