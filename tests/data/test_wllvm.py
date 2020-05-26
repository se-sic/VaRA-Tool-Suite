"""Test wllvm module."""

import unittest
import unittest.mock as mock

from varats.experiments.wllvm import Extract, BCFileExtensions


class TestExtract(unittest.TestCase):

    def test_get_bc_file_name_correct_opt(self):
        """Test if the bc file name is correctly parsed."""

        # Arrange
        test_project_name = "testProject"
        test_binary_name = "testBinary"
        test_project_version = "testProjectVersion1"
        test_bc_file_extensions = [BCFileExtensions.DEBUG, BCFileExtensions.OPT]

        mock_bc_file_name = f"{test_project_name}-{test_binary_name}-" \
                            f"{test_project_version}-dbg_O2.bc"

        # Act
        actual = Extract.get_bc_file_name(
            test_project_name, test_binary_name, test_project_version,
            test_bc_file_extensions
        )

        # Assert
        self.assertEqual(actual, mock_bc_file_name)

    def test_get_bc_file_name_correct_NoOpt(self):
        """Test if the bc file name is correctly parsed."""

        # Arrange
        test_project_name = "testProject"
        test_binary_name = "testBinary"
        test_project_version = "testProjectVersion1"
        test_bc_file_extensions = [
            BCFileExtensions.DEBUG, BCFileExtensions.NO_OPT
        ]

        mock_bc_file_name = f"{test_project_name}-{test_binary_name}-" \
                            f"{test_project_version}-dbg_O0.bc"

        # Act
        actual = Extract.get_bc_file_name(
            test_project_name, test_binary_name, test_project_version,
            test_bc_file_extensions
        )

        # Assert
        self.assertEqual(actual, mock_bc_file_name)
