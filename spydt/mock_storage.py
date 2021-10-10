from datetime import datetime
from typing import Tuple
from .model import ( 
    InstancesBootShutdownTime,
    SystemConfiguration, 
    Error, 
    Forecast,
    VmProfile
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


# server/start.go:134
def ReadVMProfiles()   -> Tuple[list[VmProfile], Error]:
    err = Error()
    vmProfiles: list[VmProfile] = []
    try:
        with open("vm_profiles.json") as f:
            data = f.read()
        vmProfiles = VmProfile.schema().loads(data, many=True)  # type: ignore
    except Exception as e:
        # print(e) # TODO: Log
        err.error = f"{e}"
    vmProfiles.sort(key=lambda x: x._Pricing.Price)
    return vmProfiles, err


# server/start.go:156
def FetchVMBootingProfiles(sysConfiguration: SystemConfiguration, vmProfiles: list[VmProfile]) -> Error:
    # TODO: Read from database
    # Currently an example JSON is used as data source
	err = Error()
	vmBootingProfile = InstancesBootShutdownTime()
    try:
        with open("tests_mock_input/mock_vms_all_times.json") as f:
            data = f.read()
            vmBootingProfile = VmProfile.schema().loads(data, many=True)  # type: ignore    except Exception as e:
        return Forecast(), Error(f"Unable to read JSON forecast: {e}")
    return Error()

    """
	vmBootingProfileDAO := storage.GetVMBootingProfileDAO()
	storedVMBootingProfiles,_ := vmBootingProfileDAO.FindAll()
	if len(storedVMBootingProfiles) == 0 {
		log.Info("Start request VM booting Profiles")
		endpoint := sysConfiguration.PerformanceProfilesComponent.Endpoint + util.ENDPOINT_ALL_VM_TIMES
		csp := sysConfiguration.CSP
		region := sysConfiguration.Region
		for _, vm := range vmProfiles {
			vmBootingProfile, err = Pservice.GetAllBootShutDownProfilesByType(endpoint, vm.Type, region, csp)
			if err != nil {
				log.Error("Error in request VM Booting Profile for type %s. %s",vm.Type, err.Error())
			}
			vmBootingProfile.VMType = vm.Type
			vmBootingProfileDAO.Insert(vmBootingProfile)
		}
		log.Info("Finish request VM booting Profiles")
	}
	return err
    """