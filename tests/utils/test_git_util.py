"""Test VaRA git utilities."""
import unittest
from pathlib import Path

from benchbuild.utils.revision_ranges import RevisionRange

from varats.project.project_util import (
    get_local_project_git,
    get_local_project_git_path,
    BinaryType,
)
from varats.projects.discover_projects import initialize_projects
from varats.utils.git_commands import checkout_branch_or_commit
from varats.utils.git_util import (
    ChurnConfig,
    CommitRepoPair,
    FullCommitHash,
    ShortCommitHash,
    is_commit_hash,
    get_commits_after_timestamp,
    get_commits_before_timestamp,
    contains_source_code,
    calc_code_churn,
    calc_commit_code_churn,
    get_all_revisions_between,
    get_current_branch,
    get_initial_commit,
    RevisionBinaryMap,
    get_submodule_head,
    get_head_commit,
    calc_code_churn_range,
)


class TestGitInteractionHelpers(unittest.TestCase):
    """Test if the different git helper classes work."""

    @classmethod
    def setUpClass(cls):
        initialize_projects()

    def test_is_commit_hash(self) -> None:
        """Check if we can correctly identify commit hashes."""
        self.assertTrue(is_commit_hash("a"))
        self.assertTrue(is_commit_hash("a94"))
        self.assertTrue(is_commit_hash("a94a8fe5cc"))
        self.assertTrue(is_commit_hash("a94a8fe5ccb19ba61c4"))
        self.assertTrue(
            is_commit_hash("a94a8fe5ccb19ba61c4c0873d391e987982fbbd3")
        )

        self.assertFalse(is_commit_hash("zzz"))
        self.assertFalse(
            is_commit_hash("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        )
        self.assertFalse(is_commit_hash("thisisnotacommithash"))

    def test_get_current_branch(self):
        """Check if we can correctly retrieve the current branch of a repo."""
        repo = get_local_project_git("brotli")

        repo.checkout(repo.lookup_branch('master'))

        self.assertEqual(get_current_branch(repo.workdir), 'master')

    def test_get_initial_commit(self) -> None:
        """Check if we can correctly retrieve the inital commit of a repo."""
        repo_path = get_local_project_git_path("FeaturePerfCSCollection")

        inital_commit = get_initial_commit(repo_path)

        self.assertEqual(
            FullCommitHash("4d84c8f80ec2db3aaa880d323f7666752c4be51d"),
            inital_commit
        )

    def test_get_initial_commit_with_specified_path(self) -> None:
        """Check if we can correctly retrieve the inital commit of a repo."""
        inital_commit = get_initial_commit(
            get_local_project_git_path("FeaturePerfCSCollection")
        )

        self.assertEqual(
            FullCommitHash("4d84c8f80ec2db3aaa880d323f7666752c4be51d"),
            inital_commit
        )

    def test_get_all_revisions_between_full(self):
        """Check if the correct all revisions are correctly found."""
        repo_path = get_local_project_git_path("brotli")
        revs = get_all_revisions_between(
            '5692e422da6af1e991f9182345d58df87866bc5e',
            '2f9277ff2f2d0b4113b1ffd9753cc0f6973d354a', FullCommitHash,
            repo_path
        )

        self.assertSetEqual(
            set(revs), {
                FullCommitHash("5692e422da6af1e991f9182345d58df87866bc5e"),
                FullCommitHash("2f9277ff2f2d0b4113b1ffd9753cc0f6973d354a"),
                FullCommitHash("63be8a99401992075c23e99f7c84de1c653e39e2"),
                FullCommitHash("2a51a85aa86abb4c294c65fab57f3d9c69f10080")
            }
        )

    def test_get_all_revisions_between_short(self):
        """Check if the correct all revisions are correctly found."""
        repo_path = get_local_project_git_path("brotli")
        revs = get_all_revisions_between(
            '5692e422da6af1e991f9182345d58df87866bc5e',
            '2f9277ff2f2d0b4113b1ffd9753cc0f6973d354a', ShortCommitHash,
            repo_path
        )

        self.assertSetEqual(
            set(revs), {
                ShortCommitHash("5692e422da"),
                ShortCommitHash("2f9277ff2f"),
                ShortCommitHash("63be8a9940"),
                ShortCommitHash("2a51a85aa8")
            }
        )

    def test_get_submodule_head(self):
        """Check if correct submodule commit is retrieved."""
        repo_path = get_local_project_git_path("grep")
        old_head = get_head_commit(repo_path)
        repo_head = FullCommitHash("cb15dfa4b2d7fba0d50e87b49f979c7f996b8ebc")
        checkout_branch_or_commit(repo_path, repo_head)

        try:
            submodule_head = get_submodule_head("grep", "gnulib", repo_head)
            self.assertEqual(
                submodule_head,
                FullCommitHash("f44eb378f7239eadac38d02463019a8a6b935525")
            )
        finally:
            checkout_branch_or_commit(repo_path, old_head)

    def test_get_submodule_head_main_repo(self):
        """Check if correct main repo commit is retrieved."""
        repo_path = get_local_project_git_path("grep")
        old_head = get_head_commit(repo_path)
        repo_head = FullCommitHash("cb15dfa4b2d7fba0d50e87b49f979c7f996b8ebc")
        checkout_branch_or_commit(repo_path, repo_head)

        try:
            submodule_head = get_submodule_head("grep", "grep", repo_head)
            self.assertEqual(submodule_head, repo_head)
        finally:
            checkout_branch_or_commit(repo_path, old_head)

    def test_get_commits_before_timestamp(self) -> None:
        """Check if we can correctly determine the commits before a specific
        timestamp."""
        project_repo = get_local_project_git_path('brotli')
        brotli_commits_after = get_commits_before_timestamp(
            '2013-10-24', project_repo
        )

        # newest found commit should be
        self.assertEqual(
            brotli_commits_after[0].hash,
            "c66e4e3e4fc3ba36ca36a43eee3b704f7b989c60"
        )
        # oldest commit should be
        self.assertEqual(
            brotli_commits_after[-1].hash,
            "8f30907d0f2ef354c2b31bdee340c2b11dda0fb0"
        )

    def test_get_commits_after_timestamp(self) -> None:
        """Check if we can correctly determine the commits after a specific
        timestamp."""
        project_repo = get_local_project_git_path('brotli')
        brotli_commits_after = get_commits_after_timestamp(
            '2021-01-01', project_repo
        )

        # oldest found commit should be
        self.assertEqual(
            brotli_commits_after[-1].hash,
            "4969984a95534a508f93b38c74d150e86ef333f4"
        )
        # second oldest commit should be
        self.assertEqual(
            brotli_commits_after[-2].hash,
            "0e8afdc968f3b7c891379e558b8dcaf42d93703b"
        )

    def test_contains_source_code_without(self) -> None:
        """Check if we can correctly identify commits with source code."""
        churn_conf = ChurnConfig.create_c_style_languages_config()
        project_git_path = get_local_project_git_path('brotli')

        self.assertFalse(
            contains_source_code(
                ShortCommitHash('f4153a09f87cbb9c826d8fc12c74642bb2d879ea'),
                project_git_path, churn_conf
            )
        )
        self.assertFalse(
            contains_source_code(
                ShortCommitHash('e83c7b8e8fb8b696a1df6866bc46cbb76d7e0348'),
                project_git_path, churn_conf
            )
        )
        self.assertFalse(
            contains_source_code(
                ShortCommitHash('698e3a7f9d3000fa44174f5be415bf713f71bd0e'),
                project_git_path, churn_conf
            )
        )

    def test_contains_source_code_with(self) -> None:
        """Check if we can correctly identify commits without source code."""
        churn_conf = ChurnConfig.create_c_style_languages_config()
        project_git_path = get_local_project_git_path('brotli')

        self.assertTrue(
            contains_source_code(
                ShortCommitHash('62662f87cdd96deda90ac817de94e3c4af75226a'),
                project_git_path, churn_conf
            )
        )
        self.assertTrue(
            contains_source_code(
                ShortCommitHash('27dd7265403d8e8fed99a854b9c3e1db7d79525f'),
                project_git_path, churn_conf
            )
        )
        # Merge commit of the previous one
        self.assertTrue(
            contains_source_code(
                ShortCommitHash('4ec67035c0d97c270c1c73038cc66fc5fcdfc120'),
                project_git_path, churn_conf
            )
        )


class TestChurnConfig(unittest.TestCase):
    """Test if ChurnConfig sets languages correctly."""

    def test_enable_language(self):
        init_config = ChurnConfig.create_default_config()
        self.assertFalse(init_config.is_enabled('c'))
        init_config.enable_language(ChurnConfig.Language.CPP)
        self.assertFalse(init_config.is_enabled('c'))
        init_config.enable_language(ChurnConfig.Language.C)
        self.assertTrue(init_config.is_enabled('c'))

    def test_initial_config(self):
        init_config = ChurnConfig.create_default_config()
        self.assertTrue(init_config.include_everything)
        self.assertListEqual(init_config.enabled_languages, [])

    def test_c_language_config(self):
        c_style_config = ChurnConfig.create_c_language_config()
        self.assertTrue(c_style_config.is_enabled('h'))
        self.assertTrue(c_style_config.is_enabled('c'))

    def test_c_style_config(self):
        c_style_config = ChurnConfig.create_c_style_languages_config()
        self.assertTrue(c_style_config.is_enabled('h'))
        self.assertTrue(c_style_config.is_enabled('c'))
        self.assertTrue(c_style_config.is_enabled('hpp'))
        self.assertTrue(c_style_config.is_enabled('cpp'))
        self.assertTrue(c_style_config.is_enabled('hxx'))
        self.assertTrue(c_style_config.is_enabled('cxx'))

    def test_enabled_language(self):
        c_config = ChurnConfig.create_c_language_config()
        self.assertTrue(c_config.is_language_enabled(ChurnConfig.Language.C))
        self.assertFalse(c_config.is_language_enabled(ChurnConfig.Language.CPP))

    def test_extensions_repr_gen(self):
        c_config = ChurnConfig.create_c_language_config()
        self.assertEqual(c_config.get_extensions_repr(), ["c", "h"])
        self.assertEqual(
            c_config.get_extensions_repr(prefix="*."), ["*.c", "*.h"]
        )
        self.assertEqual(c_config.get_extensions_repr(suffix="|"), ["c|", "h|"])

        c_style_config = ChurnConfig.create_c_style_languages_config()
        self.assertEqual(
            c_style_config.get_extensions_repr(),
            ["c", "cpp", "cxx", "h", "hpp", "hxx"]
        )
        self.assertEqual(
            c_style_config.get_extensions_repr(prefix="*."),
            ["*.c", "*.cpp", "*.cxx", "*.h", "*.hpp", "*.hxx"]
        )
        self.assertEqual(
            c_style_config.get_extensions_repr(suffix="|"),
            ["c|", "cpp|", "cxx|", "h|", "hpp|", "hxx|"]
        )


class TestCommitRepoPair(unittest.TestCase):
    """Test driver for the CommitRepoPair class."""

    @classmethod
    def setUpClass(cls):
        cls.cr_pair = CommitRepoPair(
            FullCommitHash("4200000000000000000000000000000000000000"),
            "foo_repo"
        )

    def test_commit_hash(self):
        self.assertEqual(
            self.cr_pair.commit_hash,
            FullCommitHash("4200000000000000000000000000000000000000")
        )

    def test_repo_name(self):
        self.assertEqual(self.cr_pair.repository_name, "foo_repo")

    def test_less_equal(self):
        """Tests that two equal pairs are not less."""
        cr_pair_1 = CommitRepoPair(
            FullCommitHash("4200000000000000000000000000000000000000"),
            "foo_repo"
        )
        cr_pair_2 = CommitRepoPair(
            FullCommitHash("4200000000000000000000000000000000000000"),
            "foo_repo"
        )

        self.assertFalse(cr_pair_1 < cr_pair_2)

    def test_less_commit(self):
        """Tests that a smaller commit is less."""
        cr_pair_1 = CommitRepoPair(
            FullCommitHash("4100000000000000000000000000000000000000"),
            "foo_repo"
        )
        cr_pair_2 = CommitRepoPair(
            FullCommitHash("4200000000000000000000000000000000000000"),
            "foo_repo"
        )

        self.assertTrue(cr_pair_1 < cr_pair_2)

    def test_less_repo(self):
        """Tests that a smaller repo is less, if the commits are equal."""
        cr_pair_1 = CommitRepoPair(
            FullCommitHash("4200000000000000000000000000000000000000"),
            "foo_repo"
        )
        cr_pair_2 = CommitRepoPair(
            FullCommitHash("4200000000000000000000000000000000000000"),
            "boo_repo"
        )

        self.assertFalse(cr_pair_1 < cr_pair_2)

    def tests_less_something_other(self):
        self.assertFalse(self.cr_pair < 42)

    def test_equal_equal(self):
        """Tests that two equal pairs are equal."""
        cr_pair_1 = CommitRepoPair(
            FullCommitHash("4200000000000000000000000000000000000000"),
            "foo_repo"
        )
        cr_pair_2 = CommitRepoPair(
            FullCommitHash("4200000000000000000000000000000000000000"),
            "foo_repo"
        )

        self.assertTrue(cr_pair_1 == cr_pair_2)

    def test_equal_commit(self):
        """Tests that two different commits are not equal."""
        cr_pair_1 = CommitRepoPair(
            FullCommitHash("4100000000000000000000000000000000000000"),
            "foo_repo"
        )
        cr_pair_2 = CommitRepoPair(
            FullCommitHash("4200000000000000000000000000000000000000"),
            "foo_repo"
        )

        self.assertFalse(cr_pair_1 == cr_pair_2)

    def test_equal_repo(self):
        """Tests that two different commits are not equal."""
        cr_pair_1 = CommitRepoPair(
            FullCommitHash("4200000000000000000000000000000000000000"),
            "bar_repo"
        )
        cr_pair_2 = CommitRepoPair(
            FullCommitHash("4200000000000000000000000000000000000000"),
            "foo_repo"
        )

        self.assertFalse(cr_pair_1 == cr_pair_2)

    def tests_equal_something_other(self):
        self.assertFalse(self.cr_pair == 42)

    def test_to_string(self):
        self.assertEqual(
            str(self.cr_pair),
            "foo_repo[4200000000000000000000000000000000000000]"
        )


class TestCodeChurnCalculation(unittest.TestCase):
    """Test if we correctly compute code churn."""

    @classmethod
    def setUpClass(cls):
        initialize_projects()

    def test_one_commit_diff(self):
        """Check if we get the correct code churn for a single commit."""

        repo_path = get_local_project_git_path("brotli")

        files_changed, insertions, deletions = calc_commit_code_churn(
            repo_path,
            FullCommitHash("0c5603e07bed1d5fbb45e38f9bdf0e4560fde3f0"),
            ChurnConfig.create_c_style_languages_config()
        )

        self.assertEqual(files_changed, 1)
        self.assertEqual(insertions, 2)
        self.assertEqual(deletions, 2)

    def test_one_commit_diff_2(self):
        """Check if we get the correct code churn for a single commit."""

        repo_path = get_local_project_git_path("brotli")

        files_changed, insertions, deletions = calc_commit_code_churn(
            repo_path,
            FullCommitHash("fc823290a76a260b7ba6f47ab5f52064a0ce19ff"),
            ChurnConfig.create_c_style_languages_config()
        )

        self.assertEqual(files_changed, 1)
        self.assertEqual(insertions, 5)
        self.assertEqual(deletions, 0)

    def test_one_commit_diff_3(self):
        """Check if we get the correct code churn for a single commit."""

        repo_path = get_local_project_git_path("brotli")

        files_changed, insertions, deletions = calc_commit_code_churn(
            repo_path,
            FullCommitHash("924b2b2b9dc54005edbcd85a1b872330948cdd9e"),
            ChurnConfig.create_c_style_languages_config()
        )

        self.assertEqual(files_changed, 3)
        self.assertEqual(insertions, 38)
        self.assertEqual(deletions, 7)

    def test_one_commit_diff_ignore_non_c_cpp_files(self):
        """Check if we get the correct code churn for a single commit but only
        consider code changes."""

        repo_path = get_local_project_git_path("brotli")

        files_changed, insertions, deletions = calc_commit_code_churn(
            repo_path,
            FullCommitHash("f503cb709ca181dbf5c73986ebac1b18ac5c9f63"),
            ChurnConfig.create_c_style_languages_config()
        )

        self.assertEqual(files_changed, 1)
        self.assertEqual(insertions, 11)
        self.assertEqual(deletions, 4)

    def test_start_with_initial_commit(self):
        """Check if the initial commit is handled correctly."""

        repo_path = get_local_project_git_path("brotli")

        churn = calc_code_churn_range(
            repo_path, ChurnConfig.create_c_style_languages_config(),
            FullCommitHash("8f30907d0f2ef354c2b31bdee340c2b11dda0fb0"),
            FullCommitHash("8f30907d0f2ef354c2b31bdee340c2b11dda0fb0")
        )

        files_changed, insertions, deletions = churn[
            FullCommitHash("8f30907d0f2ef354c2b31bdee340c2b11dda0fb0")]
        self.assertEqual(files_changed, 11)
        self.assertEqual(insertions, 1730)
        self.assertEqual(deletions, 0)

    def test_end_only(self):
        """Check if churn is correct if only end range is set."""

        repo_path = get_local_project_git_path("brotli")

        churn = calc_code_churn_range(
            repo_path, ChurnConfig.create_c_style_languages_config(), None,
            FullCommitHash("645552217219c2877780ba4d7030044ec62d8255")
        )

        self.assertEqual(
            churn[FullCommitHash("645552217219c2877780ba4d7030044ec62d8255")],
            (2, 173, 145)
        )
        self.assertEqual(
            churn[FullCommitHash("e0346c826249368f0f4a68a2b95f4ab5cf1e235b")],
            (3, 51, 51)
        )
        self.assertEqual(
            churn[FullCommitHash("8f30907d0f2ef354c2b31bdee340c2b11dda0fb0")],
            (11, 1730, 0)
        )

    def test_commit_range(self):
        """Check if we get the correct code churn for commit range."""

        repo_path = get_local_project_git_path("brotli")

        files_changed, insertions, deletions = calc_code_churn(
            repo_path,
            FullCommitHash("36ac0feaf9654855ee090b1f042363ecfb256f31"),
            FullCommitHash("924b2b2b9dc54005edbcd85a1b872330948cdd9e"),
            ChurnConfig.create_c_style_languages_config()
        )

        self.assertEqual(files_changed, 3)
        self.assertEqual(insertions, 49)
        self.assertEqual(deletions, 11)


class TestRevisionBinaryMap(unittest.TestCase):
    """Test if we can correctly setup and use the RevisionBinaryMap."""

    rv_map: RevisionBinaryMap

    def setUp(self) -> None:
        self.rv_map = RevisionBinaryMap(
            get_local_project_git_path("FeaturePerfCSCollection")
        )

    def test_specification_of_always_valid_binaries(self) -> None:
        """Check if we can add binaries to the map."""
        self.rv_map.specify_binary(
            "build/bin/SingleLocalSimple", BinaryType.EXECUTABLE
        )

        self.assertIn("SingleLocalSimple", self.rv_map)

    def test_specification_validity_range_binaries(self) -> None:
        """Check if we can add binaries to the map that are only valid in a
        specific range."""
        self.rv_map.specify_binary(
            "build/bin/SingleLocalMultipleRegions",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("162db88346", "master")
        )

        self.assertIn("SingleLocalMultipleRegions", self.rv_map)

    def test_specification_binaries_with_special_name(self) -> None:
        """Check if we can add binaries that have a special name."""
        self.rv_map.specify_binary(
            "build/bin/SingleLocalSimple",
            BinaryType.EXECUTABLE,
            override_binary_name="Overridden"
        )

        self.assertIn("Overridden", self.rv_map)

    def test_specification_binaries_with_special_entry_point(self) -> None:
        """Check if we can add binaries that have a special entry point."""
        self.rv_map.specify_binary(
            "build/bin/SingleLocalSimple",
            BinaryType.EXECUTABLE,
            override_entry_point="build/bin/OtherSLSEntry"
        )

        test_query = self.rv_map[ShortCommitHash("745424e3ae")]

        self.assertEqual(
            "build/bin/OtherSLSEntry", str(test_query[0].entry_point)
        )
        self.assertIsInstance(test_query[0].entry_point, Path)

    def test_wrong_contains_check(self) -> None:
        """Check if wrong values are correctly shows as not in the map."""
        self.rv_map.specify_binary(
            "build/bin/SingleLocalSimple", BinaryType.EXECUTABLE
        )

        self.assertNotIn("WrongFilename", self.rv_map)

        obj_with_wrong_type = object()
        self.assertNotIn(obj_with_wrong_type, self.rv_map)

    def test_valid_binary_lookup(self) -> None:
        """Check if we can correctly determine the list of valid binaries for a
        specified revision."""
        self.rv_map.specify_binary(
            "build/bin/SingleLocalSimple", BinaryType.EXECUTABLE
        )
        self.rv_map.specify_binary(
            "build/bin/SingleLocalMultipleRegions",
            BinaryType.EXECUTABLE,
            only_valid_in=RevisionRange("162db88346", "master")
        )

        test_query = self.rv_map[ShortCommitHash("162db88346")]
        self.assertSetEqual({x.name for x in test_query},
                            {"SingleLocalSimple", "SingleLocalMultipleRegions"})

        test_query = self.rv_map[ShortCommitHash("745424e3ae")]
        self.assertSetEqual({x.name for x in test_query}, {"SingleLocalSimple"})
