#!/bin/env python
import sys
from logging import ERROR, basicConfig

from common import AfterDisconnect

basicConfig(level=ERROR)

sys.exit(AfterDisconnect().run())
