"""Implements the SZZUnleashed experiment."""

import json
import typing as tp
from datetime import datetime
from pathlib import Path

import yaml
from benchbuild import Project, source
from benchbuild.experiment import ProjectT
from benchbuild.utils import actions
from benchbuild.utils.cmd import java, mkdir
from plumbum import local

from varats.base.version_header import VersionHeader
from varats.data.reports.szz_report import (
    SZZReport,
    SZZUnleashedReport,
    SZZTool,
)
from varats.experiment.experiment_util import (
    VersionExperiment,
    ExperimentHandle,
    create_default_analysis_failure_handler,
    get_varats_result_folder,
    exec_func_with_pe_error_handler,
)
from varats.provider.bug.bug_provider import BugProvider
from varats.report.report import FileStatusExtension as FSE
from varats.report.report import ReportSpecification
from varats.tools.research_tools.szz_unleashed import SZZUnleashed
from varats.utils.settings import bb_cfg


class PrepareSZZUnleashedData(actions.Step):  # type: ignore
    """
    Prepare data about bug fixing commits.

    This information is needed by the SZZUnleashed tool.
    """

    NAME = "PrepareSZZUnleashedData"
    DESCRIPTION = "Prepares data needed for running SZZUnleashed."

    def __init__(self, project: Project):
        super().__init__(obj=project, action_fn=self.prepare_szz_data)

    def prepare_szz_data(self) -> actions.StepResult:
        """Prepare data needed for running SZZUnleashed."""
        project: Project = self.obj
        run_dir = Path(project.source_of_primary).parent

        bug_provider = BugProvider.get_provider_for_project(project)
        bugs = bug_provider.find_pygit_bugs()

        fixers_dict = {}
        for bug in bugs:
            # SZZUnleashed uses some strange timezone format that cannot be
            # produced by datetime, so we just fake it.
            def fix_date(date: datetime) -> str:
                return str(date) + " +0000"

            commitdate = fix_date(
                datetime.fromtimestamp(bug.fixing_commit.commit_time)
            )
            creationdate = fix_date(
                bug.creation_date
            ) if bug.creation_date else commitdate
            resolutiondate = fix_date(
                bug.resolution_date
            ) if bug.resolution_date else commitdate
            fixers_dict[str(bug.fixing_commit.id)] = {
                "hash": str(bug.fixing_commit.id),
                "commitdate": commitdate,
                "creationdate": creationdate,
                "resolutiondate": resolutiondate
            }

        with (run_dir / "issue_list.json").open("w") as issues_file:
            json.dump(fixers_dict, issues_file, indent=2)

        return actions.StepResult.OK


class RunSZZUnleashed(actions.Step):  # type: ignore
    """Run the SZZUnleashed tool."""
    NAME = "RunSZZUnleashed"
    DESCRIPTION = "Run SZZUnleashed on a project"

    def __init__(self, project: Project, experiment_handle: ExperimentHandle):
        super().__init__(obj=project, action_fn=self.run_szz)
        self.__experiment_handle = experiment_handle

    def run_szz(self) -> actions.StepResult:
        """Prepare data needed for running SZZUnleashed."""
        project: Project = self.obj
        run_dir = Path(project.source_of_primary).parent
        szzunleashed_jar = SZZUnleashed.install_location(
        ) / SZZUnleashed.get_jar_name()

        varats_result_folder = get_varats_result_folder(project)

        with local.cwd(run_dir):
            run_cmd = java["-jar",
                           str(szzunleashed_jar), "-d", "1", "-i",
                           str(run_dir / "issue_list.json"), "-r",
                           project.source_of_primary]
            exec_func_with_pe_error_handler(
                run_cmd,
                create_default_analysis_failure_handler(
                    self.__experiment_handle, project, SZZUnleashedReport,
                    Path(varats_result_folder)
                )
            )

        return actions.StepResult.OK


class CreateSZZUnleashedReport(actions.Step):  # type: ignore
    """Create a SZZReport from the data generated by SZZUnleashed."""
    NAME = "CreateSZZUnleashedReport"
    DESCRIPTION = "Create a report from SZZUnleashed data"

    def __init__(self, project: Project):
        super().__init__(obj=project, action_fn=self.create_report)

    def create_report(self) -> actions.StepResult:
        """Create a report from SZZUnleashed data."""
        project = self.obj

        varats_result_folder = get_varats_result_folder(project)

        run_dir = Path(project.source_of_primary).parent
        with (run_dir / "results" /
              "fix_and_introducers_pairs.json").open("r") as result_json:
            szz_result = json.load(result_json)

        bugs: tp.Dict[str, tp.Set[str]] = {}
        # entries are lists of the form [<fix>, <introducing>]
        for result_entry in szz_result:
            bugs.setdefault(result_entry[0], set())
            bugs[result_entry[0]].add(result_entry[1])
        raw_szz_report = {
            "szz_tool": SZZTool.SZZ_UNLEASHED.tool_name,
            "bugs": {k: sorted(list(v)) for k, v in bugs.items()}
        }

        result_file = SZZUnleashedReport.get_file_name(
            "SZZUnleashed",
            project_name=str(project.name),
            binary_name="none",  # we don't rely on binaries in this experiment
            project_revision=project.version_of_primary,
            project_uuid=str(project.run_uuid),
            extension_type=FSE.SUCCESS
        )

        with open(f"{varats_result_folder}/{result_file}", "w") as yaml_file:
            yaml_file.write(
                yaml.dump_all([
                    VersionHeader.from_version_number("SZZReport",
                                                      1).get_dict(),
                    raw_szz_report
                ],
                              explicit_start=True,
                              explicit_end=True)
            )

        return actions.StepResult.OK


class SZZUnleashedExperiment(VersionExperiment, shorthand="SZZUnleashed"):
    """
    Generates a SZZUnleashed report.

    This experiment should be run only on one (preferably the newest) revision
    of a project.
    """

    NAME = "SZZUnleashed"

    REPORT_SPEC = ReportSpecification(SZZReport)

    @classmethod
    def sample(cls, prj_cls: ProjectT) -> tp.List[source.VariantContext]:
        variants = list(source.product(*prj_cls.SOURCE))
        return [source.context(*variants[0])]

    def actions_for_project(self, project: Project) -> tp.List[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""

        analysis_actions = [
            PrepareSZZUnleashedData(project),
            RunSZZUnleashed(project, self.get_handle()),
            CreateSZZUnleashedReport(project),
            actions.Clean(project)
        ]

        return analysis_actions
