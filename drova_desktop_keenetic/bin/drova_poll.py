import asyncio

from drova_desktop_keenetic.common.drova_poll import DrovaPoll


def run_async_main():
    asyncio.run(DrovaPoll().serve(True))


if __name__ == "__main__":
    run_async_main()
