import os

from cilantro.logger.base import get_logger
log = get_logger("INIT TEST")
log.critical("XYZ@@@@")
if os.getenv('HOST_IP'):
    # import seneca
    # log.critical("BEFORE seneca file: {}".format(seneca.__file__))

    # log.important("uninstall seneca pip")
    # os.system("pip3 uninstall seneca")
    import sys
    log.important("sys path before append: {}".format(sys.path))
    # sys.path.append("/app/venv/lib/python3.6/site-packages/seneca")
    sys.path.insert(0, "/app/venv/lib/python3.6/site-packages")
    # sys.path = ["/app/venv/lib/python3.6/site-packages", "/app"]
    # log.critical("Hopefully starting virtual env....")
    log.important("sys path after append: {}".format(sys.path))
    # os.system("/app/venv/bin/activate")

    import seneca
    log.critical("AFTER seneca file: {}".format(seneca.__file__))
else:
    log.critical("NOT SOURCING VENV!!!")

from decimal import getcontext
import sys
import hashlib
from os.path import dirname, abspath
from cilantro.constants.system_config import DECIMAL_PRECISION

import cython
# if cython.compiled: print("Yep, I'm compiled.")
# else: print("Just a lowly interpreted script.")

os.environ['LOCAL_PATH'] = abspath(dirname(dirname(dirname(__file__))))

# Add /messages/capnp to Python path. We need these loaded for capnp magic imports
sys.path.append(os.path.dirname(__file__) + '/messages/capnp')

# Set the decimal precision for floating point arithmetic
getcontext().prec = DECIMAL_PRECISION
