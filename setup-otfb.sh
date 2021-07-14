#!/bin/bash
#
################################
# WARNING USE AT YOUR OWN RISK #
################################
#
mkdir -p ../vara-root
# Install requirements
cd varats-core && python3 -m pip install --user --upgrade -e . && cd -
cd varats && python3 -m pip install --user --upgrade -e . && cd -
# Create benchbuild config
cd $VARA_ROOT && /usr/bin/yes | vara-gen-bbconfig
# Add OTFB experiment to benchbuild.yml
awk '/ide_linear_constant_experiment/ { print; print "        - varats.experiments.phasar.otfb_experiment"; next }1' $VARA_ROOT/benchbuild/.benchbuild.yml > $VARA_ROOT/benchbuild/.benchbuild_new.yml
mv $VARA_ROOT/benchbuild/.benchbuild_new.yml $VARA_ROOT/benchbuild/.benchbuild.yml
mkdir -p $VARA_ROOT/tools/bin
# TODO: Place your custom phasar-llvm binary at
# ../vara-root/tools/phasar/bin/phasar-with-otfb-llvm
#
# To start an analysis:
# cd ../vara-root/benchbuild
# benchbuild -vvvv run -E PhasarOtfb gzip