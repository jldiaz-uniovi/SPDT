# Contains the "commands" that start the policy derivation
from datetime import datetime
from typing import Tuple

from .model import Error, Policy, SystemConfiguration
from .util import ReadConfigFile
from .mock_storage import (
    FetchApplicationProfile, 
    fetchForecast,
    ReadVMProfiles,
    FetchVMBootingProfiles
)

# cmd/cmd_derive_policy.go:23
# Heavily adapted: most command-line options are hardcoded
def derive ():
    configFile = "config.yml"
    sysConfiguration, err  = ReadConfigFile(configFile)
    if err.error:
        print(f"ERROR:{err.error}")
    else:
        print(f"Configuracion leida con éxito: {sysConfiguration}")
    
    timeStart = sysConfiguration.ScalingHorizon.StartTime
    timeEnd = sysConfiguration.ScalingHorizon.EndTime

    p, err = StartPolicyDerivation(timeStart,timeEnd,sysConfiguration)
    if err.error:
        print(f"An error has occurred and policies have been not derived. Please try again. Details: {err}")
    print(f"\nSUCESS: Policy={p}")
    
# server/pullForecast.go:16
def StartPolicyDerivation(timeStart: datetime, timeEnd: datetime, sysConfiguration: SystemConfiguration) -> Tuple[Policy, Error]:

    selectedPolicy = Policy()
    err = Error("")
    mainService = sysConfiguration.MainServiceName

    # Request Performance Profiles
    error = FetchApplicationProfile(sysConfiguration)  # Does nothing (TODO)
    if error.error:
        return Policy(),error

    # Request Forecasting
    forecast, err = fetchForecast(sysConfiguration, timeStart, timeEnd)
    if err.error:
        return Policy(), err
    
    
    # Get VM Profiles
    vmProfiles, err = ReadVMProfiles()
    if err.error:
        return Policy(), err
    
    
    # Get VM booting Profiles
    err = FetchVMBootingProfiles(sysConfiguration, vmProfiles)
    if err.error:
        return Policy(), err

    """
    updateForecastInDB(forecast, sysConfiguration)

    policyDAO = GetPolicyDAO(mainService)
    storedPolicy, err = policyDAO.FindSelectedByTimeWindow(timeStart, timeEnd)
    if err.error:
        selectedPolicy, err = setNewPolicy(forecast, sysConfiguration, vmProfiles)
        ScheduleScaling(sysConfiguration, selectedPolicy)
    else:
        shouldUpdate = ValidateMSCThresholds(forecast,storedPolicy, sysConfiguration)
        if shouldUpdate:
            InvalidateOldPolicies(sysConfiguration, timeStart, timeEnd )
            selectedPolicy, err = setNewPolicy(forecast, sysConfiguration, vmProfiles)
            ScheduleScaling(sysConfiguration, selectedPolicy)
            if err.error:
                return Policy(), err
    """       
    return selectedPolicy, err
    
if __name__ == "__main__":
    p, e = StartPolicyDerivation(datetime.now(), datetime.now(), SystemConfiguration())
    print(e)
    print(p)