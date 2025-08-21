#!/bin/env python
import sys
from logging import ERROR, basicConfig

from common import BeforeConnect

basicConfig(level=ERROR)

sys.exit(BeforeConnect().run())
