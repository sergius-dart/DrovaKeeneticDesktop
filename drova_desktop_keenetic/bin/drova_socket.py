import asyncio
import os
from logging import DEBUG, StreamHandler, basicConfig
from logging.handlers import RotatingFileHandler

from drova_desktop_keenetic.common.contants import DROVA_SOCKET_LISTEN
from drova_desktop_keenetic.common.drova_socket import DrovaSocket

assert DROVA_SOCKET_LISTEN in os.environ, "Need socket listening"

ch = StreamHandler()
handler_rotating = RotatingFileHandler(
    f"app.{os.environ[DROVA_SOCKET_LISTEN]}.log", maxBytes=1024 * 1024, backupCount=5
)


basicConfig(level=DEBUG, handlers=(handler_rotating, ch))


def run_async_main():
    asyncio.run(DrovaSocket().serve(True))


if __name__ == "__main__":
    run_async_main()
