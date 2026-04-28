import asyncio

from drova_desktop_keenetic.common.config import Config
from drova_desktop_keenetic.common.drova import FakeDrova
from drova_desktop_keenetic.common.drova_poll import DrovaPoll


async def main():
    fake_drova = FakeDrova()
    await fake_drova.start()
    config = Config(drova_service_host=fake_drova.faked_host)
    await DrovaPoll(config).serve(True)


def run_async_main():
    asyncio.run(main())


if __name__ == "__main__":
    run_async_main()
