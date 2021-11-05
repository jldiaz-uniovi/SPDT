import copy
from dataclasses import dataclass, field
import math
from typing import Any, Optional, Tuple
from functools import lru_cache

from .model import BootShutDownTime, Const, ContainersConfig, Error, InstancesBootShutdownTime, Limit_, MSCCompleteSetting, MSCSimpleSetting, MaxServiceCapacity, PerformanceProfile
from .run import log


@dataclass
class PerformanceProfileDAO:
    store: list[PerformanceProfile]
    containers_config_cache: dict[Tuple[float, float, float], list[ContainersConfig]] = field(default_factory=dict)

    # LATER: Use mongodb instead of fake storage
    def FindByLimitsAndReplicas(self, cores: float, memory: float, replicas: int) -> Tuple[PerformanceProfile, Error]:
        def filter(x:PerformanceProfile) -> bool:
            return (x.Limit.CPUCores == cores and
                x.Limit.MemoryGB == memory and
                any(v.Replicas == replicas for v in x.MSCSettings)
            )
        result = [x for x in self.store if filter(x)]
        if not result:
            return PerformanceProfile(), Error(f"not found any PerformanceProfile for cores={cores}, memory={memory}, replicas={replicas}")
        result_copy = copy.deepcopy(result[0])
        result_copy.MSCSettings = [m for m in result_copy.MSCSettings if m.Replicas == replicas]
        return result_copy, Error()
        """	
        var performanceProfile types.PerformanceProfile
        err := p.db.C(p.Collection).Find(bson.M{
            "limits.cpu_cores" : cores,
            "limits.mem_gb" : memory,
            "mscs": bson.M{"$elemMatch": bson.M{"replicas":replicas}}}).
            Select(bson.M{"_id": 1, "limits":1, "mscs.$":1}).One(&performanceProfile)
        return performanceProfile,err
        """

    def FindProfileByLimits(self, limit: Limit_) -> Tuple[PerformanceProfile, Error]:
        def filter(x: PerformanceProfile):
            return (x.Limit.CPUCores == limit.CPUCores and
                    x.Limit.MemoryGB == limit.MemoryGB)
        result = [x for x in self.store if filter(x)]
        if not result:
            return PerformanceProfile(), Error(f"not found any PerformanceProfile for Limit_(cores={limit.CPUCores}, memory={limit.MemoryGB})")
        return result[0], Error()        
        """
        var performanceProfile types.PerformanceProfile
        err := p.db.C(p.Collection).Find(bson.M{
            "limits.cpu_cores" : limit.CPUCores,
            "limits.mem_gb" : limit.MemoryGB}).One(&performanceProfile)
        return performanceProfile,err
        """

    def UpdateById(self, id: str, performanceProfile: PerformanceProfile) -> Error:
        found = None
        for i, p in enumerate(self.store):
            if p.ID == id:
                found = i
                break
        if not found:
            return Error(f"Not found any PerformanceProfile with ID={id}")
        self.store[i] = performanceProfile
        return Error()  # No error
        """	
        err := p.db.C(p.Collection).
        Update(bson.M{"_id":id},performanceProfile)
        return err
        """

    # storage/profile_storage.go:132
    def FindAllUnderLimits(self, cores: float, memory: float) -> Tuple[list[PerformanceProfile], Error]:
        """/*
            Bring limits for which are profiles available
            in:
                @cores float64
                @memory float64
            out:
                @ContainersConfig []types.ContainersConfig
                @error
        */
        """
        result = [x for x in self.store 
            if x.Limit.CPUCores<=cores and x.Limit.MemoryGB <= memory]
        if result:
            # log.debug(f"FillAllUnderLimits({cores=}, {memory=}) returns {result}")
            log.info(f"FillAllUnderLimits({cores=}, {memory=}) returns {len(result)} of {len(self.store)} results")
            return result, Error()
        else:
            return result, Error(f"No results found for ({cores=}, {memory=})")


    def MatchProfileFitLimitsOver(self, cores: float, memory: float, requests: float) -> Tuple[list[ContainersConfig], Error]:
        """/*
            Matches the profiles  which fit into the specified limits and that provide a MSCPerSecond greater or equal than
            than the number of requests needed
            in:
                @requests float64
            out:
                @ContainersConfig []types.ContainersConfig
                @error
        */
        """
        # log.info(f"({cores=}, {memory=}, {requests=})")
        if (cores, memory, requests) in self.containers_config_cache:
            log.info("Cache hit")
            return self.containers_config_cache[(cores, memory, requests)], Error()

        # Query
        result: list[PerformanceProfile] = [x for x in self.store 
            if x.Limit.CPUCores<cores and x.Limit.MemoryGB < memory]
        if not result:
            msg = f"No results for MatchProfileLimitsOver({cores=}, {memory=}, {requests=})"
            log.warning(msg)
            return [], Error(msg)

        # Unwind msc, by creating a list of PerformanceProfile whose MSCSettings is a single item
        # instead of a sublist, and filter those which can give enouth MSC
        aux: list[PerformanceProfile] = [
            PerformanceProfile(
                ID=x.ID,
                MSCSettings=[msc],
                Limit=x.Limit
            ) for x in result for msc in x.MSCSettings if msc.MSCPerSecond >= requests
        ]
        # sort
        result = sorted(aux, key=lambda x: (x.Limit.CPUCores, x.Limit.MemoryGB, x.MSCSettings[0].Replicas, x.MSCSettings[0].MSCPerSecond))

        # Create list of ContainersConfig to return
        to_return:list[ContainersConfig] = [
            ContainersConfig(
                Limits=x.Limit, 
                MSCSetting=x.MSCSettings[0],
                )
            for x in result
        ]
        self.containers_config_cache[(cores, memory, requests)] = to_return
        # if cores==2 and memory==8 and 9.2<requests<9.3:
        #     log.info(f"MatchProfileLimitsOver({cores=}, {memory=}, {requests=}) found {len(to_return)} results")
        #     log.info(f"The 5 first ones are {to_return[:5]}")
        return to_return, Error()
        """
        var result []types.ContainersConfig
        query := []bson.M{
            bson.M{ "$match" : bson.M{"limits.cpu_cores" : bson.M{"$lt": cores}, "limits.mem_gb" : bson.M{"$lt":memory}}},
            bson.M{"$unwind": "$mscs" },
            bson.M{"$match": bson.M{"mscs.maximum_service_capacity_per_sec":bson.M{"$gte": requests}}},
            bson.M{"$sort": bson.M{"limits.cpu_cores":1, "limits.mem_gb":1, "mscs.replicas":1, "mscs.maximum_service_capacity_per_sec": 1}}}
        err := p.db.C(p.Collection).Pipe(query).All(&result)
        if len(result) == 0 {
            return result, errors.New("No result found")
        }
        return result, err
        """

