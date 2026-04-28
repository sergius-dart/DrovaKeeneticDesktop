import pytest

from drova_desktop_keenetic.common.commands import (
    DuplicateAuthCode,
    NotFoundAuthCode,
    PsExec,
    PsExecNotFoundExecutable,
    RegQueryEsme,
)


def test_parse_PSExec() -> None:  # pylint: disable=C0103
    with pytest.raises(PsExecNotFoundExecutable):
        PsExec.parse_stderr_errror_code("Test\r\nNot found executable\r\n\r\n\r\n")

    with pytest.raises(PsExecNotFoundExecutable):
        PsExec.parse_stderr_errror_code("Не удается найти указанный файл")


def test_parse_RegQueryEsme() -> None:  # pylint: disable=C0103
    with pytest.raises(DuplicateAuthCode):
        RegQueryEsme.parse_auth_code(
            r"""
HKEY_LOCAL_MACHINE\SOFTWARE\ITKey\Esme\servers\8ff8ea03-5b09-4fad-a132-888888888888
    auth_token    REG_SZ    07c43183-61b2-4e18-91cd-888888888888
    auth_token    REG_SZ    07c43183-61b2-4e18-91cd-888888888888
"""
        )

    with pytest.raises(NotFoundAuthCode):
        RegQueryEsme.parse_auth_code(
            r"""
HKEY_LOCAL_MACHINE\SOFTWARE\ITKey\Esme\servers\8ff8ea03-5b09-4fad-a132-888888888888
"""
        )

    server_id, auth_token = RegQueryEsme.parse_auth_code(
        r"""
HKEY_LOCAL_MACHINE\SOFTWARE\ITKey\Esme\servers\8ff8ea03-5b09-4fad-a132-888888888888
    auth_token    REG_SZ    07c43183-61b2-4e18-91cd-888888888888
"""
    )
    assert server_id == "8ff8ea03-5b09-4fad-a132-888888888888"
    assert auth_token == "07c43183-61b2-4e18-91cd-888888888888"
