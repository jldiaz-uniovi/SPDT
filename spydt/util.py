from datetime import datetime
from .model import Component, ForecastComponent_, ScalingHorizon_, SystemConfiguration, Error
import yaml
import json
from typing import Tuple

def ReadConfigFile(configFile: str) -> Tuple[SystemConfiguration, Error]:
    """//Method that parses the configuration file into a struct type"""
    try:
        with open(configFile) as f:
            y_data = yaml.load(f, Loader=yaml.BaseLoader)
        j = json.dumps(y_data)
        sysconf = SystemConfiguration.from_json(j) # type: ignore
        return sysconf, Error("")
    except Exception as e:
        print(f"There was a problem reading the configuration file: {e}")
        return SystemConfiguration(), Error(f"{e}")
