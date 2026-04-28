import logging

logger = logging.getLogger(__name__)


class RebootRequired(RuntimeError): ...


def to_str(pstr: bytes | str | None, encoding: str = "utf-8") -> str:
    if not pstr:
        return ""
    if isinstance(pstr, bytes):
        return pstr.decode(encoding=encoding)
    if isinstance(pstr, str):
        return pstr
    return ""