performanceProfileDAO:PerformanceProfileDAO = None

def GetPerformanceProfileDAO(serviceName: str) -> PerformanceProfileDAO:
    # LATER: this is related to database connections
    global performanceProfileDAO
    from . import mock_storage
    if performanceProfileDAO is None:
        performanceProfileDAO = PerformanceProfileDAO(mock_storage.storedPerformanceProfiles)
    return performanceProfileDAO

    """
    if PerformanceProfileDB == nil {
        PerformanceProfileDB = &PerformanceProfileDAO {
            Database:DEFAULT_DB_PROFILES,
            Collection:DEFAULT_DB_COLLECTION_PROFILES + "_" + serviceName,
        }
        _,err := PerformanceProfileDB.Connect()
        if err != nil {
            log.Error("Error connecting to Profiles database "+err.Error())
        }
    } else if PerformanceProfileDB.Collection != DEFAULT_DB_COLLECTION_PROFILES + "_" + serviceName {
        PerformanceProfileDB = &PerformanceProfileDAO {
            Database:DEFAULT_DB_PROFILES,
            Collection:DEFAULT_DB_COLLECTION_PROFILES + "_" + serviceName,
        }
        _,err := PerformanceProfileDB.Connect()
        if err != nil {
            log.Error("Error connecting to Profiles database "+err.Error())
        }
    }
    return PerformanceProfileDB
    """

