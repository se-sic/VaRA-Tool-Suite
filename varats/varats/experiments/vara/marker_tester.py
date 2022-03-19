"""Instrument the generated binary with print markers to show region
entry/exits."""

import typing as tp

from benchbuild import Experiment, Project
from benchbuild.extensions import base, compiler
from benchbuild.utils import run
from benchbuild.utils.actions import Step
from benchbuild.utils.settings import Configuration
from plumbum import local
from plumbum.commands.base import BoundCommand


class TraceBinaryCreator(base.Extension):  # type: ignore
    """Create an additional binary with trace markers."""

    def __init__(
        self,
        project: Project,
        experiment: Experiment,
        marker_type: str,
        *extensions: tp.List[base.Extension],
        extra_ldflags: tp.Optional[tp.List[str]] = None,
        config: tp.Optional[Configuration] = None
    ) -> None:
        self.project = project
        self.experiment = experiment
        self.marker_type = marker_type
        if extra_ldflags is None:
            self.extra_ldflags: tp.List[str] = []
        else:
            self.extra_ldflags = extra_ldflags

        super().__init__(*extensions, config=config)

    def __call__(
        self,
        command: BoundCommand,
        *args: tp.Any,
        project: Project = None,
        rerun_on_error: bool = True,
        **kwargs: tp.Any
    ) -> tp.List[run.RunInfo]:

        res: tp.List[run.RunInfo] = self.call_next(command, *args, **kwargs)

        for arg in args:
            if arg.endswith(".cpp"):
                src_file = arg
                break

        fake_file_name = src_file.replace(".cpp", "_fake.ll")

        clang_stage_1 = command[self.extra_ldflags, "-Qunused-arguments",
                                "-fvara-handleRM=High", "-S", "-emit-llvm",
                                "-o", fake_file_name, src_file]
        with run.track_execution(
            clang_stage_1, self.project, self.experiment
        ) as _run:
            res.append(_run())

        opt = local["opt"]["-vara-HD", "-vara-trace", "-vara-trace-RTy=High",
                           f"-vara-trace-MTy={self.marker_type}", "-S", "-o",
                           "traced.ll", fake_file_name]
        with run.track_execution(opt, self.project, self.experiment) as _run:
            res.append(_run())

        llc = local["llc"]["-filetype=obj", "-o", "traced.o", "traced.ll"]
        with run.track_execution(llc, self.project, self.experiment) as _run:
            res.append(_run())

        clang_stage_2 = command["-O2", "traced.o", self.extra_ldflags,
                                "-lSTrace", "-o",
                                src_file.replace(".cpp", "_traced")]
        with run.track_execution(
            clang_stage_2, self.project, self.experiment
        ) as _run:
            res.append(_run())

        return res


class PrintMarkerInstTest(Experiment):  # type: ignore
    """Instrument all highlight regions with print markers."""

    NAME = "PrintMarkerInstTest"

    def actions_for_project(self, project: Project) -> tp.MutableSequence[Step]:
        """
        Defines the actions, which should be run on a project.

        Args:
            project: the project we run our `Experiment` on
        """
        project.compiler_extension = compiler.RunCompiler(
            project, self
        ) << TraceBinaryCreator(project, self, "Print")

        project.cflags = ["-fvara-handleRM=High"]

        project_actions: tp.MutableSequence[
            Step] = self.default_compiletime_actions(project)

        return project_actions


class PapiMarkerInstTest(Experiment):  # type: ignore
    """Instrument all highlight regions with papi markers."""

    NAME = "PapiMarkerInstTest"

    def actions_for_project(self, project: Project) -> tp.MutableSequence[Step]:
        """
        Defines the actions, which should be run on a project.

        Args:
            project: the project we run our `Experiment` on
        """
        project.compiler_extension = compiler.RunCompiler(
            project, self
        ) << TraceBinaryCreator(
            project,
            self,
            "Papi",
            extra_ldflags=["-stdlib=libc++", "-lpthread", "-lpapi"]
        )

        project.cflags = ["-fvara-handleRM=High"]

        project_actions: tp.MutableSequence[
            Step] = self.default_compiletime_actions(project)

        return project_actions


class CheckMarkerInstTest(Experiment):  # type: ignore
    """Instrument all highlight regions with check markers."""

    NAME = "CheckMarkerInstTest"

    def actions_for_project(self, project: Project) -> tp.MutableSequence[Step]:
        """
        Defines the actions, which should be run on a project.

        Args:
            project: the project we run our `Experiment` on
        """
        project.compiler_extension = compiler.RunCompiler(
            project, self
        ) << TraceBinaryCreator(project, self, "Check")

        project.cflags = ["-fvara-handleRM=High"]

        project_actions: tp.MutableSequence[
            Step] = self.default_compiletime_actions(project)

        return project_actions
