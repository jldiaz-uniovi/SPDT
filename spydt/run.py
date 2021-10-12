# Contains the "commands" that start the policy derivation
from datetime import datetime
from typing import Tuple

from spydt.policy import Policies, SelectPolicy

from .model import Error, Forecast, Policy, SystemConfiguration, VmProfile
from .util import ReadConfigFile
from .mock_storage import (
    FetchApplicationProfile, 
    fetchForecast,
    ReadVMProfiles,
    FetchVMBootingProfiles,
    updateForecastInDB
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

    # Populate Performance Profiles from external API (mocked from json)
    # and store it in mongo (also mocked, stored in global var)
    error = FetchApplicationProfile(sysConfiguration)
    if error.error:
        return Policy(),error

    # Request Forecasting from external API (mocked from json)
    forecast, err = fetchForecast(sysConfiguration, timeStart, timeEnd)
    if err.error:
        return Policy(), err
    
    
    # Get VM Profiles from json file
    vmProfiles, err = ReadVMProfiles()
    if err.error:
        return Policy(), err
    
    
    # Populate VM Booting Profiles from external API (mocked from json)
    # and store it in mongo (also mocker, stored in global var)
    err = FetchVMBootingProfiles(sysConfiguration, vmProfiles)
    if err.error:
        return Policy(), err


    # Store forecast in Mongo (mocked in global var)
    updateForecastInDB(forecast, sysConfiguration)  # LATER: does not subscribe

    # LATER: retrieve existing policies. Currently no policies are stored
    """
    policyDAO = GetPolicyDAO(mainService)
    storedPolicy, err = policyDAO.FindSelectedByTimeWindow(timeStart, timeEnd)
    """

    if True: # If previous lines do not find any policy....
        selectedPolicy, err = setNewPolicy(forecast, sysConfiguration, vmProfiles)
        # ScheduleScaling(sysConfiguration, selectedPolicy)  # TODO
    else:
        pass
        """
        shouldUpdate = ValidateMSCThresholds(forecast,storedPolicy, sysConfiguration)
        if shouldUpdate:
            InvalidateOldPolicies(sysConfiguration, timeStart, timeEnd )
            selectedPolicy, err = setNewPolicy(forecast, sysConfiguration, vmProfiles)
            ScheduleScaling(sysConfiguration, selectedPolicy)
            if err.error:
                return Policy(), err
        """
    return selectedPolicy, err
    
# server/start.go:223
def setNewPolicy(forecast: Forecast, sysConfiguration: SystemConfiguration, vmProfiles: list[VmProfile]) -> Tuple[Policy, Error]:
    """//Start Derivation of a new scaling policy for the specified scaling horizon and correspondent forecast"""
    # //timeStart := forecast.TimeWindowStart
    # //timeEnd := forecast.TimeWindowEnd

    # // Get VM Profiles
    err = Error()
    selectedPolicy = Policy()


    # //Derive Strategies
    # log.Info("Start policies derivation")
    policies,err = Policies(vmProfiles, sysConfiguration, forecast)
    if err.error:
        return selectedPolicy, err
    
    # log.Info("Finish policies derivation")
    # log.Info("Start policies evaluation")
    # var err error
    '''
    selectedPolicy, err = SelectPolicy(policies, sysConfiguration, vmProfiles, forecast)
    if err.error:
        print(f"Error evaluation policies: {err.error}")
    else:
        # log.Info("Finish policies evaluation")
        # LATER: store policies in mongo
        """
        policyDAO = storage.GetPolicyDAO(sysConfiguration.MainServiceName)
        for _,p := range policies {
            err = policyDAO.Insert(p)
            if err != nil {
                log.Error("The policy with ID = %s could not be stored. Error %s\n", p.ID, err)
            }
        }
        """
    '''
    return  selectedPolicy, err



if __name__ == "__main__":
    p, e = StartPolicyDerivation(datetime.now(), datetime.now(), SystemConfiguration())
    print(e)
    print(p)