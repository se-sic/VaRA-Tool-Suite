"""Test wllvm module."""

import unittest

from varats.experiment.wllvm import Extract, BCFileExtensions


class TestExtract(unittest.TestCase):
    """Test if the extraction of a llvm bitcode file from the project is
    correct."""

    @classmethod
    def setUpClass(cls):
        """Setup example bc file name."""
        cls.test_project_name = "testProject"
        cls.test_binary_name = "testBinary"
        cls.test_project_version = "testProjectVersion1"
        cls.test_bc_file_extensions = []

        cls.mock_bc_file_name = f"{cls.test_project_name}" \
                                f"-{cls.test_binary_name}-" \
                                f"{cls.test_project_version}-"

    def test_get_bc_file_name_opt(self):
        """Test if the bc file name is correctly parsed."""

        # Given
        self.test_bc_file_extensions = [
            BCFileExtensions.DEBUG, BCFileExtensions.OPT
        ]
        self.mock_bc_file_name = f"{self.mock_bc_file_name}dbg_O2.bc"

        # When
        actual = Extract.get_bc_file_name(
            self.test_project_name, self.test_binary_name,
            self.test_project_version, self.test_bc_file_extensions
        )

        # Then
        self.assertEqual(self.mock_bc_file_name, actual)

    def test_get_bc_file_name_no_opt(self):
        """Test if the bc file name is correctly parsed."""

        # Given
        self.test_bc_file_extensions = [
            BCFileExtensions.DEBUG, BCFileExtensions.NO_OPT
        ]
        self.mock_bc_file_name = f"{self.mock_bc_file_name}dbg_O0.bc"

        # When
        actual = Extract.get_bc_file_name(
            self.test_project_name, self.test_binary_name,
            self.test_project_version, self.test_bc_file_extensions
        )

        # Then
        self.assertEqual(actual, self.mock_bc_file_name)
