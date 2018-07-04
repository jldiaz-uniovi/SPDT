package policies_derivation

import (
	"github.com/Cloud-Pie/SPDT/types"
	"github.com/Cloud-Pie/SPDT/util"
	"github.com/Cloud-Pie/SPDT/config"
	"time"
	"github.com/Cloud-Pie/SPDT/rest_clients/scheduler"
	"log"
)

//TODO: Profile for Current config

//Interface for strategies of how to scale
type PolicyDerivation interface {
	CreatePolicies(poiList []types.PoI, values []int, times [] time.Time ,profile types.ServiceProfile)
	FindSuitableVMs(vmsInfo []types.VmProfile, limit types.Limit)
}

//Interface for strategies of when to scale
type TimeWindowDerivation interface {
	Cost()	int
	NumberIntervals()	int
	WindowDerivation(values []int, times [] time.Time)	types.ProcessedForecast
}

func Policies(poiList []types.PoI, values []int, times [] time.Time, mapVMProfiles map[string]types.VmProfile, ServiceProfiles types.ServiceProfile, configuration config.SystemConfiguration) []types.Policy {
	var policies []types.Policy
	currentState,err := scheduler.CurrentState(configuration.SchedulerComponent.Endpoint + util.ENDPOINT_CURRENT_STATE)
	if err != nil {
		log.Printf("Error to get current state")
	}

	switch configuration.PreferredAlgorithm {

	case util.NAIVE_ALGORITHM:
		timeWindows := SmallStepOverProvision{PoIList:poiList}
		processedForecast := timeWindows.WindowDerivation(values,times)
		naive := NaivePolicy {util.NAIVE_ALGORITHM, 100, timeWindows}
		policies = naive.CreatePolicies(currentState, processedForecast, mapVMProfiles, ServiceProfiles)

	case util.INTEGER_PROGRAMMING_ALGORITHM:
		integer := IntegerPolicy{util.INTEGER_PROGRAMMING_ALGORITHM}
		policies = integer.CreatePolicies(poiList,values,times, ServiceProfiles)
	case util.SMALL_STEP_ALGORITHM:
		//sstep := SStepPolicy{ util.SMALL_STEP_ALGORITHM}
		//policies = sstep.CreatePolicies(poiList,values,times, mapVMProfiles, ServiceProfiles)
	default:
		/*timeWindows := SmallStepOverProvision{}
		timeWindows.PoIList = poiList
		processedForecast := timeWindows.WindowDerivation(values,times)
		naive := NaivePolicy {util.NAIVE_ALGORITHM, 100, timeWindows}
		policies = naive.CreatePolicies(processedForecast, mapVMProfiles, ServiceProfiles)
		sstep := SStepPolicy{ util.SMALL_STEP_ALGORITHM}
		policies = append(naive.CreatePolicies(processedForecast, mapVMProfiles, ServiceProfiles),sstep.CreatePolicies(poiList,values,times, mapVMProfiles, ServiceProfiles)...)
	*/
	}
	return policies
}

//Adjust the times that were interpolated
func adjustTime(t time.Time, factor float64) time.Time {
	f := factor*3600
	return t.Add(time.Duration(f) * time.Second)
}