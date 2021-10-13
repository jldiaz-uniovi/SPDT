from datetime import datetime
import logging
from .model import Component, ForecastComponent_, ScalingHorizon_, SystemConfiguration, Error
import yaml
import json
from typing import Tuple

log = logging.getLogger("spydt")

def ReadConfigFile(configFile: str) -> Tuple[SystemConfiguration, Error]:
    """//Method that parses the configuration file into a struct type"""
    try:
        with open(configFile) as f:
            y_data = yaml.load(f, Loader=yaml.BaseLoader)
        j = json.dumps(y_data)
        sysconf = SystemConfiguration.schema().loads(j) # type: ignore
        return sysconf, Error("")
    except Exception as e:
        log.error(f"There was a problem reading the configuration file: {e}")
        return SystemConfiguration(), Error(f"{e}")
