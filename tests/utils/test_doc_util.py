"""Test VaRA documentation utils."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import varats.ts_utils.doc_util as du
from tests.test_utils import run_in_test_environment


class TestProjectOverviewGeneration(unittest.TestCase):
    """Tests if we can automatically generate an overview table for all projects
    sphinx documentation."""

    def test_generate_projects_overview_table(self) -> None:
        """Checks if we can correctly generate the project overview table."""
        generated_overview = du.generate_project_overview_table()

        table_lines = generated_overview.splitlines()

        cleaned_headerline = list(
            map(lambda x: x.strip(), table_lines[1].split("|")[1:-1])
        )

        cleaned_first_row = list(
            map(lambda x: x.strip(), table_lines[3].split("|")[1:-1])
        )

        self.assertEqual(cleaned_headerline[0], "Project")
        self.assertEqual(cleaned_headerline[1], "Group")
        self.assertEqual(cleaned_headerline[2], "Domain")
        self.assertEqual(cleaned_headerline[3], "Main Source")

        self.assertEqual(
            cleaned_first_row[0],
            ":class:`~varats.projects.c_projects.glibc.Glibc`"
        )
        self.assertEqual(cleaned_first_row[1], "c_projects")
        self.assertEqual(cleaned_first_row[2], "C Library")
        self.assertEqual(
            cleaned_first_row[3], "git://sourceware.org/git/glibc.git"
        )


class TestAutoclassGenerationForProjects(unittest.TestCase):
    """Tests if we can automatically generate sphinx documentation for
    projects."""

    @run_in_test_environment()
    def test_generate_projects_autoclass_files(self) -> None:
        """Checks if all the required files are generated."""
        with TemporaryDirectory() as tmpdir:
            du.generate_projects_autoclass_files(Path(tmpdir))

            generated_inc_files = sorted([
                inc_file.name for inc_file in Path(tmpdir).iterdir()
            ])

            self.assertTrue(
                all(x.startswith("Autoclass_") for x in generated_inc_files)
            )

            self.assertTrue(generated_inc_files[0].endswith("c_projects.inc"))
            self.assertTrue(generated_inc_files[1].endswith("cpp_projects.inc"))
            self.assertTrue(
                generated_inc_files[2].endswith("test_projects.inc")
            )

    def test_generate_projects_autoclass_directives(self) -> None:
        """Checks if we correctly generate the autoclass directives for
        projects."""
        generated_doc_string = du.generate_project_groups_autoclass_directives(
            'test_projects'
        )

        generated_doc_string = generated_doc_string.rstrip()

        for line in generated_doc_string.split('\n'):
            self.assertTrue(line.startswith(".. autoclass::"))

        self.assertEqual(
            generated_doc_string.split('\n')[0][15:],
            "varats.projects.test_projects.basic_tests.BasicTests"
        )
