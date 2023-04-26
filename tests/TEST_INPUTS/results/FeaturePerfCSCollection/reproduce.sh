#/usr/bin/env bash
set -eu

RESULT_DIR="$1"
for zip in "$RESULT_DIR"/*config-[0,2]_success.zip; do
    unzip "$zip" -d /tmp    
done

llvm-cov show --instr-profile=/tmp/coverage_report_MSMR-no-input_0.\[\'--slow\'\].profdata $VARATS_ROOT/benchbuild/results/GenerateCoverage/FeaturePerfCSCollection-perf_tests@27f1708037,0/FeaturePerfCSCollection/build/bin/MultiSharedMultipleRegions | sed "s|$VARATS_ROOT/benchbuild/results/GenerateCoverage/FeaturePerfCSCollection-perf_tests@27f1708037,0/FeaturePerfCSCollection-27f1708037/||g" > cov_show_slow.txt
llvm-cov show --use-color --instr-profile=/tmp/coverage_report_MSMR-no-input_0.\[\'--slow\'\].profdata $VARATS_ROOT/benchbuild/results/GenerateCoverage/FeaturePerfCSCollection-perf_tests@27f1708037,0/FeaturePerfCSCollection/build/bin/MultiSharedMultipleRegions | sed "s|$VARATS_ROOT/benchbuild/results/GenerateCoverage/FeaturePerfCSCollection-perf_tests@27f1708037,0/FeaturePerfCSCollection-27f1708037/||g" > cov_show_slow_color.txt

llvm-profdata merge /tmp/coverage_report_MSMR-no-input_0.\[\'--slow\'\].profdata /tmp/coverage_report_MSMR-no-input_0.\[\'--header\'\].profdata -o /tmp/slow_header.profdata

llvm-cov export --instr-profile=/tmp/slow_header.profdata $VARATS_ROOT/benchbuild/results/GenerateCoverage/FeaturePerfCSCollection-perf_tests@27f1708037,0/FeaturePerfCSCollection/build/bin/MultiSharedMultipleRegions > llvm-profdata_merged_slow_and_header.json
