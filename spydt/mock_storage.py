from datetime import datetime
from typing import Tuple
from .model import ( 
    SystemConfiguration, 
    Error, 
    Forecast
    )



# server/start.go:180
def FetchApplicationProfile(sysConfiguration: SystemConfiguration) -> Error:
    """//Fetch the performance profile of the microservice that should be scaled"""
    # TODO: Read it from database
    # The original code apparently fetched the data from some external API and
    # stored the result in Mongo, but no data was returned from this function
    err = Error()
    return err

    # Original go code
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
