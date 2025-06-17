"""Project file for FastDownward."""
import os
import re
import typing as tp
from pathlib import Path

import benchbuild
import benchbuild as bb
from benchbuild.command import WorkloadSet, SourceRoot, ArgsToken
from benchbuild.utils.cmd import cmake, mkdir, pytest
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local, ProcessExecutionError

from varats.base.configuration import PlainCommandlineConfiguration
from varats.containers.containers import get_base_image, ImageBase
from varats.experiment.workload_util import (
    WorkloadCategory,
    ConfigurationParameterRenderer,
    RSBinary,
)
from varats.paper.paper_config import PaperConfigSpecificGit
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    BinaryType,
    ProjectBinaryWrapper,
    get_local_project_repo,
    get_tagged_commits,
    verify_binaries,
    RevisionBinaryMap,
)
from varats.project.sources import FeatureSource
from varats.project.varats_command import VCommand
from varats.project.varats_project import VProject
from varats.provider.release.release_provider import (
    ReleaseProviderHook,
    ReleaseType,
)
from varats.utils.config import get_config, get_extra_config_options
from varats.utils.git_util import FullCommitHash, ShortCommitHash, GitFileSource
from varats.utils.settings import bb_cfg


class _FDParameterRenderer:

    STR_REPRESENTATIONS = {
        "allSystems": "ALL_TRANSITION_SYSTEMS",
        "allSystemsWithFixpoint": "ALL_TRANSITION_SYSTEMS_WITH_FIXPOINT",
        "twoSystems": "TWO_TRANSITION_SYSTEMS",
        "blind": "blind()",
        "max": "hmax()",
        "canonicalPDB": "cpdbs()",
        "landmarkCut": "lmcut()",
        "bisimulation": "shrink_bisimulation()",
        "RHWLM": "lm_rhw",
        "exhaustiveLM": "lm_exhaust",
        "zhuGivanLM": "lm_zg",
        "hmLM": "lm_hm",
        "resonableOrders": "reasonable_orders",
        "onlyCausalLMs": "only_causal_landmarks",
        "conjunctiveLMs": "conjunctive_landmarks",
        "noOrders": "use_orders",
        "pdbMaxSize": "pdb_max_size",
        "collectionMaxSize": "collection_max_size",
        "numSamples": "num_samples",
        "minImprovement": "min_improvement",
        "random": "random_seed"
    }

    def __init__(self, *default_args: str) -> None:
        self.__default_args = default_args

    def __render_option(
        self, options: tp.Dict[str, tp.Union[int, bool]], to_render: str
    ) -> str:
        if to_render in options:
            options.pop(to_render)
            return self.STR_REPRESENTATIONS.get(to_render, "")

        return ""

    def _render_lm_factory_arg(
        self, options: tp.Dict[str, tp.Union[int, bool]], arg: str
    ) -> str:
        val = options.pop(arg, False)
        return f"{self.STR_REPRESENTATIONS[arg]}={str(val).lower()}"

    def _render_lm_count(
        self, options: tp.Dict[str, tp.Union[int, bool]]
    ) -> str:
        rendered = "landmark_sum(lm_factory="

        if "reasonableOrders" in options:
            rendered += "lm_reasonable_orders_hps("

        # Render factory used
        # Different factories support a different subset of the arguments
        factory = ""
        factory_args = []
        if "exhaustiveLM" in options:
            factory = "exhaustiveLM"
            # Exhaustive supports causalLMs
            factory_args.append("onlyCausalLMs")
        elif "hmLM" in options:
            factory = "hmLM"
            # mLM supports conjunctive and useOrders
            factory_args.append("noOrders")
            factory_args.append("conjunctiveLMs")
        elif "RHWLM" in options:
            factory = "RHWLM"
            # RHW supports causal and useOrders
            factory_args.append("noOrders")
            factory_args.append("onlyCausalLMs")
        elif "zhuGivanLM" in options:
            factory = "zhuGivanLM"
            # zg supports useOrders
            factory_args.append("noOrders")
        else:
            raise NotImplementedError("Landmark factory not supported")

        rendered += self.__render_option(options, factory)
        rendered += f"({','.join([self._render_lm_factory_arg(options, arg) for arg in factory_args])})"

        if "reasonableOrders" in options:
            rendered += ")"
            options.pop("reasonableOrders")

        rendered += ")"

        return rendered

    def _render_iPDB(self, options: tp.Dict[str, tp.Union[int, bool]]) -> str:
        rendered = "ipdb(max_time=infinity,"

        rendered += "max_time_dominance_pruning=0.0,"

        ipdb_options = [
            "pdbMaxSize", "collectionMaxSize", "numSamples", "minImprovement",
            "random"
        ]

        ipdb_args = []

        for arg in ipdb_options:
            ipdb_args.append(f"{self.STR_REPRESENTATIONS[arg]}={options[arg]}")
            options.pop(arg)

        rendered += ",".join(ipdb_args)

        rendered += ")"

        return rendered

    def _render_merge_and_shrink(
        self, options: tp.Dict[str, tp.Union[int, bool]]
    ) -> str:
        random_str = f"random_seed={options.get('random', 1)}"

        rendered = "merge_and_shrink("

        rendered += f"label_reduction=exact(before_shrinking={str(options.get('beforeShrinking',False)).lower()},before_merging={str(options.get('beforeMerging',False)).lower()},method="
        options.pop("beforeShrinking", None)
        options.pop("beforeMerging", None)

        methods = ["allSystems", "allSystemsWithFixpoint", "twoSystems"]

        for method in methods:
            rendered += self.__render_option(options, to_render=method)

        # End label_reduction=...
        rendered += f",{random_str})"

        # Shrink Strategy
        rendered += ",shrink_strategy="

        rendered += self.__render_option(options, to_render="bisimulation")
        if "fPreserving" in options:
            options.pop("fPreserving")
            rendered += f"shrink_fh({random_str})"

        # Add linear merge strategy
        rendered += f",merge_strategy=merge_precomputed(merge_tree=linear({random_str}))"

        # End merge_and_shrink...
        rendered += ")"

        return rendered

    def _render_heuristic(
        self, options: tp.Dict[str, tp.Union[int, bool]]
    ) -> str:
        rendered = ""

        # Simple cases
        simple_heuristics = ["blind", "max", "canonicalPDB", "landmarkCut"]

        for h in simple_heuristics:
            rendered += self.__render_option(options, to_render=h)

        # Merge and Shrink heuristic
        if "mergeAndShrink" in options:
            options.pop("mergeAndShrink")

            rendered += self._render_merge_and_shrink(options)

        # LMCount
        if "landmarkCount" in options:
            options.pop("landmarkCount")

            rendered += self._render_lm_count(options)

        # iPDB
        if "iPDB" in options:
            options.pop("iPDB")

            rendered += self._render_iPDB(options)

        return rendered

    def unrendered(self) -> str:
        return f"<params>"

    def render_internal(self, requested_options):
        options_dict: tp.Dict[str, tp.Union[int, bool]] = {}

        for option in requested_options:
            if "=" in option:
                option, value = option.split("=", 1)
                options_dict[option] = int(value)
            else:
                options_dict[option] = True

        # Convert options to specific FD required Syntax
        params = "astar("

        # Render heuristics
        params += self._render_heuristic(options_dict)

        params += ")"

        if len(options_dict) > 0:
            print("There were unprocessed options:")
            for option in options_dict.keys():
                print(f"\t{option}: {options_dict[option]}")

        return params

    def rendered(self, project: VProject, **kwargs: tp.Any) -> str:
        if not isinstance(project, FastDownward):
            raise NotImplementedError(
                f"This renderer must not be used for any project other than FastDownward"
            )

        requested_options = set(get_extra_config_options(project))
        if get_config(project, PlainCommandlineConfiguration) is None:
            requested_options = set(self.__default_args)

        params = self.render_internal(requested_options)

        return [params]


