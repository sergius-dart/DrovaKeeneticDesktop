import pytest

from drova_desktop_keenetic.common.patch import _ALL_PATCHES, ISessionHandler, patcher


def test_registered():

    @patcher
    class SimplePath(ISessionHandler):  # pylint: disable=W0612
        async def on_idle(self, ctx):
            return await super().on_idle(ctx)

        async def on_session_start(self, ctx):
            return await super().on_session_start(ctx)

        async def on_session_active(self, ctx):
            return await super().on_session_active(ctx)

        async def on_session_end(self, ctx):
            return await super().on_session_end(ctx)

    with pytest.raises(RuntimeError):

        @patcher
        class NotAPatcher:  # pylint: disable=R0903,W0612
            pass

    assert len(_ALL_PATCHES) == 1
