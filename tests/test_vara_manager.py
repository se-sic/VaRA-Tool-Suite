import unittest
from pathlib import Path

from varats.vara_manager import LLVMProjects, VaRAProjectsIter,\
    VaRAExtraProjectsIter


class TestLLVMProjects(unittest.TestCase):
    """
    Test VaRA Project handling.
    """

    def test_get_vara_values(self):
        vara_project = LLVMProjects.vara

        self.assertEqual(vara_project.project_name, "VaRA")
        self.assertEqual(vara_project.url, "git@github.com:se-passau/VaRA.git")
        self.assertEqual(vara_project.remote, "origin")
        self.assertEqual(vara_project.path, Path("tools/VaRA"))

    def test_vara_projects_iter(self):
        vara_projects_iter = iter(VaRAProjectsIter())
        self.assertEqual(next(vara_projects_iter), LLVMProjects.llvm)
        self.assertEqual(next(vara_projects_iter), LLVMProjects.clang)
        self.assertEqual(next(vara_projects_iter), LLVMProjects.vara)
        self.assertRaises(StopIteration, next, vara_projects_iter)

    def test_vara_extra_projects_iter(self):
        vara_extra_projects_iter = iter(VaRAExtraProjectsIter())
        self.assertEqual(
            next(vara_extra_projects_iter), LLVMProjects.clang_extra)
        self.assertEqual(
            next(vara_extra_projects_iter), LLVMProjects.compiler_rt)
        self.assertEqual(next(vara_extra_projects_iter), LLVMProjects.lld)
        self.assertEqual(next(vara_extra_projects_iter), LLVMProjects.phasar)
        self.assertRaises(StopIteration, next, vara_extra_projects_iter)
