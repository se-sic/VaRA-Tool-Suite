#!/bin/bash
#
################################
# WARNING USE AT YOUR OWN RISK #
################################
#
CWD=$(pwd)
echo 'Current VARA_ROOT content: "'${VARA_ROOT}'"'
while true; do
    read -p "Have you set the VARA_ROOT environment variable? [y/n] " yn
    case $yn in
        [Yy]* ) break;;
        [Nn]* ) echo "Please set the VARA_ROOT env variable before running this script."; exit;;
        * ) echo "Please answer yes or no.";;
    esac
done
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
cd ${CWD} && ./add-paper-config.sh
cd ${VARA_ROOT} && printf "0\n" | vara-pc select
printf "\n\n\n"
#
echo 'TODO: Set the correct paper-config-path in '${VARA_ROOT}'/.varats.yml'
#
echo 'TODO: Add your custom phasar-llvm binary to $PATH'
#
# To start the otfb analysis:
# cd ${VARA_ROOT}/benchbuild && benchbuild -vv run -E PhasarOtfb gzip grep vim [MORE TOOLS]