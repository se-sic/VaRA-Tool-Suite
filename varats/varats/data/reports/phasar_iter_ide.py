import shutil
import typing as tp
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

from varats.report.gnu_time_report import TimeReportAggregate
from varats.report.report import BaseReport


class PhasarBCStats():

    def __init__(self, path: Path) -> None:
        self._num_instructions = -1

        with open(path, "r", encoding="utf-8") as stats_file:
            for line in stats_file.readlines():
                if line.startswith("> LLVM IR instructions"):
                    self._num_instructions = int(line.split(":")[1])

    @property
    def num_instructions(self) -> int:
        return self._num_instructions


class PhasarIterIDESolverStats():

    def __init__(self, path: Path) -> None:
        self._all_inter_propagations = -1
        self._source_facts_and_cs_to_inter_job = -1
        self._source_facts_and_func_to_inter_job = -1
        self._max_inner_map_size = -1
        self._avg_inner_map_size = -1.0
        self._jump_functions_map_bytes = -1
        self._val_tab_bytes = -1
        self._num_unique_flow_facts = -1
        self._node_compressor_size = -1
        self._fact_compressor_size = -1
        self._fun_compressor_size = -1
        self._jump_functions_high_watermark = -1
        self._worklist_high_watermark = -1
        self._call_wl_high_watermark = -1
        self._wl_prop_high_watermark = -1
        self._wl_comp_high_watermark = -1
        self._total_calls_propagate_procedure_summaries = -1
        self._max_inter_jobs_per_relevant_call = -1
        self._avg_inter_jobs_per_relevant_call = -1.0
        self._total_num_linear_search_for_summaries = -1
        self._max_linear_search_len_for_summaries = -1
        self._avg_linear_search_len_for_summaries = -1.0
        self._max_diff_summaries_vs_search_len = -1
        self._avg_diff_summaries_vs_search_len = -1.0
        self._rel_diff_summaries_vs_search_len = -1.0

        with open(path, "r", encoding="utf-8") as stats_file:
            for line in stats_file.readlines():
                if line.startswith("> AllInterPropagations:"):
                    self._all_inter_propagations = int(
                        line.split(":")[1].strip()
                    )
                elif line.startswith("> SourceFactAndCSToInterJob:"):
                    self._source_facts_and_cs_to_inter_job = int(
                        line.split(":")[1].strip()
                    )
                elif line.startswith("> SourceFactAndFuncToInterJob:"):
                    self._source_facts_and_func_to_inter_job = int(
                        line.split(":")[1].strip()
                    )
                elif line.startswith("> MaxInnerMapSize:"):
                    self._max_inner_map_size = int(line.split(":")[1].strip())
                elif line.startswith("> AvgInnerMapSize:"):
                    self._avg_inner_map_size = float(line.split(":")[1].strip())
                elif line.startswith("> JumpFunctions Map Size(Bytes):"):
                    ApproxSize = line.split(":")[1].strip()
                    if ApproxSize.startswith('~'):
                        ApproxSize = ApproxSize[1:]
                    self._jump_functions_map_bytes = int(ApproxSize)
                elif line.startswith("> ValTab Size(Bytes):"):
                    ApproxSize = line.split(":")[1].strip()
                    if ApproxSize.startswith('~'):
                        ApproxSize = ApproxSize[1:]
                    self._val_tab_bytes = int(ApproxSize)
                elif line.startswith("> NumFlowFacts:"):
                    self._num_unique_flow_facts = int(
                        line.split(":")[1].strip()
                    )
                elif line.startswith("> NodeCompressor:"):
                    self._node_compressor_size = int(line.split(":")[1].strip())
                elif line.startswith("> FactCompressor:"):
                    self._fact_compressor_size = int(line.split(":")[1].strip())
                elif line.startswith("> FunCompressor:"):
                    self._fun_compressor_size = int(line.split(":")[1].strip())
                elif line.startswith("> JumpFunctions:"):
                    self._jump_functions_high_watermark = int(
                        line.split(":")[1].strip()
                    )
                elif line.startswith("> WorkList:"):
                    self._worklist_high_watermark = int(
                        line.split(":")[1].strip()
                    )
                elif line.startswith("> CallWL:"):
                    self._call_wl_high_watermark = int(
                        line.split(":")[1].strip()
                    )
                elif line.startswith("> WLProp:"):
                    self._wl_prop_high_watermark = int(
                        line.split(":")[1].strip()
                    )
                elif line.startswith("> WLComp:"):
                    self._wl_comp_high_watermark = int(
                        line.split(":")[1].strip()
                    )
                elif line.startswith(
                    "> Total calls to propagateProcedureSummaries:"
                ):
                    self._total_calls_propagate_procedure_summaries = int(
                        line.split(":")[1].strip()
                    )
                elif line.startswith("> Max InterJobs per relevant call:"):
                    self._max_inter_jobs_per_relevant_call = int(
                        line.split(":")[1].strip()
                    )
                elif line.startswith("> Avg InterJobs per relevant call:"):
                    self._avg_inter_jobs_per_relevant_call = float(
                        line.split(":")[1].strip()
                    )
                elif line.startswith(
                    "> Total num of linear searches for summaries:"
                ):
                    self._total_num_linear_search_for_summaries = int(
                        line.split(":")[1].strip()
                    )
                elif line.startswith(
                    "> Max Length of linear search for summaries:"
                ):
                    self._max_linear_search_len_for_summaries = int(
                        line.split(":")[1].strip()
                    )
                elif line.startswith(
                    "> Avg Length of linear search for summaries:"
                ):
                    self._avg_linear_search_len_for_summaries = float(
                        line.split(":")[1].strip()
                    )
                elif line.startswith(
                    "> Max Diff of summaries found vs search length:"
                ):
                    self._max_diff_summaries_vs_search_len = int(
                        line.split(":")[1].strip()
                    )
                elif line.startswith(
                    "> Avg Diff of summaries found vs search length:"
                ):
                    self._avg_diff_summaries_vs_search_len = float(
                        line.split(":")[1].strip()
                    )
                elif line.startswith(
                    "> Rel Diff of summaries found vs search length:"
                ):
                    self._rel_diff_summaries_vs_search_len = float(
                        line.split(":")[1].strip()
                    )


