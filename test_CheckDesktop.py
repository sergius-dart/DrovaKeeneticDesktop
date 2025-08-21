import os

from paramiko import AutoAddPolicy, SSHClient

from common import WINDOWS_HOST, WINDOWS_LOGIN, WINDOWS_PASSWORD, CheckDesktop

client = SSHClient()
client.set_missing_host_key_policy(AutoAddPolicy())
client.connect(os.environ[WINDOWS_HOST], username=os.environ[WINDOWS_LOGIN], password=os.environ[WINDOWS_PASSWORD])

print(CheckDesktop().exec(client))
