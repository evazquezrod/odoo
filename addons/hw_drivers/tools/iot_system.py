
from enum import Enum, unique
from functools import cache
import logging
import platform

_logger = logging.getLogger(__name__)


@unique
class IoTSystem(Enum):
    TEST = 'T'
    IOT_BOX = 'L'
    WINDOWS = 'W'

    @classmethod
    @cache
    def get_all_value(cls):
        """
        Return all names of the enum as a tuple.
        """
        return (item.value for item in cls)


def determine_iot_system():
    """
    Determine the IoT system based on the platform and environment variables.
    """
    if platform.system() == 'Windows':
        return IoTSystem.WINDOWS
    if 'rpi' in platform.release():  # same logic as in the iot requirement.txt
        return IoTSystem.IOT_BOX
    return IoTSystem.TEST


IOT_SYSTEM = determine_iot_system()
"""IoT system type detected for the current environment"""

IS_IOT_TEST = IOT_SYSTEM == IoTSystem.TEST
"""True if the IoT system is a test environment ->
any system which are not raspberry pi nor Windows"""
IS_IOT_BOX = IOT_SYSTEM == IoTSystem.IOT_BOX
IS_WINDOWS = IOT_SYSTEM == IoTSystem.WINDOWS

LOG_LEVEL = logging.WARNING if IS_IOT_TEST else logging.INFO
_logger.log(LOG_LEVEL, "Detected IoT system: %s (%s)", IOT_SYSTEM.name, IOT_SYSTEM.value)