class ResultCompare():

    def __init__(self, path: Path) -> None:
        found_match = False
        found_not_match = False
        with open(path, "r", encoding="utf-8") as stats_file:
            for line in stats_file.readlines():
                if line.startswith("The results do not match!"):
                    found_not_match = True

                if line.startswith("The results do match!"):
                    found_match = True

        if found_match and found_not_match:
            raise AssertionError(
                "File contained mixed information wrong/wright results "
                "at the same time"
            )

        # if not found_match and not found_not_match:
        #     raise AssertionError("File did not contain cmp data")

        if found_match:
            self._results_match = True
        else:
            self._results_match = False

    @property
    def results_match(self) -> bool:
        return self._results_match


class PhasarIterIDEStatsReport(
    BaseReport, shorthand="PIterIDEStats", file_type="zip"
):

    _bc_stats: tp.Optional[PhasarBCStats]
    _old_typestate: tp.Optional[TimeReportAggregate]
    _old_taint: tp.Optional[TimeReportAggregate]
    _old_lca: tp.Optional[TimeReportAggregate]
    _old_iia: tp.Optional[TimeReportAggregate]

    _new_typestate_stack: tp.Optional[TimeReportAggregate]
    _new_taint_stack: tp.Optional[TimeReportAggregate]
    _new_lca_stack: tp.Optional[TimeReportAggregate]
    _new_iia_stack: tp.Optional[TimeReportAggregate]

    _new_typestate_queue: tp.Optional[TimeReportAggregate]
    _new_taint_queue: tp.Optional[TimeReportAggregate]
    _new_lca_queue: tp.Optional[TimeReportAggregate]
    _new_typestate_depth_prio: tp.Optional[TimeReportAggregate]
    _new_taint_depth_prio: tp.Optional[TimeReportAggregate]
    _new_lca_depth_prio: tp.Optional[TimeReportAggregate]
    _new_typestate_depth_prio_rev: tp.Optional[TimeReportAggregate]
    _new_taint_depth_prio_rev: tp.Optional[TimeReportAggregate]
    _new_lca_depth_prio_rev: tp.Optional[TimeReportAggregate]
    _new_typestate_size_prio: tp.Optional[TimeReportAggregate]
    _new_taint_size_prio: tp.Optional[TimeReportAggregate]
    _new_lca_size_prio: tp.Optional[TimeReportAggregate]
    _new_typestate_size_prio_rev: tp.Optional[TimeReportAggregate]
    _new_taint_size_prio_rev: tp.Optional[TimeReportAggregate]
    _new_lca_size_prio_rev: tp.Optional[TimeReportAggregate]
    _new_typestate_jf1: tp.Optional[TimeReportAggregate]
    _new_taint_jf1: tp.Optional[TimeReportAggregate]
    _new_lca_jf1: tp.Optional[TimeReportAggregate]
    _new_iia_jf1: tp.Optional[TimeReportAggregate]
    _new_typestate_jf3: tp.Optional[TimeReportAggregate]
    _new_taint_jf3: tp.Optional[TimeReportAggregate]
    _new_lca_jf3: tp.Optional[TimeReportAggregate]
    _new_iia_jf3: tp.Optional[TimeReportAggregate]
    _new_typestate_gc: tp.Optional[TimeReportAggregate]
    _new_taint_gc: tp.Optional[TimeReportAggregate]
    _new_lca_gc: tp.Optional[TimeReportAggregate]
    _new_iia_gc: tp.Optional[TimeReportAggregate]
    _new_typestate_gc_jf1: tp.Optional[TimeReportAggregate]
    _new_taint_gc_jf1: tp.Optional[TimeReportAggregate]
    _new_lca_gc_jf1: tp.Optional[TimeReportAggregate]
    _new_iia_gc_jf1: tp.Optional[TimeReportAggregate]

    _solver_stats_taint_jf1: tp.Optional[PhasarIterIDESolverStats]
    _solver_stats_taint_jf2: tp.Optional[PhasarIterIDESolverStats]
    _solver_stats_typestate_jf1: tp.Optional[PhasarIterIDESolverStats]
    _solver_stats_typestate_jf2: tp.Optional[PhasarIterIDESolverStats]
    _solver_stats_lca_jf1: tp.Optional[PhasarIterIDESolverStats]
    _solver_stats_lca_jf2: tp.Optional[PhasarIterIDESolverStats]

    def __init__(self, path: Path) -> None:
        self._bc_stats = None
        self._cmp_typestate = None
        self._cmp_taint = None
        self._cmp_lca = None

        self._old_typestate = None
        self._old_taint = None
        self._old_lca = None
        self._old_iia = None

        # self._new_typestate = None
        # self._new_taint = None
        # self._new_lca = None
        self._new_typestate_stack = None
        self._new_taint_stack = None
        self._new_lca_stack = None
        self._new_iia_stack = None

        self._new_typestate_queue = None
        self._new_taint_queue = None
        self._new_lca_queue = None

        self._new_typestate_depth_prio = None
        self._new_taint_depth_prio = None
        self._new_lca_depth_prio = None

        self._new_typestate_depth_prio_rev = None
        self._new_taint_depth_prio_rev = None
        self._new_lca_depth_prio_rev = None

        self._new_typestate_size_prio = None
        self._new_taint_size_prio = None
        self._new_lca_size_prio = None

        self._new_typestate_size_prio_rev = None
        self._new_taint_size_prio_rev = None
        self._new_lca_size_prio_rev = None

        self._new_typestate_jf1 = None
        self._new_taint_jf1 = None
        self._new_lca_jf1 = None
        self._new_iia_jf1 = None

        self._new_typestate_jf3 = None
        self._new_taint_jf3 = None
        self._new_lca_jf3 = None
        self._new_iia_jf3 = None

        self._new_typestate_gc = None
        self._new_taint_gc = None
        self._new_lca_gc = None
        self._new_iia_gc = None

        self._new_typestate_gc_jf1 = None
        self._new_taint_gc_jf1 = None
        self._new_lca_gc_jf1 = None
        self._new_iia_gc_jf1 = None

        self._solver_stats_taint_jf1 = None
        self._solver_stats_taint_jf2 = None
        self._solver_stats_typestate_jf1 = None
        self._solver_stats_typestate_jf2 = None
        self._solver_stats_lca_jf1 = None
        self._solver_stats_lca_jf2 = None

        with TemporaryDirectory() as tmpdir:
            shutil.unpack_archive(path, tmpdir)

            for file in Path(tmpdir).iterdir():
                if file.suffix in (
                    ".timeout",
                    ".oom",
                    ".err",
                ):
                    print(f"Skip errorneous file {file}")
                    continue

                if file.name.startswith("phasar_bc_stats"):
                    self._bc_stats = PhasarBCStats(file)
                elif file.name.startswith("cmp_typestate"):
                    self._cmp_typestate = ResultCompare(file)
                elif file.name.startswith("cmp_taint"):
                    self._cmp_taint = ResultCompare(file)
                elif file.name.startswith("cmp_lca"):
                    self._cmp_lca = ResultCompare(file)

                elif file.name.startswith("old_typestate"):
                    self._old_typestate = TimeReportAggregate(file)
                elif file.name.startswith("old_taint"):
                    self._old_taint = TimeReportAggregate(file)
                elif file.name.startswith("old_lca"):
                    self._old_lca = TimeReportAggregate(file)
                elif file.name.startswith("new_iia_vara-BR-Old"):
                    self._old_iia = TimeReportAggregate(file)

                elif file.name.startswith("new_typestate_stack"):
                    self._new_typestate_stack = TimeReportAggregate(file)
                elif file.name.startswith("new_taint_stack"):
                    self._new_taint_stack = TimeReportAggregate(file)
                elif file.name.startswith("new_lca_stack"):
                    self._new_lca_stack = TimeReportAggregate(file)
                elif file.name == "new_iia_vara-BR-JF2":
                    self._new_iia_stack = TimeReportAggregate(file)

                elif file.name.startswith("new_typestate_queue"):
                    self._new_typestate_queue = TimeReportAggregate(file)
                elif file.name.startswith("new_taint_queue"):
                    self._new_taint_queue = TimeReportAggregate(file)
                elif file.name.startswith("new_lca_queue"):
                    self._new_lca_queue = TimeReportAggregate(file)

                elif file.name.startswith("new_typestate_size-prio-rev"):
                    self._new_typestate_size_prio_rev = TimeReportAggregate(
                        file
                    )
                elif file.name.startswith("new_typestate_size-prio"):
                    self._new_typestate_size_prio = TimeReportAggregate(file)
                elif file.name.startswith("new_taint_size-prio-rev"):
                    self._new_taint_size_prio_rev = TimeReportAggregate(file)
                elif file.name.startswith("new_taint_size-prio"):
                    self._new_taint_size_prio = TimeReportAggregate(file)
                elif file.name.startswith("new_lca_size-prio-rev"):
                    self._new_lca_size_prio_rev = TimeReportAggregate(file)
                elif file.name.startswith("new_lca_size-prio"):
                    self._new_lca_size_prio = TimeReportAggregate(file)
                elif file.name.startswith("new_typestate_depth-prio-rev"):
                    self._new_typestate_depth_prio_rev = TimeReportAggregate(
                        file
                    )
                elif file.name.startswith("new_taint_depth-prio-rev"):
                    self._new_taint_depth_prio_rev = TimeReportAggregate(file)
                elif file.name.startswith("new_lca_depth-prio-rev"):
                    self._new_lca_depth_prio_rev = TimeReportAggregate(file)
                elif file.name.startswith("new_typestate_depth-prio"):
                    self._new_typestate_depth_prio = TimeReportAggregate(file)
                elif file.name.startswith("new_taint_depth-prio"):
                    self._new_taint_depth_prio = TimeReportAggregate(file)
                elif file.name.startswith("new_lca_depth-prio"):
                    self._new_lca_depth_prio = TimeReportAggregate(file)

                elif file.name.startswith("new_typestate_jf1"):
                    self._new_typestate_jf1 = TimeReportAggregate(file)
                elif file.name.startswith("new_taint_jf1"):
                    self._new_taint_jf1 = TimeReportAggregate(file)
                elif file.name.startswith("new_lca_jf1"):
                    self._new_lca_jf1 = TimeReportAggregate(file)
                elif file.name.startswith("new_iia_vara-BR-JF1"):
                    self._new_iia_jf1 = TimeReportAggregate(file)

                elif file.name.startswith("new_typestate_jf3"):
                    self._new_typestate_jf3 = TimeReportAggregate(file)
                elif file.name.startswith("new_taint_jf3"):
                    self._new_taint_jf3 = TimeReportAggregate(file)
                elif file.name.startswith("new_lca_jf3"):
                    self._new_lca_jf3 = TimeReportAggregate(file)
                elif file.name.startswith("new_iia_vara-BR-JF2S"):
                    print("Have _new_iia_jf3")
                    self._new_iia_jf3 = TimeReportAggregate(file)

                elif file.name.startswith("new_typestate_gc_jf1"):
                    self._new_typestate_gc_jf1 = TimeReportAggregate(file)
                elif file.name.startswith("new_taint_gc_jf1"):
                    self._new_taint_gc_jf1 = TimeReportAggregate(file)
                elif file.name.startswith("new_lca_gc_jf1"):
                    self._new_lca_gc_jf1 = TimeReportAggregate(file)
                elif file.name.startswith("new_iia_vara-BR-JF1-GC"):
                    self._new_iia_gc_jf1 = TimeReportAggregate(file)

                elif file.name.startswith("new_typestate_gc"):
                    self._new_typestate_gc = TimeReportAggregate(file)
                elif file.name.startswith("new_taint_gc"):
                    self._new_taint_gc = TimeReportAggregate(file)
                elif file.name.startswith("new_lca_gc"):
                    self._new_lca_gc = TimeReportAggregate(file)
                elif file.name.startswith("new_iia_vara-BR-JF2-GC"):
                    self._new_iia_gc = TimeReportAggregate(file)

                elif file.name.startswith("stats_taint_jf1"):
                    self._solver_stats_taint_jf1 = PhasarIterIDESolverStats(
                        file
                    )
                elif file.name.startswith("stats_taint_jf2"):
                    self._solver_stats_taint_jf2 = PhasarIterIDESolverStats(
                        file
                    )
                elif file.name.startswith("stats_typestate_jf1"):
                    self._solver_stats_typestate_jf1 = PhasarIterIDESolverStats(
                        file
                    )
                elif file.name.startswith("stats_typestate_jf2"):
                    self._solver_stats_typestate_jf2 = PhasarIterIDESolverStats(
                        file
                    )
                elif file.name.startswith("stats_lca_jf1"):
                    self._solver_stats_lca_jf1 = PhasarIterIDESolverStats(file)
                elif file.name.startswith("stats_lca_jf2"):
                    self._solver_stats_lca_jf2 = PhasarIterIDESolverStats(file)
                else:
                    print(f"Unknown file {file}!")

    def merge_with(self, Other):
        if self._bc_stats is None:
            self._bc_stats = Other._bc_stats
        if self._cmp_typestate is None:
            self._cmp_typestate = Other._cmp_typestate
        if self._cmp_taint is None:
            self._cmp_taint = Other._cmp_taint
        if self._cmp_lca is None:
            self._cmp_lca = Other._cmp_lca

        if self._old_typestate is None:
            self._old_typestate = Other._old_typestate
        if self._old_taint is None:
            self._old_taint = Other._old_taint
        if self._old_lca is None:
            self._old_lca = Other._old_lca
        if self._old_iia is None:
            self._old_iia = Other._old_iia

        if self._new_typestate_stack is None:
            self._new_typestate_stack = Other._new_typestate_stack
        if self._new_taint_stack is None:
            self._new_taint_stack = Other._new_taint_stack
        if self._new_lca_stack is None:
            self._new_lca_stack = Other._new_lca_stack
        if self._new_iia_stack is None:
            self._new_iia_stack = Other._new_iia_stack

        if self._new_typestate_jf1 is None:
            self._new_typestate_jf1 = Other._new_typestate_jf1
        if self._new_taint_jf1 is None:
            self._new_taint_jf1 = Other._new_taint_jf1
        if self._new_lca_jf1 is None:
            self._new_lca_jf1 = Other._new_lca_jf1
        if self._new_iia_jf1 is None:
            self._new_iia_jf1 = Other._new_iia_jf1

        if self._new_typestate_jf3 is None:
            self._new_typestate_jf3 = Other._new_typestate_jf3
        if self._new_taint_jf3 is None:
            self._new_taint_jf3 = Other._new_taint_jf3
        if self._new_lca_jf3 is None:
            self._new_lca_jf3 = Other._new_lca_jf3
        if self._new_iia_jf3 is None:
            self._new_iia_jf3 = Other._new_iia_jf3

        if self._new_typestate_gc_jf1 is None:
            self._new_typestate_gc_jf1 = Other._new_typestate_gc_jf1
        if self._new_taint_gc_jf1 is None:
            self._new_taint_gc_jf1 = Other._new_taint_gc_jf1
        if self._new_lca_gc_jf1 is None:
            self._new_lca_gc_jf1 = Other._new_lca_gc_jf1
        if self._new_iia_gc_jf1 is None:
            self._new_iia_gc_jf1 = Other._new_iia_gc_jf1

        if self._new_typestate_gc is None:
            self._new_typestate_gc = Other._new_typestate_gc
        if self._new_taint_gc is None:
            self._new_taint_gc = Other._new_taint_gc
        if self._new_lca_gc is None:
            self._new_lca_gc = Other._new_lca_gc
        if self._new_iia_gc is None:
            self._new_iia_gc = Other._new_iia_gc

    @property
    def basic_bc_stats(self) -> tp.Optional[PhasarBCStats]:
        return self._bc_stats

    @property
    def cmp_typestate(self) -> tp.Optional[ResultCompare]:
        return self._cmp_typestate

    @property
    def cmp_taint(self) -> tp.Optional[ResultCompare]:
        return self._cmp_taint

    @property
    def cmp_lca(self) -> tp.Optional[ResultCompare]:
        return self._cmp_lca

    @property
    def old_typestate(self) -> tp.Optional[TimeReportAggregate]:
        return self._old_typestate

    @property
    def old_taint(self) -> tp.Optional[TimeReportAggregate]:
        return self._old_taint

    @property
    def old_lca(self) -> tp.Optional[TimeReportAggregate]:
        return self._old_lca

    @property
    def old_iia(self) -> tp.Optional[TimeReportAggregate]:
        return self._old_iia

    # convenience methods
    @property
    def new_typestate(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_typestate_stack

    @property
    def new_taint(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_taint_stack

    @property
    def new_lca(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_lca_stack

    @property
    def new_iia(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_iia_stack

    @property
    def new_typestate_stack(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_typestate_stack

    @property
    def new_taint_stack(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_taint_stack

    @property
    def new_lca_stack(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_lca_stack

    @property
    def new_iia_stack(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_iia_stack

    @property
    def new_typestate_queue(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_typestate_queue

    @property
    def new_taint_queue(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_taint_queue

    @property
    def new_lca_queue(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_lca_queue

    @property
    def new_typestate_size_prio(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_typestate_size_prio

    @property
    def new_taint_size_prio(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_taint_size_prio

    @property
    def new_lca_size_prio(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_lca_size_prio

    @property
    def new_typestate_size_prio_rev(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_typestate_size_prio_rev

    @property
    def new_taint_size_prio_rev(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_taint_size_prio_rev

    @property
    def new_lca_size_prio_rev(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_lca_size_prio_rev

    @property
    def new_typestate_depth_prio(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_typestate_depth_prio

    @property
    def new_taint_depth_prio(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_taint_depth_prio

    @property
    def new_lca_depth_prio(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_lca_depth_prio

    @property
    def new_typestate_depth_prio_rev(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_typestate_depth_prio_rev

    @property
    def new_taint_depth_prio_rev(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_taint_depth_prio_rev

    @property
    def new_lca_depth_prio_rev(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_lca_depth_prio_rev

    @property
    def new_typestate_jf1(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_typestate_jf1

    @property
    def new_taint_jf1(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_taint_jf1

    @property
    def new_lca_jf1(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_lca_jf1

    @property
    def new_iia_jf1(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_iia_jf1

    @property
    def new_typestate_jf3(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_typestate_jf3

    @property
    def new_taint_jf3(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_taint_jf3

    @property
    def new_lca_jf3(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_lca_jf3

    @property
    def new_iia_jf3(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_iia_jf3

    @property
    def new_typestate_gc(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_typestate_gc

    @property
    def new_taint_gc(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_taint_gc

    @property
    def new_lca_gc(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_lca_gc

    @property
    def new_iia_gc(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_iia_gc

    @property
    def new_typestate_gc_jf1(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_typestate_gc_jf1

    @property
    def new_taint_gc_jf1(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_taint_gc_jf1

    @property
    def new_lca_gc_jf1(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_lca_gc_jf1

    @property
    def new_iia_gc_jf1(self) -> tp.Optional[TimeReportAggregate]:
        return self._new_iia_gc_jf1

    @property
    def solver_stats_taint_jf1(self) -> tp.Optional[PhasarIterIDESolverStats]:
        return self._solver_stats_taint_jf1

    @property
    def solver_stats_taint_jf2(self) -> tp.Optional[PhasarIterIDESolverStats]:
        return self._solver_stats_taint_jf2

    @property
    def solver_stats_typestate_jf1(
        self
    ) -> tp.Optional[PhasarIterIDESolverStats]:
        return self._solver_stats_typestate_jf1

    @property
    def solver_stats_typestate_jf2(
        self
    ) -> tp.Optional[PhasarIterIDESolverStats]:
        return self._solver_stats_typestate_jf2

    @property
    def solver_stats_lca_jf1(self) -> tp.Optional[PhasarIterIDESolverStats]:
        return self._solver_stats_lca_jf1

    @property
    def solver_stats_lca_jf2(self) -> tp.Optional[PhasarIterIDESolverStats]:
        return self._solver_stats_lca_jf2
