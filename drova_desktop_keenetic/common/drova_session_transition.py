import logging
from enum import Enum

from drova_desktop_keenetic.common.drova import StatusEnum
from drova_desktop_keenetic.common.patch import SessionHandlerContext, make_patchers


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

    def __init__(self, status: StatusEnum | None):
        self._state: SessionState = SessionState.from_status_enum(status)
        self._patchers = make_patchers()
        self._ctx = SessionHandlerContext(ssh=None, sftp=None)

    async def set_status(self, new_status: StatusEnum | None):
        old_state = self._state
        self._state = SessionState.from_status_enum(new_status)

        # not need any work if state not changed
        if old_state == self._state:
            return

        self.logger.info("Session transition from %s to %s", old_state, self._state)

        task = None
        match self._state:
            case SessionState.NONE_SESSION:
                task = self._on_idle()
            case SessionState.SESSION_START:
                task = self._on_session_start()
            case SessionState.SESSION_ACTIVE:
                task = self._on_session_active()
            case SessionState.SESSION_END:
                task = self._on_session_end()

        if task:
            self.logger.debug("Call task to execute %s", task)
            await task

    async def _on_idle(self):
        for patch in self._patchers:
            try:
                await patch.on_idle(self._ctx)
            except Exception as exc:  # pylint: disable=W0718
                self.logger.error(exc)

    async def _on_session_start(self):
        for patch in self._patchers:
            try:
                await patch.on_session_start(self._ctx)
            except Exception as exc:  # pylint: disable=W0718
                self.logger.error(exc)

    async def _on_session_active(self):
        for patch in self._patchers:
            try:
                await patch.on_session_active(self._ctx)
            except Exception as exc:  # pylint: disable=W0718
                self.logger.error(exc)

    async def _on_session_end(self):
        for patch in self._patchers:
            try:
                await patch.on_session_end(self._ctx)
            except Exception as exc:  # pylint: disable=W0718
                self.logger.error(exc)
