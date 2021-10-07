# Contains the "commands" that start the policy derivation
from datetime import datetime
from typing import Tuple

from .model import Error, Forecast, ForecastedValue, Policy, SystemConfiguration
from .util import ReadConfigFile

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
    
    """
    # Get VM Profiles
    vmProfiles, err = ReadVMProfiles()
    if err.error:
        return Policy(), err
    
    # Get VM booting Profiles
    err = FetchVMBootingProfiles(sysConfiguration, vmProfiles)
    if err.error:
        return Policy(), err

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
    
# server/start.go:180
def FetchApplicationProfile(sysConfiguration: SystemConfiguration) -> Error:
    """//Fetch the performance profile of the microservice that should be scaled"""
    # WIP: mocked. TODO: Read it from database
    # The original code apparently fetched the data from some external API and
    # stored the result in Mongo, but no data was returned from this function
    err = Error()
    return err
    """
    servicePerformanceProfile: ServicePerformanceProfile
    serviceProfileDAO := storage.GetPerformanceProfileDAO(sysConfiguration.MainServiceName)
    storedPerformanceProfiles,_ := serviceProfileDAO.FindAll()
    if len(storedPerformanceProfiles) == 0 {

        log.Info("Start request Performance Profiles")
        endpoint := sysConfiguration.PerformanceProfilesComponent.Endpoint + util.ENDPOINT_SERVICE_PROFILES
        servicePerformanceProfile, err = Pservice.GetServicePerformanceProfiles(endpoint,sysConfiguration.AppName,
                                                                sysConfiguration.AppType, sysConfiguration.MainServiceName)

        if err != nil {
            log.Error("Error in request Performance Profiles: %s",err.Error())
        } else {
            log.Info("Finish request Performance Profiles")
        }

        //Selects and stores received information about Performance Profiles
        for _,p := range servicePerformanceProfile.Profiles {
            mscSettings := []types.MSCSimpleSetting{}
            for _,msc := range p.MSCs {
                setting := types.MSCSimpleSetting{
                    BootTimeSec: util.MillisecondsToSeconds(msc.BootTimeMs),
                    MSCPerSecond: msc.MSCPerSecond.RegBruteForce,
                    Replicas: msc.Replicas,
                    StandDevBootTimeSec: util.MillisecondsToSeconds(msc.StandDevBootTimeMS),
                }
                mscSettings = append(mscSettings, setting)
            }
            performanceProfile := types.PerformanceProfile {
                ID: bson.NewObjectId(),Limit: p.Limits, MSCSettings: mscSettings,
            }
            err = serviceProfileDAO.Insert(performanceProfile)
            if err != nil {
                log.Error("Error Storing Performance Profiles: %s",err.Error())
            }
        }
    }
    return err
    """

def fetchForecast(sysConfiguration: SystemConfiguration, timeStart: datetime, timeEnd: datetime) -> Tuple[Forecast, Error]:
    # TODO: Read from database
    # Currently an example JSON is used as data source
    try:
        with open("tests_mock_input/mock_forecast_test.json") as f:
            forecast = Forecast.from_json(f.read()) # type:ignore
    except Exception as e:
        return Forecast(), Error(f"Unable to read JSON forecast: {e}")
    return forecast, Error()

if __name__ == "__main__":
    r = ReadConfigFile("config.yml")
    print(r)