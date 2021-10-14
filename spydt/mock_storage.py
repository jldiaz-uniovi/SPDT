from datetime import datetime
from typing import Tuple
import logging
from bson.objectid import ObjectId  # type: ignore

from spydt.aux_func import (MillisecondsToSeconds, memBytesToGB,
                            stringToCPUCores)

from .model import (Error, Forecast, InfrastructureState,
                    InstancesBootShutdownTime, MSCSimpleSetting,
                    PerformanceProfile, Service, ServiceInfo,
                    ServicePerformanceProfile, State, StateToSchedule,
                    SystemConfiguration, VmProfile)


log = logging.getLogger("spydt")

storedPerformanceProfiles: list[PerformanceProfile] = []

# server/start.go:180
def FetchApplicationProfile(sysConfiguration: SystemConfiguration) -> Error:
    """//Fetch the performance profile of the microservice that should be scaled"""
    # LATER: Store in database. Currently stores in a global variable
    if storedPerformanceProfiles:
        return Error() # No error. Already stored. Do nothing
    
    try:
        # LATER: Use REST API to retrieve info
        with open("tests_mock_input/performance_profiles_test.json") as f:
            data = f.read()
        servicePerformanceProfile: ServicePerformanceProfile = ServicePerformanceProfile.schema().loads(data) # type: ignore

    except Exception as e:
        log.error(f"Error in request Performance Profiles: {e}")
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
            ID=str(ObjectId()),
            Limit=p.Limits,
            MSCSettings=mscSettings
        )
        storedPerformanceProfiles.append(performanceProfile)
    return Error()


def fetchForecast(sysConfiguration: SystemConfiguration, timeStart: datetime, timeEnd: datetime) -> Tuple[Forecast, Error]:
    # LATER: Read from external API
    # Currently an example JSON is used as data source
    try:
        with open("tests_mock_input/mock_forecast_test.json") as f:
            forecast = Forecast.schema().loads(f.read()) # type:ignore
    except Exception as e:
        return Forecast(), Error(f"Unable to read JSON forecast: {e}")
    # log.debug(f"Forecast -> {forecast}")
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
        log.error(e)
        err.error = f"{e}"
    vmProfiles.sort(key=lambda x: x._Pricing.Price)
    return vmProfiles, err


storedVmBootingProfiles: list[InstancesBootShutdownTime] = []


# server/start.go:156
def FetchVMBootingProfiles(sysConfiguration: SystemConfiguration, vmProfiles: list[VmProfile]) -> Error:
    # LATER: Populate database. Currently stores all in a global var
    # Currently an example JSON is used as data source
    global storedVmBootingProfiles
    err = Error()
    if storedVmBootingProfiles:
        return err
    
    for vm in vmProfiles:
        try:
            with open("tests_mock_input/mock_vms_all_times.json") as f:
                data = f.read()
            vmBootingProfile: InstancesBootShutdownTime = InstancesBootShutdownTime.schema().loads(data)  # type: ignore
            vmBootingProfile.VMType = vm.Type
            storedVmBootingProfiles.append(vmBootingProfile)
        except Exception as e:
            err.error = f"{e}"
            log.error(f"Error in request VM Booting Profile for type {vm.Type}: {e}")
    return err


storedForecast: list[Forecast] = []

def updateForecastInDB(forecast: Forecast, sysConfiguration: SystemConfiguration) -> Error:
    """Updates the forecast in mongo database (mocked, uses global vars)"""
    timeStart = forecast.TimeWindowStart
    timeEnd = forecast.TimeWindowEnd
    mainService = sysConfiguration.MainServiceName

    # LATER: find forecast by time window
    """
    //Retrieve data access to the database for forecasting
    forecastDAO := storage.GetForecastDAO(mainService)
    //Check if already exist, then update
    resultQuery,err := forecastDAO.FindOneByTimeWindow(timeStart, timeEnd)
    """
    
    if not storedForecast:
        # If it is not already stored
        forecast.IDdb = str(ObjectId())
        storedForecast.append(forecast)
    else:
        # LATER
        """
        id := resultQuery.IDdb
        forecast.IDdb = id
        if resultQuery.IDPrediction != forecast.IDPrediction {
            subscribeForecastingUpdates(sysConfiguration, forecast.IDPrediction)
        }
        forecastDAO.Update(id, forecast)
        """
    return Error()



def RetrieveCurrentState(endpoint: str ) -> Tuple[State, Error]:
    policyState = State()
    stateScheduled, e = InfraCurrentState(endpoint)
    if e.error:
        log.error(f"InfraCurrentState() returned error '{e.error}'")
    mapServicesScheduled = stateScheduled.Services
    policyServices: Service = Service({})

    for k, v in mapServicesScheduled.items():
        mem = memBytesToGB(v.Memory)
        cpu = stringToCPUCores(v.CPU)
        replicas = v.Scale
        policyServices[k] = ServiceInfo(
            Memory=mem,
            CPU=cpu,
            Scale=replicas,
        )

    policyState = State(
        VMs = stateScheduled.VMs,
        Services = policyServices,
    )
    return policyState, Error()





def InfraCurrentState(endpoint: str) -> Tuple[StateToSchedule, Error]:
    # LATER: Use REST API to retrieve info
    currentState = StateToSchedule()
    infrastructureState = InfrastructureState()
    try:
        with open("tests_mock_input/mock_current_state.json") as f:
            data = f.read()
            infrastructureState = InfrastructureState.schema().loads(data)  # type: ignore
    except Exception as e:
        # raise
        return currentState, Error(f"{e}")

    log.debug(f"Infrastructure current state={infrastructureState}")
    currentState = infrastructureState.ActiveState
    return currentState, Error()
