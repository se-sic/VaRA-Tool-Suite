#!/bin/bash

# Setup

mkdir -p paper_configs/test/

if [ ! -d "gzip" ]; then
  git clone https://git.savannah.gnu.org/git/gzip.git gzip
fi

COVERAGE='coverage run -p'

# Smoke tests
$COVERAGE $(which vara-buildsetup) -c
$COVERAGE $(which vara-cs) gen paper_configs/test/ half_norm gzip/
$COVERAGE $(which vara-cs) ext paper_configs/test/gzip_0.case_study simple_add gzip/ --extra-revs 0dd8313ea7bce --merge-stage 3
$COVERAGE $(which vara-cs) ext paper_configs/test/gzip_0.case_study distrib_add gzip/ --distribution uniform --num-rev 5
$COVERAGE $(which vara-cs) status
