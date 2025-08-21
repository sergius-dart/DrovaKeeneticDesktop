import pytest

from common import DuplicateAuthCode, NotFoundAuthCode, PsExec, PsExecNotFoundExecutable, RegQueryEsme


def test_parse_PSExec() -> None:
    with pytest.raises(PsExecNotFoundExecutable):
        PsExec.parseStderrErrorCode(b"Test\r\nNot found executable\r\n\r\n\r\n")

    with pytest.raises(PsExecNotFoundExecutable):
        PsExec.parseStderrErrorCode("Не удается найти указанный файл".encode("windows-1251"))


def test_parse_RegQueryEsme() -> None:
    with pytest.raises(DuplicateAuthCode):
        RegQueryEsme.parseAuthCode(
            r"""
HKEY_LOCAL_MACHINE\SOFTWARE\ITKey\Esme\servers\8ff8ea03-5b09-4fad-a132-888888888888
    auth_token    REG_SZ    07c43183-61b2-4e18-91cd-888888888888
    auth_token    REG_SZ    07c43183-61b2-4e18-91cd-888888888888
""".encode(
                "windows-1251"
            )
        )

    with pytest.raises(NotFoundAuthCode):
        RegQueryEsme.parseAuthCode(
            r"""
HKEY_LOCAL_MACHINE\SOFTWARE\ITKey\Esme\servers\8ff8ea03-5b09-4fad-a132-888888888888
""".encode(
                "windows-1251"
            )
        )

    server_id, auth_token = RegQueryEsme.parseAuthCode(
        r"""
HKEY_LOCAL_MACHINE\SOFTWARE\ITKey\Esme\servers\8ff8ea03-5b09-4fad-a132-888888888888
    auth_token    REG_SZ    07c43183-61b2-4e18-91cd-888888888888
""".encode(
            "windows-1251"
        )
    )
    assert server_id == "8ff8ea03-5b09-4fad-a132-888888888888"
    assert auth_token == "07c43183-61b2-4e18-91cd-888888888888"
