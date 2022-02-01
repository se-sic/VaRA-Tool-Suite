"""Test VaRA project domain classes."""

import unittest

import varats.project.project_domain as pd


class TestProjectDomain(unittest.TestCase):
    """Tests basic functionallity for project domains."""

    def test_to_str(self) -> None:
        """Checks if we can correctly convert domain enums into strings."""
        self.assertEqual(str(pd.ProjectDomains.CODEC), "Codec")
        self.assertEqual(str(pd.ProjectDomains.DATABASE), "Database")

    def test_lesser_ordering(self) -> None:
        """Checks if project domains get correctly ordered."""
        unsorted_project_domains = [
            pd.ProjectDomains.HW_EMULATOR,
            pd.ProjectDomains.DATABASE,
            pd.ProjectDomains.PARSER,
            pd.ProjectDomains.C_LIBRARY,
        ]

        sorted_project_domains = sorted(unsorted_project_domains)

        self.assertEqual(sorted_project_domains[0], pd.ProjectDomains.C_LIBRARY)
        self.assertEqual(sorted_project_domains[-1], pd.ProjectDomains.PARSER)


class TestProjectGroup(unittest.TestCase):
    """Tests basic functionallity for project groups."""

    def test_to_str(self) -> None:
        """Checks if we can correctly convert domain enums into strings."""
        self.assertEqual(str(pd.ProjectGroups.C_PROJECTS), "c_projects")
        self.assertEqual(str(pd.ProjectGroups.CPP_PROJECTS), "cpp_projects")

    def test_lesser_ordering(self) -> None:
        """Checks if project domains get correctly ordered."""
        unsorted_project_groups = [
            pd.ProjectGroups.CPP_PROJECTS, pd.ProjectGroups.C_PROJECTS
        ]

        sorted_project_groups = sorted(unsorted_project_groups)

        self.assertEqual(sorted_project_groups[0], pd.ProjectGroups.C_PROJECTS)
        self.assertEqual(
            sorted_project_groups[-1], pd.ProjectGroups.CPP_PROJECTS
        )
