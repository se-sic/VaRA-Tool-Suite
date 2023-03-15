"""Test VaRA workload utilities."""
import typing as tp
import unittest
from pathlib import Path

from benchbuild.command import Command, PathToken, RootRenderer

import varats.experiment.workload_util as wu

TT = PathToken.make_token(RootRenderer())


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
