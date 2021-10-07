from dataclasses import dataclass
from .model import (
    PerformanceProfile, Error, Limit, MSCCompleteSetting
)
from typing import Tuple

@dataclass
class PerformanceProfileDAO:
    # TODO: access to database or files to retrieve the queried info
    def FindByLimitsAndReplicas(self, cores: float, memory: float, replicas: int) -> Tuple[PerformanceProfile, Error]:
        return PerformanceProfile(), Error("Not implemented")

    def FindProfileByLimits(self, limit: Limit) -> Tuple[PerformanceProfile, Error]:
        return PerformanceProfile(), Error("Not implemented")

    def UpdateById(self, id: str, performanceProfile: PerformanceProfile) -> Error:
        return Error("Not implemented")


def GetPerformanceProfileDAO(serviceName: str) -> PerformanceProfileDAO:
    # TODO: this is related to database connections
    return PerformanceProfileDAO()
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

def GetPredictedReplicas(endpoint: str, appName: str, appType: str, mainServiceName: str,
              msc: float, cpuCores: float, memGb: float) -> Tuple[MSCCompleteSetting, Error]:

    # TODO: this is related to database connections
    return MSCCompleteSetting(), Error("Not implemented")