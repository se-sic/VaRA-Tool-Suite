"""
Execute showcase cpp examples with VaRA's taint analysis.

We run the analysis on exemplary cpp files. The cpp examples can be found in the
https://github.com/se-passau/vara-perf-tests repository. The result LLVM IR is
then parsed into an file contaning only the instructions tainted by the commit
regions of the cpp file.
"""

import typing as tp
from typing import List

import benchbuild.utils.actions as actions
from benchbuild import Project
from benchbuild.utils.cmd import FileCheck, echo, rm
from plumbum import ProcessExecutionError

from varats.data.report import FileStatusExtension as FSE
from varats.data.reports.taint_report import TaintPropagationReport as TPR
from varats.experiments.vara.vara_full_mtfa import VaRATaintPropagation
from varats.utils.experiment_util import (
    PEErrorHandler,
    exec_func_with_pe_error_handler,
)
from varats.utils.settings import bb_cfg


class ParseAndValidateVaRAOutput(actions.Step):  # type: ignore
    """Read the LLVM IR, store the tainted ones and pipe them into FileCheck."""

    NAME = "ParseAndValidateVaRAOutput"
    DESCRIPTION = "Parses VaRA's LLVM IR into only the tainted instructions."\
        + "Also the parsed results get validated with LLVM FileCheck."

    RESULT_FOLDER_TEMPLATE = "{result_dir}/{project_dir}"

    FC_FILE_SOURCE_DIR = "{tmp_dir}/{project_src}/{project_name}"
    EXPECTED_FC_FILE = "{binary_name}.txt"

    def __init__(self, project: Project):
        super().__init__(obj=project, action_fn=self.filecheck)

    def filecheck(self) -> actions.StepResult:
        """
        Compare the generated results against the expected result.

        First the result files are read, printed and piped into FileCheck.
        """

        if not self.obj:
            return
        project = self.obj
        # Define the output directory.
        result_folder = self.RESULT_FOLDER_TEMPLATE.format(
            result_dir=str(bb_cfg()["varats"]["outfile"]),
            project_dir=str(project.name)
        )

        # The temporary directory the project is stored under
        tmp_repo_dir = self.FC_FILE_SOURCE_DIR.format(
            tmp_dir=str(bb_cfg()["tmp_dir"]),
            project_src=str(project.SRC_FILE),
            project_name=str(project.name)
        )

        timeout_duration = '3h'

        for binary in project.binaries:
            # get the file name of the JSON Output
            old_result_file = TPR.get_file_name(
                project_name=str(project.name),
                binary_name=binary.name,
                project_version=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FSE.Success,
                file_ext=".ll"
            )

            # Define output file name of failed runs
            error_file = "vara-" + TPR.get_file_name(
                project_name=str(project.name),
                binary_name=binary.name,
                project_version=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FSE.Failed,
                file_ext=TPR.FILE_TYPE
            )

            # The file name of the text file with the expected filecheck regex
            expected_file = self.EXPECTED_FC_FILE.format(
                binary_name=binary.name
            )

            # write new result into a taint propagation report
            result_file = "vara-" + TPR.get_file_name(
                project_name=str(project.name),
                binary_name=binary.name,
                project_version=project.version_of_primary,
                project_uuid=str(project.run_uuid),
                extension_type=FSE.Success
            )

            tainted_instructions = []

            # parse the old result file
            with open(
                "{res_folder}/{old_res_file}".format(
                    res_folder=result_folder, old_res_file=old_result_file
                )
            ) as file:
                # each instruction still contains '\n' at the end
                instructions: List[str] = file.readlines()
                for inst in instructions:
                    if '{getenv' in inst:
                        tainted_instructions.append(inst)

            # remove the no longer needed llvm ir files
            rm(
                "{res_folder}/{old_res_file}".format(
                    res_folder=result_folder, old_res_file=old_result_file
                )
            )

            # validate the result with filecheck
            array_string = ""
            for inst in tainted_instructions:
                array_string.join(inst)

            file_check_cmd = FileCheck["{fc_dir}/{fc_exp_file}".format(
                fc_dir=tmp_repo_dir, fc_exp_file=expected_file
            )]

            cmd_chain = (
                echo[array_string] | file_check_cmd > "{res_folder}/{res_file}".
                format(res_folder=result_folder, res_file=result_file)
            )

            try:
                exec_func_with_pe_error_handler(
                    cmd_chain,
                    PEErrorHandler(result_folder, error_file, timeout_duration)
                )
            # remove the success file on error in the filecheck.
            except ProcessExecutionError:
                rm(
                    "{res_folder}/{res_file}".format(
                        res_folder=result_folder, res_file=result_file
                    )
                )


class VaRAFileCheckTaintPropagation(VaRATaintPropagation):
    """
    Generates a inter-procedural data flow analysis (IFDS) on a project's
    binaries and propagates commit regions similar to the VaraTaintPropagation
    experiment.

    The result however gets parsed, that FileCheck can validate the propagation
    against the expected result.
    """

    NAME = "VaRAFileCheckTaintPropagation"

    REPORT_TYPE = TPR

    def actions_for_project(self, project: Project) -> tp.List[actions.Step]:
        """Returns the specified steps to run the project(s) specified in the
        call in a fixed order."""
        analysis_actions = super().actions_for_project(project)

        # remove the clean step from the other experiment
        del analysis_actions[-1]

        analysis_actions.append(ParseAndValidateVaRAOutput(project))
        analysis_actions.append(actions.Clean(project))

        return analysis_actions
