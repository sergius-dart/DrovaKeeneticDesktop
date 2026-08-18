import logging
from enum import Enum

from drova_desktop_keenetic.common.config import Config
from drova_desktop_keenetic.common.drova import StatusEnum
from drova_desktop_keenetic.common.patch import (
    ISessionHandler,
    SessionHandlerContext,
    make_patchers,
)


def load_patchers():
    import drova_desktop_keenetic.patches.obs  # pylint: disable=W0611
    from drova_desktop_keenetic.patches.basic import logger

    logger.info("load basic patchers")


class SessionState(Enum):
    NONE_SESSION = frozenset({0})  # idle session
    SESSION_START = frozenset({StatusEnum.NEW, StatusEnum.HANDSHAKE})
    SESSION_ACTIVE = frozenset({StatusEnum.ACTIVE})
    SESSION_END = frozenset({StatusEnum.ABORTED, StatusEnum.FINISHED})
    SESSION_FORCE_CLOSE = frozenset({1})  # session ended - need close
    # frosensets in enum check value - need unique value

    @classmethod
    def from_status_enum(cls, status: StatusEnum | None) -> "SessionState":
        if not status:
            return cls.NONE_SESSION

        for enum in cls:
            if status in enum.value:
                return enum

        return cls.NONE_SESSION


class DrovaSessionTransition:
    logger = logging.getLogger(__file__)

    def __init__(self, protector: ISessionHandler, config: Config):
        load_patchers()
        self._patchers = make_patchers(config)
        self._protector = protector
        self._prev_ctx: None | SessionHandlerContext = None

    async def _start_protections(self, ctx: SessionHandlerContext):
        await self._protector.on_session_start(ctx)
        await self._on_session_start(ctx)

    async def update_ctx(self, ctx: SessionHandlerContext):  # pylint: disable=R0912
        old_state = SessionState.from_status_enum(
            self._prev_ctx.session.status if self._prev_ctx and self._prev_ctx.session else None
        )
        new_state = SessionState.from_status_enum(ctx.session.status if ctx.session else None)

        self.logger.info("Session transition from %s to %s", old_state, new_state)

        # not need any work if state not changed
        if (  # pylint: disable=R0916
            self._prev_ctx
            and self._prev_ctx.session
            and ctx.session
            and self._prev_ctx.session.uuid != ctx.session.uuid
            and new_state == SessionState.SESSION_ACTIVE
            and old_state == SessionState.SESSION_ACTIVE
        ):
            new_state = SessionState.SESSION_FORCE_CLOSE
        if old_state == new_state:
            self._prev_ctx = ctx
            return

        # return to NONE_SESSION need stop session - server don't answer as session and need reboot and all close
        if new_state == SessionState.NONE_SESSION:
            if old_state in {SessionState.SESSION_ACTIVE}:
                new_state = SessionState.SESSION_FORCE_CLOSE
        elif new_state == SessionState.SESSION_END:
            if old_state == SessionState.NONE_SESSION:
                return  # skip from end session to none
        elif new_state == SessionState.SESSION_ACTIVE:
            if old_state in {SessionState.SESSION_END, SessionState.SESSION_FORCE_CLOSE}:
                new_state = SessionState.SESSION_START

        self._prev_ctx = ctx

        self.logger.info("Session transition after fix from %s to %s", old_state, new_state)

        task_protect = None
        task = None
        match new_state:
            case SessionState.NONE_SESSION:
                task_protect = self._protector.on_idle(ctx)
                task = self._on_idle(ctx)
            case SessionState.SESSION_START:
                task_protect = self._protector.on_session_start(ctx)
                task = self._on_session_start(ctx)
            case SessionState.SESSION_ACTIVE:
                task_protect = self._protector.on_session_active(ctx)
                task = self._on_session_active(ctx)
            case SessionState.SESSION_END | SessionState.SESSION_FORCE_CLOSE:
                task_protect = self._protector.on_session_end(ctx)
                task = self._on_session_end(ctx)
            case _:
                task_protect = None
                task = None

        self.logger.debug("Call task to execute %s", task)
        if task_protect:
            await task_protect

        if task:
            await task

    async def _on_idle(self, ctx: SessionHandlerContext):
        for patch in self._patchers:
            try:
                await patch.on_idle(ctx)
            except Exception:  # pylint: disable=W0718
                self.logger.exception("_on_idle")

    async def _on_session_start(self, ctx: SessionHandlerContext):
        for patch in self._patchers:
            try:
                await patch.on_session_start(ctx)
            except Exception:  # pylint: disable=W0718
                self.logger.exception("_on_session_start")

    async def _on_session_active(self, ctx: SessionHandlerContext):
        for patch in self._patchers:
            try:
                await patch.on_session_active(ctx)
            except Exception:  # pylint: disable=W0718
                self.logger.exception("_on_session_active")

    async def _on_session_end(self, ctx: SessionHandlerContext):
        for patch in self._patchers:
            try:
                await patch.on_session_end(ctx)
            except Exception:  # pylint: disable=W0718
                self.logger.exception("_on_session_end")
