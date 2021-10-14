from dataclasses import dataclass
import copy
from .model import (
    PerformanceProfile, Error, Limit_, MSCCompleteSetting
)
from typing import Tuple

@dataclass
class PerformanceProfileDAO:
    store: list[PerformanceProfile]

    # LATER: Use mongodb instead of fake storage
    def FindByLimitsAndReplicas(self, cores: float, memory: float, replicas: int) -> Tuple[PerformanceProfile, Error]:
        def filter(x:PerformanceProfile):
            return (x.Limit.CPUCores == cores and
                x.Limit.MemoryGB == memory and
                any(v.Replicas == replicas for v in x.MSCSettings)
            )
        result = [x for x in self.store if filter(x)]
        if not result:
            return PerformanceProfile(), Error(f"not found any PerformanceProfile for cores={cores}, memory={memory}, replicas={replicas}")
        result = copy.deepcopy(result[0])
        result.MSCSettings = [m for m in result.MSCSettings if m.Replicas == replicas]
        return result, Error()
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


def GetPerformanceProfileDAO(serviceName: str) -> PerformanceProfileDAO:
    # LATER: this is related to database connections
    from .mock_storage import storedPerformanceProfiles    
    return PerformanceProfileDAO(storedPerformanceProfiles)
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

    # TODO: this is related to database connections
    return MSCCompleteSetting(), Error("GetPredictedReplicas() not implemented")
    
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

