# Contains the "commands" that start the policy derivation
import logging
from datetime import datetime
from typing import Tuple
from rich.logging import RichHandler

from .execute import TriggerScheduler
from .mock_storage import (FetchApplicationProfile, FetchVMBootingProfiles,
                           ReadVMProfiles, fetchForecast, updateForecastInDB)
from .model import Const, Error, Forecast, Policy, SystemConfiguration, VmProfile
from .policy import Policies, SelectPolicy
from .util import ReadConfigFile

log = logging.getLogger("spydt")
FORMAT = "%(funcName)20s ▶ %(message)s"
logging.basicConfig(format=FORMAT, datefmt='%H:%M:%S', handlers=[RichHandler()])
log.setLevel(logging.DEBUG)


# cmd/cmd_derive_policy.go:23
# Heavily adapted: most command-line options are hardcoded
def derive ():
    configFile = "config.yml"
    sysConfiguration, err  = ReadConfigFile(configFile)
    if err.error:
        log.error(f"ERROR:{err.error}")
    else:
        log.debug(f"Configuracion leida con éxito: {sysConfiguration}")
    
    timeStart = sysConfiguration.ScalingHorizon.StartTime
    timeEnd = sysConfiguration.ScalingHorizon.EndTime

    p, err = StartPolicyDerivation(timeStart,timeEnd,sysConfiguration)
    if err.error:
        log.error(f"An error has occurred and policies have been not derived. Please try again. Details: {err.error}")
    log.debug(f"SUCESS: Policy={p}")
    
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

    err = Error("no existing policies")
    if err.error: # If previous lines do not find any policy....
        selectedPolicy, err = setNewPolicy(forecast, sysConfiguration, vmProfiles)
        ScheduleScaling(sysConfiguration, selectedPolicy)
    else:
        log.warning("NOT IMPLEMENTED, invalidate old policy")
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
    log.info("Start policies derivation")
    policies, err = Policies(vmProfiles, sysConfiguration, forecast)
    if err.error:
        log.error(f"Policies() returned error '{err.error}'")
        return selectedPolicy, err
    
    log.info("Finish policies derivation")
    log.info("Start policies evaluation")
    selectedPolicy, err = SelectPolicy(policies, sysConfiguration, vmProfiles, forecast)
    if err.error:
        log.error(f"Error evaluation policies: {err.error}")
    else:
        log.info("Finish policies evaluation")
        log.warning("setNewPolicy() INCOMPLETE. Not storing generated policy in MongoDB")
        # LATER: store policies in mongo
        """
        policyDAO = storage.GetPolicyDAO(sysConfiguration.MainServiceName)
        for _,p := range policies {
            err = policyDAO.Insert(p)
            if err != nil {
                log.error(f"The policy with ID = {p.ID} could not be stored. Error {err.error}")
            }
        }
        """
    return  selectedPolicy, err


# server/start.go:259
def ScheduleScaling(sysConfiguration: SystemConfiguration, selectedPolicy:Policy):
    log.info("Start request Scheduler")
    schedulerURL = sysConfiguration.SchedulerComponent.Endpoint + Const.ENDPOINT_STATES.value
    tset, err = TriggerScheduler(selectedPolicy, schedulerURL)
    if err.error:
        log.error(f"The scheduler request failed with error '{err.error}'")
    else:
        log.info("Finish request Scheduler")

if __name__ == "__main__":
    derive()
