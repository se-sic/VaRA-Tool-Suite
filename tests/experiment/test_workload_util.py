"""Test VaRA workload utilities."""
import unittest
from pathlib import Path
from unittest.mock import patch

from benchbuild.command import Command, PathToken, RootRenderer
from benchbuild.source.base import Revision, Variant

import varats.experiment.workload_util as wu
from varats.projects.c_projects.xz import Xz
from varats.utils.git_util import ShortCommitHash

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

        commands = next(
            wu.filter_workload_index(
                wu.WorkloadSet(wu.WorkloadCategory.EXAMPLE), project.workloads
            )
        )
        commands[0]._requires = {"--compress"}
        commands = wu.workload_commands(
            project, binary, [wu.WorkloadCategory.EXAMPLE]
        )
        self.assertEqual(len(commands), 0)
        with patch(
            "varats.experiment.workload_util.get_extra_config_options",
            return_value=["--compress"]
        ):
            commands = wu.workload_commands(
                project, binary, [wu.WorkloadCategory.EXAMPLE]
            )
            self.assertEqual(len(commands), 1)


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
