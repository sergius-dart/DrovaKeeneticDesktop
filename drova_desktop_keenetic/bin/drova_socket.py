import asyncio
import os
from logging import warning
from logging.handlers import RotatingFileHandler

from drova_desktop_keenetic.common.contants import DROVA_SOCKET_LISTEN
from drova_desktop_keenetic.common.drova_socket import DrovaSocket

assert DROVA_SOCKET_LISTEN in os.environ, "Need socket listening"


def run_async_main():
    warning("Is DEPRECATED!")
    asyncio.run(DrovaSocket().serve(True))


if __name__ == "__main__":
    run_async_main()
