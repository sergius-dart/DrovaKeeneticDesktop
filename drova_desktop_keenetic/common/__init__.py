from dotenv import load_dotenv
import os
from pathlib import Path

ENV_LOCATION = (
    os.environ["ENV_LOCATION"] if hasattr(os.environ, "ENV_LOCATION") else Path(__file__).parent.parent.parent / ".env"
)

load_dotenv(ENV_LOCATION)
