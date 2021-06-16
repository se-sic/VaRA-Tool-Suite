#!/bin/bash
#
################################
# WARNING USE AT YOUR OWN RISK #
################################
#
mkdir -p ../vara-root
# Install requirements
cd ../varats-core && python3 -m pip install --user --upgrade -e . && cd -
cd ../varats && python3 -m pip install --user --upgrade -e . && cd -
# Create benchbuild config
cd ../vara-root && /usr/bin/yes | vara-gen-bbconfig
# Add OTFB experiment to benchbuild.yml
awk '/ide_linear_constant_experiment/ { print; print "        - varats.experiments.phasar.otfb_experiment"; next }1' ../vara-root/benchbuild/.benchbuild.yml > ../vara-root/benchbuild/.benchbuild_new.yml
mv ../vara-root/benchbuild/.benchbuild_new.yml ../vara-root/benchbuild/.benchbuild.yml
#
# Place your custom phasar-llvm binary at
# ../vara-root/tools/phasar/bin/phasar-with-otfb-llvm
#
# To start an analysis:
# cd ../vara-root/benchbuild
# benchbuild -vvvv run -E PhasarOtfb gzip