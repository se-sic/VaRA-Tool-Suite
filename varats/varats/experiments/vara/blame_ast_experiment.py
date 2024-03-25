"""
Implements the blame AST experiment.

The experiment compares AST based blame annotations to line based ones.
"""

import fnmatch
import os
import typing as tp
from pathlib import Path

from benchbuild import Project
from benchbuild.utils import actions
from benchbuild.utils.cmd import opt

import varats.experiments.vara.blame_experiment as BE
from varats.data.reports.blame_annotations import ASTBlameReport as BAST
from varats.data.reports.blame_annotations import BlameAnnotations as BA
from varats.data.reports.blame_annotations import compare_blame_annotations
from varats.experiment.experiment_util import (
    ExperimentHandle,
    VersionExperiment,
    create_default_analysis_failure_handler,
    create_default_compiler_error_handler,
    create_new_success_result_filepath,
    exec_func_with_pe_error_handler,
    get_varats_result_folder,
    wrap_unlimit_stack_size,
)
from varats.experiment.wllvm import (
    BCFileExtensions,
    _create_default_bc_file_creation_actions,
    get_cached_bc_file_path,
)
from varats.project.project_util import get_local_project_git_paths
from varats.project.varats_project import VProject
from varats.report.report import ReportSpecification


class BlameAnnotationGeneration(actions.ProjectStep):  #type: ignore
    """Generate blame annotation report."""

    NAME = "BlameAnnotationGeneration"
    DESCRIPTION = "Generates report with debug and IInfo blame "\
                  "with -vara-BA of VaRA."

    project: VProject

    def __init__(self, project: Project, experiment_handle: ExperimentHandle):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle

    def __call__(self) -> actions.StepResult:
        return self.analyze()

    def analyze(self) -> actions.StepResult:
        """
        This step performs the actual analysis with the correct command line
        flags.

        Flags used:
            * -vara-BA: to run a commit flow report
            * -yaml-report-outfile=<path>: specify the path to store the results
        """

        for binary in self.project.binaries:
            # Add to the user-defined path for saving the results of the
            # analysis also the name and the unique id of the project of every
            # run.
            result_file = create_new_success_result_filepath(
                self.__experiment_handle, BA, self.project, binary
            )

            opt_params = [
                "--enable-new-pm=0", "-vara-BD", "-vara-BA",
                "-vara-init-commits", "-vara-rewriteMD",
                "-vara-git-mappings=" + ",".join([
                    f'{repo}:{path}' for repo, path in
                    get_local_project_git_paths(self.project.name).items()
                ]), "-vara-use-phasar", f"-vara-report-outfile={result_file}",
                get_cached_bc_file_path(
                    self.project, binary, [
                        BCFileExtensions.NO_OPT, BCFileExtensions.TBAA,
                        BCFileExtensions.BLAME
                    ]
                )
            ]

            run_cmd = opt[opt_params]

            run_cmd = wrap_unlimit_stack_size(run_cmd)

            exec_func_with_pe_error_handler(
                run_cmd,
                create_default_analysis_failure_handler(
                    self.__experiment_handle, self.project, BA
                )
            )

        return actions.StepResult.OK


class BlameASTComparison(actions.ProjectStep):  #type: ignore
    """Compare BlameAnnotation reports of AST based annotations to line based
    ones."""

    NAME = "BlameASTComparison"
    DESCRIPTION = "Compares BlameAnnotation reports of AST based "\
                  "annotations to line based ones."

    project: VProject

    def __init__(
        self,
        project: Project,
        experiment_handle: ExperimentHandle,
    ):
        super().__init__(project=project)
        self.__experiment_handle = experiment_handle

    def __call__(self) -> actions.StepResult:
        return self.analyze()

    def analyze(self) -> actions.StepResult:
        """This step retrieves the two previously generated reports (with line
        based and AST based blame annotations) and compares them."""
        for binary in self.project.binaries:
            varats_result_folder = get_varats_result_folder(self.project)

            for file in os.listdir(varats_result_folder):
                if fnmatch.fnmatch(file, "LBA" + '*'):
                    line_filepath = Path(varats_result_folder / file)
                if fnmatch.fnmatch(file, "ASTBA" + '*'):
                    ast_filepath = Path(varats_result_folder / file)

            line_annotations = BA(line_filepath)
            ast_annotations = BA(ast_filepath)

            result_file = create_new_success_result_filepath(
                self.__experiment_handle, BAST, self.project, binary
            )

            ast_report = compare_blame_annotations(
                line_annotations, ast_annotations, result_file.full_path()
            )

            ast_report.print_yaml()

        return actions.StepResult.OK


