import asyncio

from drova_desktop_keenetic.common import ENV_LOCATION
from drova_desktop_keenetic.common.drova_validate import validate_creds, validate_env


def main():
    print(ENV_LOCATION)
    validate_env()
    asyncio.run(validate_creds())
    print("Ok!")


if __name__ == "__main__":
    main()
