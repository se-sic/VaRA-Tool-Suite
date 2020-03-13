#!/bin/bash

# Setup

# mkdir -p extra_tests/
# cd extra_tests

mkdir -p paper_configs/

function check_err {
  local retVal=$?
  if [ $retVal -ne 0 ]; then
    echo "Error with exit code: " $retVal
    exit $retVal
  fi
}

COVERAGE='coverage run -p'

# Smoke tests
$COVERAGE $(which vara-buildsetup) -c
check_err

$COVERAGE $(which vara-gen-bbconfig)
check_err

$COVERAGE $(which vara-pc) create test_extra
check_err

$COVERAGE $(which vara-pc) select test_extra
check_err

$COVERAGE $(which vara-cs) gen paper_configs/test_extra/ -p gzip half_norm # benchbuild/tmp/gzip-HEAD #gzip/
check_err

$COVERAGE $(which vara-cs) ext paper_configs/test_extra/gzip_0.case_study -p gzip simple_add  --extra-revs 0dd8313ea7bce --merge-stage 3 #gzip/
check_err

$COVERAGE $(which vara-cs) ext paper_configs/test_extra/gzip_0.case_study -p gzip distrib_add --distribution uniform --num-rev 5 #gzip/
check_err

$COVERAGE $(which vara-cs) ext paper_configs/test_extra/gzip_0.case_study -p gzip release_add --release-type major --merge-stage 4 #gzip/
check_err

$COVERAGE $(which vara-cs) status EmptyReport
check_err

$COVERAGE $(which vara-art) add plot overview report_type=EmptyReport plot_type=paper_config_overview_plot
check_err

$COVERAGE $(which vara-art) generate --only overview
check_err

$COVERAGE $(which vara-art) list
check_err

$COVERAGE $(which vara-art) show overview
check_err

#rm -rf extra_tests/
