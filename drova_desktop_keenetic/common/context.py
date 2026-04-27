from dataclasses import dataclass

from asyncssh import SFTPClient, SSHClientConnection

from drova_desktop_keenetic.common.config import Config
from drova_desktop_keenetic.common.drova import ProductInfo, SessionsEntity


@dataclass
class SessionHandlerContext:
    config: Config
    ssh: SSHClientConnection | None
    sftp: SFTPClient | None

    session: SessionsEntity | None = None
    product: ProductInfo | None = None
