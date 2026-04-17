import pytest

from drova_desktop_keenetic.common.patch import _ALL_PATCHES, ISessionHandler, patcher


def test_registered():

    @patcher
    class SimplePath(ISessionHandler):  # pylint: disable=W0612
        pass

    with pytest.raises(RuntimeError):

        @patcher
        class NotAPatcher:  # pylint: disable=R0903,W0612
            pass

    assert len(_ALL_PATCHES) == 1