class LineBasedBlameAnnotations(VersionExperiment, shorthand="LBA"):
    """Create a report containing all line based blame annotations."""

    NAME = "LineBasedBlameAnnotations"

    REPORT_SPEC = ReportSpecification(BA)

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        # Try, to build the project without optimizations to get more precise
        # blame annotations. Note: this does not guarantee that a project is
        # build without optimizations because the used build tool/script can
        # still add optimizations flags after the experiment specified cflags.
        project.cflags += ["-O1", "-Xclang", "-disable-llvm-optzns", "-g"]
        bc_file_extensions = [
            BCFileExtensions.NO_OPT,
            BCFileExtensions.TBAA,
            BCFileExtensions.BLAME,
        ]

        BE.setup_basic_blame_experiment(self, project, BA)
        # Compile with line based blame annotations
        analysis_actions = _create_default_bc_file_creation_actions(
            project,
            bc_file_extensions if bc_file_extensions else [],
            extraction_error_handler=create_default_compiler_error_handler(
                self.get_handle(), project, self.REPORT_SPEC.main_report
            )
        )
        # Generate blame annotation report
        analysis_actions.append(
            BlameAnnotationGeneration(project, self.get_handle())
        )

        return analysis_actions


class ASTBasedBlameAnnotations(VersionExperiment, shorthand="ASTBA"):
    """Create a report containing all line based blame annotations."""

    NAME = "ASTBasedBlameAnnotations"

    REPORT_SPEC = ReportSpecification(BA)

    def actions_for_project(
        self, project: Project
    ) -> tp.MutableSequence[actions.Step]:
        """
        Returns the specified steps to run the project(s) specified in the call
        in a fixed order.

        Args:
            project: to analyze
        """
        # Try, to build the project without optimizations to get more precise
        # blame annotations. Note: this does not guarantee that a project is
        # build without optimizations because the used build tool/script can
        # still add optimizations flags after the experiment specified cflags.
        project.cflags += ["-O1", "-Xclang", "-disable-llvm-optzns", "-g"]
        bc_file_extensions = [
            BCFileExtensions.NO_OPT,
            BCFileExtensions.TBAA,
            BCFileExtensions.BLAME,
        ]

        BE.setup_basic_blame_experiment(self, project, BA)
        # Compile with AST based blame annotations
        project.cflags += ["-fvara-ast-GB"]
        analysis_actions = _create_default_bc_file_creation_actions(
            project,
            bc_file_extensions if bc_file_extensions else [],
            extraction_error_handler=create_default_compiler_error_handler(
                self.get_handle(), project, self.REPORT_SPEC.main_report
            )
        )
        # Generate blame annotation report
        analysis_actions.append(
            BlameAnnotationGeneration(project, self.get_handle())
        )

        return analysis_actions


class BlameASTExperiment(VersionExperiment, shorthand="BASTE"):
    """
    Compares AST based blame annotations to line based ones.

    Requires previous runs of experiments 'LineBasedBlameAnnotations' and
    'ASTBasedBlameAnnotations'
    """

    NAME = "CompareASTBlame"

    REPORT_SPEC = ReportSpecification(BAST)

    def actions_for_project(
        self, project: VProject
    ) -> tp.MutableSequence[actions.Step]:

        # Generate AST blame report (comparison)
        analysis_actions: tp.MutableSequence[actions.Step] = [
            (BlameASTComparison(project, self.get_handle()))
        ]

        analysis_actions.append(actions.Clean(project))

        return analysis_actions
