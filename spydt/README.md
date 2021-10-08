# Work in progress

This folder contains a re-implementation of SPDT in python.

Currently completed:

* System model (all dataclasses) in `model.py`. They are annotated 
  to allow the automatic marshalling to/from json (even from yaml
  via json).

* `util.py` contains the function `ReadConfigFile()` which reads 
  `config.yml` and returns the appropriate object.

* Abstract base clase in `policy.py` from which all policies derive.

* Full implementation of Naive strategy (`naive.py`), and the functions 
  which are called from it (most of them in `aux_func.py`). 
  
In progress:

* `best_pair.py`, `only_delta.py` contain "empty" implementation of
  these strategies

* `storage.py` contains empty implementation of DB interfaces. 

* `mock_storage.py` Contains implementations of functions that should
  get model data from databases, but currently returns data
  based on the json files from `../test_mock_input` folder.

* `run.py` is the entrypoint which aims to use the minimum number
  of functions required to test the Naive strategy. It contains the
  function `StartPolicyDerivation()` which in the original go implementation
  was the one launched at each timeslot to derive the next policy.

# Workflow

* Ensure that a virtual environment with python 3.8 and `requirements.txt`
  installed is activate.

* From the parent folder, run:

    ```
    $ mypy spydt
    ```

    to test that no typing errors are present. 

* Run:

    ```
    $ python -m spytest.run
    ```

    to check that no runtime errors arise.

* Work on `spytest/run.py` to complete the `StartPolicyDerivation()` function
  until a Policy is obtained. This will require to code all the auxiliary
  functions that are called from it (probably moking more database accesses)
