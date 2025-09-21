import os
from logging import DEBUG, INFO, StreamHandler, basicConfig
from logging.handlers import RotatingFileHandler

from drova_desktop_keenetic.common.contants import WINDOWS_HOST

assert WINDOWS_HOST in os.environ, "Need windows host in config env"


log_format = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
date_format = "%Y-%m-%d %H:%M:%S"
ch = StreamHandler()
handler_rotating = RotatingFileHandler(f"app.{os.environ[WINDOWS_HOST]}.log", maxBytes=1024 * 1024, backupCount=5)


basicConfig(level=INFO, handlers=(handler_rotating, ch), format=log_format, datefmt=date_format)