def _fd_config_params():
    return ArgsToken.make_token(_FDParameterRenderer())


_FDConfigParams = _fd_config_params


class FastDownward(VProject, ReleaseProviderHook):
    """Planning tool FastDownward (fetched by Git)"""

    __PlanningFilesSource = GitFileSource(
        "https://github.com/aibasel/downward-benchmarks", "planning-benchmarks",
        "8302319bb3", [
            "sokoban-sat08-strips/domain.pddl",
            "sokoban-sat08-strips/p01.pddl",
            "data-network-opt18-strips/domain.pddl",
            "data-network-opt18-strips/p05.pddl",
        ]
    )

    __PlanningProblems = {
        "sokoban-sat08": [
            "sokoban-sat08-strips/domain.pddl", "sokoban-sat08-strips/p01.pddl"
        ],
        "data-network-opt18": [
            "data-network-opt18-strips/domain.pddl",
            "data-network-opt18-strips/p05.pddl"
        ]
    }

    NAME = 'FastDownward'
    GROUP = 'cpp_projects'
    DOMAIN = ProjectDomains.PLANNING

    SOURCE = [
        PaperConfigSpecificGit(
            project_name="FastDownward",
            remote="https://github.com/aibasel/downward.git",
            local="FastDownward",
            refspec="origin/HEAD",
            limit=None,
            shallow=False
        ),
        FeatureSource(),
        __PlanningFilesSource,
    ]

    WORKLOADS = {
        WorkloadSet(WorkloadCategory.EXAMPLE): [
            VCommand(
                SourceRoot("FastDownward") / RSBinary("FDDriverPy"),
                "planning-benchmarks/sokoban-sat08-strips-domain.pddl",
                "planning-benchmarks/sokoban-sat08-strips-p01.pddl",
                "--search",
                _FDConfigParams(),
                label="sokoban-sat08-py"
            ),
            VCommand(
                SourceRoot("FastDownward") / RSBinary("downward"),
                "--search",
                _FDConfigParams(),
                redirect_stdin=SourceRoot("planning-benchmarks") /
                "sokoban-sat08.sas",
                label="sokoban-sat08"
            )
        ],
        WorkloadSet(WorkloadCategory.MEDIUM): [
            VCommand(
                SourceRoot("FastDownward") / RSBinary("FDDriverPy"),
                "planning-benchmarks/data-network-opt18-strips-domain.pddl",
                "planning-benchmarks/data-network-opt18-strips-p05.pddl",
                "--search",
                _FDConfigParams(),
                label="data-network-opt18-py"
            ),
            VCommand(
                SourceRoot("FastDownward") / RSBinary("downward"),
                "--search",
                _FDConfigParams(),
                label="data-network-opt18",
                redirect_stdin=SourceRoot("planning-benchmarks") /
                "data-network-opt18.sas"
            )
        ]
    }

    CONTAINER = get_base_image(
        ImageBase.DEBIAN_12
    ).run('apt', 'install', '-y', 'cmake', 'g++', 'git', 'make', 'python3')

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(
            get_local_project_repo(FastDownward.NAME)
        )

        binary_map.specify_binary(
            'fast-downward.py',
            BinaryType.EXECUTABLE,
            override_binary_name="FDDriverPy"
        )
        binary_map.specify_binary('build/bin/downward', BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def prepare_test_environment(self) -> None:
        """
        Prepare the test environment for fast downward.

        Note:
            Fast Downward requires tests to be built to also collect the test
            names.
        """
        version_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)
        with local.cwd(version_source):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                build_script = benchbuild.utils.cmd["./build.py"]
                bb.watch(build_script
                        )("--all", "-j", get_number_of_jobs(bb_cfg()))

    def build_tests(self) -> None:
        """
        Builds the test environment for fast downward.

        Note:
            Fast Downward requires tests to be built to also collect the test
            names. Therefore, this method just calls the prepare method.
        """
        self.prepare_test_environment()

    def run_testsuite(
        self,
        test_report_path: tp.Optional[Path] = None,
        tests_to_run: tp.Optional[tp.Iterable[str]] = None
    ) -> bool:
        """
        Run the test suite for fast downward.

        Args:
            test_report_path: Path to store the detailed test results in.
            tests_to_run: List of test cases to run. If None, all tests will be
                          run.

        Returns:
            True if all tests passed, False otherwise.
        """
        if tests_to_run is None:
            # In case no test names are given, we run all tests
            tests_to_run = []

        version_source = local.path(self.source_of(self.primary_source))

        # "test_commandline_args" requires the external plan validator VAL
        # to be installed.
        # Since this is usually not the case, we skip this test
        test_runner = pytest["-k", "not test_commandline_args"]

        if test_report_path:
            test_runner = test_runner["--junitxml", test_report_path]

        with local.cwd(version_source):
            ret_code: int
            test_args = ["driver/tests.py", *tests_to_run]
            ret_code, _, _ = bb.watch(test_runner[test_args])()

        return ret_code == 0

    def get_test_names(self) -> tp.Iterable[str]:
        """
        Get the test names for the project.

        Returns:
            A list of test names available in the project.
        """
        pytest_cmd = pytest["--collect-only", "-q", "driver/tests.py"]

        try:
            with local.cwd(self.source_of(self.primary_source)):
                _, output, _ = bb.watch(pytest_cmd)()
        except ProcessExecutionError:
            return []

        # For some reason even during the collection phase, FastDownward
        # is executed.
        # Therefore, some output from the planning tool is included in stdout
        # All test name lines start with "driver/tests.py::"
        test_names = [
            line.strip()
            for line in output.splitlines()
            if line.startswith("driver/tests.py::")
        ]

        return test_names

    def compile(self) -> None:
        """Compile the project."""
        version_source = local.path(self.source_of(self.primary_source))

        c_compiler = bb.compiler.cc(self)
        cxx_compiler = bb.compiler.cxx(self)

        mkdir("-p", version_source / "build")

        with local.cwd(version_source / "build"):
            with local.env(CC=str(c_compiler), CXX=str(cxx_compiler)):
                bb.watch(cmake)("../src")

            bb.watch(cmake)("--build", ".", "-j", get_number_of_jobs(bb_cfg()))

        with local.cwd(version_source):
            verify_binaries(self)
            # Create Symlink such that FD Python script works properly
            local["mkdir"]("-p", "builds")
            ln = local["ln"]
            ln("-rsf", "build", "builds/release")

        # Translate Planning problems into .sas files such that we can interact
        # with them directly through the 'downward' binary
        translate = local[version_source / "build/bin/translate/translate.py"]
        planning_problems_dir = self.__PlanningFilesSource.version(
            self.builddir
        )
        with local.cwd(planning_problems_dir):
            for problem, inputs in self.__PlanningProblems.items():
                inputs = [f.replace(os.sep, "-") for f in inputs]
                bb.watch(translate)(*inputs, "--sas-file", f"{problem}.sas")

    def recompile(self) -> None:
        """Recompile the project."""
        version_source = local.path(self.source_of(self.primary_source))

        with local.cwd(version_source / "build"):
            bb.watch(cmake)("--build", ".", "-j", get_number_of_jobs(bb_cfg()))

    @classmethod
    def get_release_revisions(
        cls, release_type: ReleaseType
    ) -> tp.List[tp.Tuple[FullCommitHash, str]]:
        repo_loc = get_local_project_repo(cls.NAME)
        with local.cwd(repo_loc):
            # Before 2019_07, there were no real releases, but the following
            # commits were identified as suitable.
            release_commits = {
                (
                    FullCommitHash('e4eb64c613ae34b97ab9409deac5331ec2ce5e43'),
                    'release-16.07.0'
                ),
                (
                    FullCommitHash('91f44fa59ea57014a7769062a92aa752f503128e'),
                    'release-17.01.0'
                ),
                (
                    FullCommitHash('363e2fc9a8b7adb48b4c30e929097798928c7370'),
                    'release-17.07.0'
                ),
                (
                    FullCommitHash('0e8acd2f2613e032040dc6b6d4bf1926848aa4cb'),
                    'release-18.01.0'
                ),
                (
                    FullCommitHash('dd7ddfeea72a699d381dce35657d683259be77c0'),
                    'release-18.07.0'
                ),
                (
                    FullCommitHash('2cc2a66e8073a73571e0a37cd806380f13751a7c'),
                    'release-19.01.0'
                )
            }

            tagged_commits = get_tagged_commits(cls.NAME)
            release_commits = release_commits.union({
                (FullCommitHash(h), tag)
                for h, tag in tagged_commits
                if re.match("^release-[0-9]+\\.[0-9]+\\.[0-9]+$", tag)
            })

            return list(release_commits)
