#!/bin/bash

# Setup

# mkdir -p extra_tests/
# cd extra_tests

rm -r paper_configs/
mkdir -p paper_configs/

function check_err {
  local retVal=$?
  if [ $retVal -ne 0 ]; then
    echo "Error with exit code: " $retVal
    exit $retVal
  fi
}

COVERAGE='coverage run -p --rcfile=.coveragerc'

# Smoke tests
$COVERAGE "$(which vara-buildsetup)" vara -c
check_err

#has been moved to a unit tests, has to remain until all test have been moved
$COVERAGE $(which vara-gen-bbconfig)
check_err

#has been moved to a unit tests, has to remain until all test have been moved
$COVERAGE $(which vara-config) set artefacts/artefacts_dir=artefacts
check_err

#has been moved to a unit tests, has to remain until all test have been moved
$COVERAGE $(which vara-pc) create test_extra
check_err

#has been moved to a unit tests, has to remain until all test have been moved
$COVERAGE $(which vara-pc) select --paper-config test_extra
check_err

#has been moved to a unit tests, has to remain until all test have been moved
$COVERAGE $(which vara-pc) list
check_err

$COVERAGE $(which vara-cs) gen -p gravity select_smaple HalfNormalSamplingMethod # benchbuild/tmp/gzip-HEAD #gzip/
check_err

$COVERAGE $(which vara-cs) gen -p gravity --merge-stage 3 select_specific  0dd8313ea7bce  #gravity/
check_err

$COVERAGE $(which vara-cs) gen -p gravity select_smaple UniformSamplingMethod --num-rev 5 #gravity/
check_err

$COVERAGE $(which vara-cs) gen -p gravity --merge-stage 4 select_release major  #gravity/
check_err

$COVERAGE $(which vara-cs) status EmptyReport
check_err


# Tests that we can add extra refs from other branches if a refspec is specified

#has been moved to a unit tests, has to remain until all test have been moved
$COVERAGE $(which vara-pc) create test_extra_refs
check_err

$COVERAGE $(which vara-cs) gen -p test-taint-tests select_specific f3729ae7f861dab7975f5c
check_err

$COVERAGE $(which vara-cs) status EmptyReport | grep -q f3729ae7f8
check_err

#rm -rf extra_tests/