# rest_clients/performance_profiles/client.go:59
def GetPredictedReplicas(endpoint: str, appName: str, appType: str, mainServiceName: str,
              msc: float, cpuCores: float, memGb: float) -> Tuple[MSCCompleteSetting, Error]:

    # TODO: this is related to an external API which cannot be mocked 
    # because no json data is provided

    # However, since the goal is to find a MSCCompleteSetting which can give the required msc
    # it can be faked via a formula

    # The current implementation uses only the parameters:
    # - "mainServiceName" to locate performance metrics for that service in the database
    # - "cpuCores" and "memGb" to locate performance metrics for a deployment with 1 replica
    #   which uses those limits, for that service
    # - "msc" (which is the forecasted request rate)
    #
    # It ignores appName and appType. It simply divides the expected rate between the MSCs given
    # for the replica found for the given limits,  to find out the required number of replicas
    # 
    # It returns the MSCCompleteSettings which includes the computed number of replicas,
    # and that fakes the remaining data (boot time, msc, stdboot, etc.) from the one
    # found in the database for replicas=1

    serviceProfileDAO = GetPerformanceProfileDAO(mainServiceName)
    performanceProfileBase,_ = serviceProfileDAO.FindByLimitsAndReplicas(cpuCores, memGb, 1)
    mscSettings = performanceProfileBase.MSCSettings[0]
    estimatedReplicas = int(math.ceil(msc / mscSettings.MSCPerSecond))
    result = MSCCompleteSetting(
        Replicas=estimatedReplicas,
        BootTimeMs=mscSettings.BootTimeSec*1000,
        MSCPerSecond=MaxServiceCapacity(RegBruteForce=mscSettings.MSCPerSecond),
        MSCPerMinute=MaxServiceCapacity(RegBruteForce=mscSettings.MSCPerSecond*60),
        StandDevBootTimeMS=mscSettings.StandDevBootTimeSec
        )
    errmsg = (f"GetPredictedReplicas({endpoint=}, {appName=}, {appType=}, "
              f"{mainServiceName=}, {msc=}, {cpuCores=}, {memGb=}) **making up the answer** {result=}")
    log.debug(errmsg)
    return result , Error() # No error

    """
    mscSetting = MSCCompleteSetting()
    parameters = {}
    parameters["apptype"] = appType
    parameters["appname"] = appName
    parameters["mainservicename"] = mainServiceName
    parameters["msc"] = strconv.FormatFloat(msc, 'f', 1, 64)
    parameters["numcoresutil"] = strconv.FormatFloat(cpuCores, 'f', 1, 64)
    parameters["numcoreslimit"] = strconv.FormatFloat(cpuCores, 'f', 1, 64)
    parameters["nummemlimit"] = strconv.FormatFloat(memGb, 'f', 1, 64)

    # endpoint = util.ParseURL(endpoint, parameters)

    response, err := http.Get(endpoint)
    if err != nil {
        return mscSetting,err
    }
    defer response.Body.Close()
    data, err := ioutil.ReadAll(response.Body)
    if err != nil {
        return mscSetting,err
    }
    err = json.Unmarshal(data, &mscSetting)
    if err != nil {
        return mscSetting,err
    }
    return mscSetting,err
    """    



@dataclass
class VMBootingProfileDAO:
    Database: str
    Collection: str
    store: list[InstancesBootShutdownTime]

    def BootingShutdownTime(self, vmType:str, n:int) -> Tuple[BootShutDownTime, Error]:
        # LATER: query mongo database
        for instance in self.store:
            if instance.VMType == vmType:
                for bootShutdown in instance.InstancesValues:
                    if bootShutdown.NumInstances == n:
                        return bootShutdown, Error() # No error
        
        return BootShutDownTime(), Error(f"Not found BootShutDownTime for {vmType} and {n} replicas")

    def FindByType(self, vmType: str) -> Tuple[InstancesBootShutdownTime, Error]:
        for i in self.store:
            if i.VMType == vmType:
                return i, Error()
        return InstancesBootShutdownTime(), Error("not found")

    def UpdateByType(self, vmType:str, vmBootingProfile: InstancesBootShutdownTime) -> Error:
        for index, instance in enumerate(self.store):
            if instance.VMType == vmType:
                self.store[index] = vmBootingProfile
                return Error()
        return Error(f"{vmType} not found")                

VMBootingProfileDB: Optional[VMBootingProfileDAO] = None

def GetVMBootingProfileDAO() -> VMBootingProfileDAO:
    # LATER: this is related to database connections
    from . import mock_storage
    global VMBootingProfileDB
    if VMBootingProfileDB is None:
        VMBootingProfileDB = VMBootingProfileDAO(
            Database = Const.DEFAULT_DB_PROFILES.value,
            Collection = Const.DEFAULT_DB_COLLECTION_VM_PROFILES.value,
            store=mock_storage.storedVmBootingProfiles
        )
    return VMBootingProfileDB

