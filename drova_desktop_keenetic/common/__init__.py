import os
from pathlib import Path

from dotenv import load_dotenv

ENV_LOCATION = (
    os.environ["ENV_LOCATION"] if "ENV_LOCATION" in os.environ else Path(__file__).parent.parent.parent / ".env"
)

load_dotenv(ENV_LOCATION)
