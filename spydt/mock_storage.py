from datetime import datetime
from .model import Error
from typing import Tuple

from spydt.aux_func import MillisecondsToSeconds
from .model import ( 
    InstancesBootShutdownTime,
    MSCSimpleSetting,
    PerformanceProfile,
    ServicePerformanceProfile,
    SystemConfiguration, 
    Error, 
    Forecast,
    VmProfile
    )

storedPerformanceProfiles: list[ServicePerformanceProfile] = []

# server/start.go:180
def FetchApplicationProfile(sysConfiguration: SystemConfiguration) -> Error:
    """//Fetch the performance profile of the microservice that should be scaled"""
    # TODO: Store in database. Currently stores in a global variable
    if storedPerformanceProfiles:
        return Error() # No error. Already stored. Do nothing
    
    try:
        with open("tests_mock_input/performance_profiles_test.json") as f:
            data = f.read()
        servicePerformanceProfile: ServicePerformanceProfile = ServicePerformanceProfile.schema().loads(data)

    except Exception as e:
        print(f"Error in request Performance Profiles: {e}")
        return Error(f"{e}")

    for p in servicePerformanceProfile.Profiles:
        mscSettings: list[MSCSimpleSetting] = []
        for msc in p.MSCs:
            setting = MSCSimpleSetting(
                BootTimeSec=MillisecondsToSeconds(msc.BootTimeMs),
                MSCPerSecond=msc.MSCPerSecond.RegBruteForce,
                Replicas=msc.Replicas,
                StandDevBootTimeSec=MillisecondsToSeconds(msc.StandDevBootTimeMS)
            )
            mscSettings.append(setting)
        performanceProfile = PerformanceProfile(
            ID="arbitrary_hash",
            Limit=p.Limits,
            MSCSettings=mscSettings
        )
        storedPerformanceProfiles.append(performanceProfile)
    return Error()


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


vmBootingProfiles = []


# server/start.go:156
def FetchVMBootingProfiles(sysConfiguration: SystemConfiguration, vmProfiles: list[VmProfile]) -> Error:
    # TODO: Populate database. Currently stores all in a global var
    # Currently an example JSON is used as data source
    global vmBootingProfiles
    err = Error()
    if vmBootingProfiles:
        return err
    
    for vm in vmProfiles:
        try:
            with open("tests_mock_input/mock_vms_all_times.json") as f:
                data = f.read()
            vmBootingProfile: InstancesBootShutdownTime = InstancesBootShutdownTime.schema().loads(data)  # type: ignore
            vmBootingProfile.VMType = vm.Type
            vmBootingProfiles.append(vmBootingProfile)
        except Exception as e:
            err.error = f"{e}"
            print(f"Error in request VM Booting Profile for type {vm.type}: {e}")  # TODO: log
    return err

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