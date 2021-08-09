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
# Add paper-config
./add-paper-config.sh
cd ${VARA_ROOT} && printf "0\n" | vara-pc select
#
# TODO: Set the correct paper-config-path in .varats.yml
#
# TODO: Place your custom phasar-llvm binary at ../vara-root/tools/phasar/bin/evaltool or add it to $PATH
#
# To start the otfb analysis:
# cd ${VARA_ROOT}/benchbuild && benchbuild -vv run -E PhasarOtfb gzip grep vim [MORE TOOLS]