from datetime import datetime
from .model import Error, State, StateToSchedule
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

storedPerformanceProfiles: list[PerformanceProfile] = []

# server/start.go:180
def FetchApplicationProfile(sysConfiguration: SystemConfiguration) -> Error:
    """//Fetch the performance profile of the microservice that should be scaled"""
    # TODO: Store in database. Currently stores in a global variable
    if storedPerformanceProfiles:
        return Error() # No error. Already stored. Do nothing
    
    try:
        with open("tests_mock_input/performance_profiles_test.json") as f:
            data = f.read()
        servicePerformanceProfile: ServicePerformanceProfile = ServicePerformanceProfile.schema().loads(data) # type: ignore

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


storedVmBootingProfiles: list[InstancesBootShutdownTime] = []


# server/start.go:156
def FetchVMBootingProfiles(sysConfiguration: SystemConfiguration, vmProfiles: list[VmProfile]) -> Error:
    # TODO: Populate database. Currently stores all in a global var
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
            print(f"Error in request VM Booting Profile for type {vm.Type}: {e}")  # TODO: log
    return err


storedForecast: list[Forecast] = []

def updateForecastInDB(forecast: Forecast, sysConfiguration: SystemConfiguration) -> Error:
    """Updates the forecast in mongo database (mocked, uses global vars)"""
    timeStart = forecast.TimeWindowStart
    timeEnd = forecast.TimeWindowEnd
    mainService = sysConfiguration.MainServiceName

    # TODO: find forecast by time window
    """
    //Retrieve data access to the database for forecasting
    forecastDAO := storage.GetForecastDAO(mainService)
    //Check if already exist, then update
    resultQuery,err := forecastDAO.FindOneByTimeWindow(timeStart, timeEnd)
    """
    
    if not storedForecast:
        # If it is not already stored
        forecast.IDdb = "arbitrary bson value"  # TODO
        storedForecast.append(forecast)
    else:
        # TODO
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
    ...  # TODO
    return State(), Error()
    """
    policyState = State()
    stateScheduled, _ := scheduler.InfraCurrentState(endpoint)
    mapServicesScheduled := stateScheduled.Services
    policyServices := make(map[string]types.ServiceInfo)

    for k,v := range mapServicesScheduled {
        mem := memBytesToGB(v.Memory)
        cpu := stringToCPUCores(v.CPU)
        replicas := v.Scale
        policyServices[k] = types.ServiceInfo{
            Memory:mem,
            CPU:cpu,
            Scale:replicas,
        }
    }

    policyState = types.State {
        VMs:stateScheduled.VMs,
        Services:policyServices,
    }
    return policyState,nil
    """




def InfraCurrentState(endpoint: str) -> Tuple[StateToSchedule, Error]:
    ... # TODO
    return StateToSchedule(), Error()
    """
    currentState := StateToSchedule{}
    infrastructureState := InfrastructureState{}
    response, err := http.Get(endpoint)
    if err != nil {
        return currentState, err
    }

    defer response.Body.Close()
    data, err := ioutil.ReadAll(response.Body)
    if err != nil {
        return  currentState, err
    }
    err = json.Unmarshal(data, &infrastructureState)
    if err != nil {
        return  currentState, err
    }
    currentState = infrastructureState.ActiveState
    return  currentState, err
    """
