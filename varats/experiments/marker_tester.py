"""
Instrument the generated binary with print markers to show region entry/exits.
"""

from plumbum import local

from benchbuild.experiment import Experiment
from benchbuild.extensions import base
from benchbuild.extensions import compiler
from benchbuild.utils import run


class TraceBinaryCreator(base.Extension):
    """
    Create an additional binary with trace markers.
    """

    def __init__(self,
                 project,
                 experiment,
                 marker_type,
                 *extensions,
                 extra_ldflags=None,
                 config=None):
        self.project = project
        self.experiment = experiment
        self.marker_type = marker_type
        if extra_ldflags is None:
            self.extra_ldflags = []
        else:
            self.extra_ldflags = extra_ldflags

        super(TraceBinaryCreator, self).__init__(*extensions, config=config)

    def __call__(self,
                 command,
                 *args,
                 project=None,
                 rerun_on_error=True,
                 **kwargs):

        res = self.call_next(command, *args, **kwargs)

        for arg in args:
            if arg.endswith(".cpp"):
                src_file = arg
                break

        fake_file_name = src_file.replace(".cpp", "_fake.ll")

        clang_stage_1 = command["-stdlib=libc++", "-fvara-handleRM=High", "-S",
                                "-emit-llvm", "-o", fake_file_name, src_file]
        with run.track_execution(clang_stage_1, self.project,
                                 self.experiment) as _run:
            res.append(_run())

        opt = local["opt"]["-vara-HD", "-vara-trace", "-vara-trace-RTy=high",
                           "-vara-trace-MTy={MType}".format(
                               MType=self.marker_type
                           ), "-S", "-o", "traced.ll", fake_file_name]
        with run.track_execution(opt, self.project, self.experiment) as _run:
            res.append(_run())

        llc = local["llc"]["-filetype=obj", "-o", "traced.o", "traced.ll"]
        with run.track_execution(llc, self.project, self.experiment) as _run:
            res.append(_run())

        clang_stage_2 = command["-O2", "traced.o", self.
                                extra_ldflags, "-lSTrace", "-o",
                                src_file.replace(".cpp", "_traced")]
        with run.track_execution(clang_stage_2, self.project,
                                 self.experiment) as _run:
            res.append(_run())

        return res


class PrintMarkerInstTest(Experiment):
    """
    Instrumnet all highlight regions with print markers.
    """

    NAME = "PrintMarkerInstTest"

    def actions_for_project(self, project):
        project.compiler_extension = compiler.RunCompiler(project, self) \
            << TraceBinaryCreator(project, self, "Print")

        project.cflags = ["-fvara-handleRM=High"]

        project_actions = self.default_compiletime_actions(project)

        return project_actions


class PapiMarkerInstTest(Experiment):
    """
    Instrumnet all highlight regions with papi markers.
    """

    NAME = "PapiMarkerInstTest"

    def actions_for_project(self, project):
        project.compiler_extension = compiler.RunCompiler(
            project, self) << TraceBinaryCreator(
                project,
                self,
                "Papi",
                extra_ldflags=["-stdlib=libc++", "-lpthread", "-lpapi"])

        project.cflags = ["-fvara-handleRM=High"]

        project_actions = self.default_compiletime_actions(project)

        return project_actions
