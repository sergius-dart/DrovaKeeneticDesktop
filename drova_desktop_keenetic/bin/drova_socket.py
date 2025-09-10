import asyncio
from logging import DEBUG, basicConfig

from drova_desktop_keenetic.common.drova_socket import DrovaSocket


basicConfig(level=DEBUG)


def run_async_main():
    asyncio.run(DrovaSocket().serve(True))


if __name__ == "__main__":
    run_async_main()
