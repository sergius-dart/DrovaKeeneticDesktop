from unittest.mock import AsyncMock, Mock

import pytest
from asyncssh import SSHCompletedProcess

from drova_desktop_keenetic.common.helpers import CheckDesktop, RebootRequired


@pytest.mark.asyncio
async def test_CheckDesktop(mocker):

    # async def new_run(*args,**kwargs)-> SSHCompletedProcess:
    result = SSHCompletedProcess()
    result.returncode = 0
    result.stdout = r"""
HKEY_LOCAL_MACHINE\SOFTWARE\ITKey\Esme\servers\85dd80c4-adc1-1111-1111-111111111111
    auth_token    REG_SZ    7a8b78f4-103d-1111-1111-111111111111
"""
    # return result

    client = Mock()
    client.run = AsyncMock(return_value=result)

    helper = CheckDesktop(client)
    await helper.refresh_actual_tokens()
    assert client.run.call_count == 1

    @mocker.patch("drova_desktop_keenetic.common.helpers.get_latest_session")
    async def _():
        return None

    await helper.run()

    assert client.call_count == 0


@pytest.mark.asyncio
async def test_RebootRequiredNoAuthCode():
    with pytest.raises(RebootRequired):

        # async def new_run(*args,**kwargs)-> SSHCompletedProcess:
        result = SSHCompletedProcess()
        result.returncode = 0
        result.stdout = r"""
    HKEY_LOCAL_MACHINE\SOFTWARE\ITKey\Esme\servers\85dd80c4-adc1-1111-1111-111111111111
    """
        # return result

        client = Mock()
        client.run = AsyncMock(return_value=result)

        helper = CheckDesktop(client)
        await helper.refresh_actual_tokens()
        print(client.run.called)
        assert client.run.call_count == 1


@pytest.mark.asyncio
async def test_RebootRequiredBadReturn():
    with pytest.raises(RebootRequired):

        # async def new_run(*args,**kwargs)-> SSHCompletedProcess:
        result = SSHCompletedProcess()
        result.returncode = 1
        result.stdout = None
        # return result

        client = Mock()
        client.run = AsyncMock(return_value=result)

        helper = CheckDesktop(client)
        await helper.refresh_actual_tokens()
        print(client.run.called)
        assert client.run.call_count == 1
