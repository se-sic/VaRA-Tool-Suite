0. Set `clean` to value `false` in your `$VARATS_ROOT/benchbuild/.benchbuild.yml` to keep build artificats.
1. Copy case_study files from [tests/TEST_INPUTS/paper_configs/test_coverage_plot/](../../paper_configs/test_coverage_plot/) to `$VARATS_ROOT/paper_configs/<your_paper_config_name>/`
2. `vara-run -E GenerateCoverage FeaturePerfCSCollection`
3. cd [tests/TEST_INPUTS/results/FeaturePerfCSCollection](.)
4. Copy results from `$VARATS_ROOT/results/FeaturePerfCSCollection/GenCov-CovR-FeaturePerfCSCollection-MultiSharedMultipleRegions-27f1708037/` to [tests/TEST_INPUTS/results/FeaturePerfCSCollection/GenCov-CovR-FeaturePerfCSCollection-MultiSharedMultipleRegions-27f1708037](GenCov-CovR-FeaturePerfCSCollection-MultiSharedMultipleRegions-27f1708037). The UUIDs in the result files changed. Adapt hardcoded paths in tests accordingly.
5. Run [reproduce.sh](reproduce.sh), e.g.`./reproduce.sh tests/TEST_INPUTS/results/FeaturePerfCSCollection/GenCov-CovR-FeaturePerfCSCollection-MultiSharedMultipleRegions-27f1708037`.
6. Add key value pair `"absolute_path": "$VARATS_ROOT/benchbuild/results/GenerateCoverage/FeaturePerfCSCollection-perf_tests@27f1708037,0/FeaturePerfCSCollection-27f1708037"` to [llvm-profdata_merged_slow_and_header.json](llvm-profdata_merged_slow_and_header.json)
