import logging
from enum import Enum

from drova_desktop_keenetic.common.drova import StatusEnum
from drova_desktop_keenetic.common.patch import (
    ISessionHandler,
    SessionHandlerContext,
    load_patchers,
    make_patchers,
)


class SessionState(Enum):
    NONE_SESSION = frozenset({})  # idle session
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

    def __init__(self, status: StatusEnum | None, protector: ISessionHandler):
        self._state: SessionState = SessionState.from_status_enum(status)
        load_patchers()
        self._patchers = make_patchers()
        self._protector = protector

    async def set_status(self, new_status: StatusEnum | None, ctx: SessionHandlerContext):
        old_state = self._state
        new_state = SessionState.from_status_enum(new_status)

        # not need any work if state not changed
        if old_state == new_state:
            return

        # return to NONE_SESSION need stop session - server don't answer as session and need reboot and all close
        if new_state == SessionState.NONE_SESSION:
            if old_state not in {SessionState.NONE_SESSION, SessionState.SESSION_END, SessionState.SESSION_FORCE_CLOSE}:
                new_state = SessionState.SESSION_FORCE_CLOSE
        elif new_state == SessionState.SESSION_END:
            if old_state == SessionState.NONE_SESSION:
                return  # skip from end session to none

        self._state = new_state

        self.logger.info("Session transition from %s to %s", old_state, self._state)

        task_protect = None
        task = None
        match self._state:
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
