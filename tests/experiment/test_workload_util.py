"""Test VaRA workload utilities."""
import unittest
from pathlib import Path

from benchbuild.command import Command, PathToken, RootRenderer
from benchbuild.source.base import Revision, Variant

import varats.experiment.workload_util as wu
from tests.helper_utils import run_in_test_environment, UnitTestFixtures
from varats.paper.paper_config import load_paper_config
from varats.projects.c_projects.xz import Xz
from varats.projects.perf_tests.feature_perf_cs_collection import (
    SynthIPTemplate,
    SynthIPRuntime,
)
from varats.utils.git_util import ShortCommitHash
from varats.utils.settings import vara_cfg

TT = PathToken.make_token(RootRenderer())


class TestWorkloadCategory(unittest.TestCase):

    def test_str(self) -> None:
        self.assertEqual(str(wu.WorkloadCategory.SMALL), "small")


class TestRevisionBinaryRenderer(unittest.TestCase):

    def test_unrendered(self) -> None:
        self.assertEqual(
            wu.RevisionBinaryRenderer("foo").unrendered(), "<binaryLocFor(foo)>"
        )

    def test_rendered(self) -> None:
        revision = Revision(Xz, Variant(Xz.SOURCE[0], "c5c7ceb08a"))
        project = Xz(revision=revision)
        binary_renderer = wu.RevisionBinaryRenderer("xz")
        self.assertEqual(binary_renderer.rendered(project), Path("src/xz/xz"))


class TestWorkloadCommands(unittest.TestCase):

    def test_workload_commands_tags(self) -> None:
        revision = Revision(Xz, Variant(Xz.SOURCE[0], "c5c7ceb08a"))
        project = Xz(revision=revision)
        binary = Xz.binaries_for_revision(ShortCommitHash("c5c7ceb08a"))[0]

        commands = wu.workload_commands(project, binary, [])
        self.assertEqual(len(commands), 2)

    def test_workload_commands_tags_selected(self) -> None:
        revision = Revision(Xz, Variant(Xz.SOURCE[0], "c5c7ceb08a"))
        project = Xz(revision=revision)
        binary = Xz.binaries_for_revision(ShortCommitHash("c5c7ceb08a"))[0]

        commands = wu.workload_commands(
            project, binary, [wu.WorkloadCategory.EXAMPLE]
        )
        self.assertEqual(len(commands), 1)

    def test_workload_commands_requires(self) -> None:
        revision = Revision(Xz, Variant(Xz.SOURCE[0], "c5c7ceb08a"))
        project = Xz(revision=revision)
        binary = Xz.binaries_for_revision(ShortCommitHash("c5c7ceb08a"))[0]

        commands = wu.workload_commands(
            project, binary, [wu.WorkloadCategory.EXAMPLE]
        )
        self.assertEqual(len(commands), 1)
        commands = wu.workload_commands(
            project, binary, [wu.WorkloadCategory.MEDIUM]
        )
        self.assertEqual(len(commands), 1)

    @run_in_test_environment(UnitTestFixtures.PAPER_CONFIGS)
    def test_workload_config_param_token(self) -> None:
        vara_cfg()['paper_config']['current_config'] = "test_config_ids"
        load_paper_config()

        revision = Revision(
            SynthIPRuntime, Variant(SynthIPRuntime.SOURCE[0], "7930350628"),
            Variant(SynthIPRuntime.SOURCE[1], "1")
        )
        project = SynthIPRuntime(revision=revision)
        binary = SynthIPRuntime.binaries_for_revision(
            ShortCommitHash("7930350628")
        )[0]

        commands = wu.workload_commands(
            project, binary, [wu.WorkloadCategory.SMALL]
        )
        self.assertEqual(len(commands), 1)
        command = commands[0]
        args = command.command.rendered_args(project=project)
        self.assertEquals(args, tuple(["-c"]))

    @run_in_test_environment(UnitTestFixtures.PAPER_CONFIGS)
    def test_workload_commands_requires_patch(self) -> None:
        vara_cfg()['paper_config']['current_config'] = "test_config_ids"
        load_paper_config()

        revision = Revision(
            SynthIPTemplate, Variant(SynthIPTemplate.SOURCE[0], "7930350628"),
            Variant(SynthIPTemplate.SOURCE[1], "1")
        )
        project = SynthIPTemplate(revision=revision)
        binary = SynthIPTemplate.binaries_for_revision(
            ShortCommitHash("7930350628")
        )[0]
        workloads = wu.workload_commands(project, binary, [])
        self.assertEqual(2, len(workloads))

    @run_in_test_environment(UnitTestFixtures.PAPER_CONFIGS)
    def test_workload_commands_requires_patch2(self) -> None:
        vara_cfg()['paper_config']['current_config'] = "test_config_ids"
        load_paper_config()

        revision = Revision(
            SynthIPTemplate, Variant(SynthIPTemplate.SOURCE[0], "7930350628"),
            Variant(SynthIPTemplate.SOURCE[1], "0")
        )
        project = SynthIPTemplate(revision=revision)
        binary = SynthIPTemplate \
            .binaries_for_revision(ShortCommitHash("7930350628"))[0]
        workloads = wu.workload_commands(project, binary, [])
        self.assertEqual(0, len(workloads))


class TestWorkloadFilenames(unittest.TestCase):

    def test_create_wl_specific_filename(self) -> None:
        base_name = "base"
        label = "myLabel"
        cmd = Command(TT / "bin" / "true", label=label)
        reps = 42
        file_suffix = ".json"

        filename = wu.create_workload_specific_filename(
            base_name, cmd, reps, file_suffix
        )

        self.assertEqual(Path("base_myLabel_42.json"), filename)

    def test_that_labels_contain_underscores_are_rejected(self) -> None:
        base_name = "base"
        forbidden_label = "my_label"
        cmd2 = Command(TT / "bin" / "true", label=forbidden_label)

        self.assertRaises(
            AssertionError, wu.create_workload_specific_filename, base_name,
            cmd2
        )

    def test_get_wl_label_from_filename(self) -> None:
        base_name = "base"
        label = "myLabel"
        cmd = Command(TT / "bin" / "true", label=label)
        reps = 42
        file_suffix = ".json"

        filename = wu.create_workload_specific_filename(
            base_name, cmd, reps, file_suffix
        )

        self.assertEqual("myLabel", wu.get_workload_label(filename))
