import logging
from enum import Enum

from drova_desktop_keenetic.common.drova import StatusEnum
from drova_desktop_keenetic.common.patch import (
    ISessionHandler,
    SessionHandlerContext,
    make_patchers,
)


class SessionState(Enum):
    NONE_SESSION = frozenset({})
    SESSION_START = frozenset({StatusEnum.NEW, StatusEnum.HANDSHAKE})
    SESSION_ACTIVE = frozenset({StatusEnum.ACTIVE})
    SESSION_END = frozenset({StatusEnum.ABORTED, StatusEnum.FINISHED})

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
        self._patchers = make_patchers()
        self._protector = protector

    async def set_status(self, new_status: StatusEnum | None, ctx: SessionHandlerContext):
        old_state = self._state
        self._state = SessionState.from_status_enum(new_status)

        # not need any work if state not changed
        if old_state == self._state:
            return

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
            case SessionState.SESSION_END:
                task_protect = self._protector.on_session_end(ctx)
                task = self._on_session_end(ctx)

        if task and task_protect:
            self.logger.debug("Call task to execute %s", task)
            await task_protect
            await task

    async def _on_idle(self, ctx: SessionHandlerContext):
        for patch in self._patchers:
            try:
                await patch.on_idle(ctx)
            except Exception as exc:  # pylint: disable=W0718
                self.logger.error(exc)

    async def _on_session_start(self, ctx: SessionHandlerContext):
        for patch in self._patchers:
            try:
                await patch.on_session_start(ctx)
            except Exception as exc:  # pylint: disable=W0718
                self.logger.error(exc)

    async def _on_session_active(self, ctx: SessionHandlerContext):
        for patch in self._patchers:
            try:
                await patch.on_session_active(ctx)
            except Exception as exc:  # pylint: disable=W0718
                self.logger.error(exc)

    async def _on_session_end(self, ctx: SessionHandlerContext):
        for patch in self._patchers:
            try:
                await patch.on_session_end(ctx)
            except Exception as exc:  # pylint: disable=W0718
                self.logger.error(exc)
