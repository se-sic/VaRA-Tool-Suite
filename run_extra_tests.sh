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

$COVERAGE $(which vara-gen-bbconfig)
check_err

$COVERAGE $(which vara-config) set artefacts/artefacts_dir=artefacts
check_err

$COVERAGE $(which vara-pc) create test_extra
check_err

$COVERAGE $(which vara-pc) select --paper-config test_extra
check_err

$COVERAGE $(which vara-pc) list
check_err

$COVERAGE $(which vara-cs) gen paper_configs/test_extra/ -p gravity HalfNormalSamplingMethod # benchbuild/tmp/gzip-HEAD #gzip/
check_err

$COVERAGE $(which vara-cs) ext paper_configs/test_extra/gravity_0.case_study -p gravity simple_add  --extra-revs 0dd8313ea7bce --merge-stage 3 #gravity/
check_err

$COVERAGE $(which vara-cs) ext paper_configs/test_extra/gravity_0.case_study -p gravity distrib_add --distribution UniformSamplingMethod --num-rev 5 #gravity/
check_err

$COVERAGE $(which vara-cs) ext paper_configs/test_extra/gravity_0.case_study -p gravity release_add --release-type major --merge-stage 4 #gravity/
check_err

$COVERAGE $(which vara-cs) status EmptyReport
check_err

<<<<<<< HEAD
# already a unit test but needed for succeeding tests to make sense
$COVERAGE $(which vara-plot) --save-artefact overview --plot-dir overview_plots pc-overview-plot --report-type EmptyReport
check_err

$COVERAGE $(which vara-art) generate --only overview
check_err

$COVERAGE $(which vara-art) list
check_err

$COVERAGE $(which vara-art) show overview
check_err

=======
>>>>>>> vara-dev
# Tests that we can add extra refs from other branches if a refspec is specified
$COVERAGE $(which vara-pc) create test_extra_refs
check_err

$COVERAGE $(which vara-cs) gen paper_configs/test_extra_refs/ -p test-taint-tests UniformSamplingMethod --num-rev 0 --extra-revs f3729ae7f861dab7975f5c
check_err

$COVERAGE $(which vara-cs) status EmptyReport | grep -q f3729ae7f8
check_err

#rm -rf extra_tests/
