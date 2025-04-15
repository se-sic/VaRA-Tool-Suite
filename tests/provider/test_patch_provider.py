import typing as tp
import unittest
from copy import deepcopy
from pathlib import Path

from benchbuild.source.base import target_prefix
from jinja2 import TemplateError

import benchbuild as bb
from tests.helper_utils import TEST_INPUTS_DIR
from varats.projects.perf_tests.feature_perf_cs_collection import (
    FeaturePerfCSCollection,
)
from varats.provider.patch.patch_provider import PatchProvider, Patch, PatchSet
from varats.utils.git_util import (
    ShortCommitHash,
    get_all_revisions_between,
    get_initial_commit,
    RepositoryHandle,
)


class TestPatchArguments(unittest.TestCase):

    def __check_render(
        self, rendered_patch: Path, expected_content: tp.List[str]
    ):
        with open(rendered_patch, "r", encoding="utf-8") as patch_file:
            rendered_content = patch_file.read().splitlines()
            self.assertEqual(rendered_content, expected_content)

    def test_parse_arguments(self):
        """Test if the arguments are correctly parsed from the patch file."""

        BASE_PATH = Path(TEST_INPUTS_DIR / 'patch_configs')
        argument_patch_nodefault = Patch.from_yaml(
            BASE_PATH / 'patch-with-args-nodefault.info'
        )

        argument_patch_default = Patch.from_yaml(
            BASE_PATH / 'patch-with-default-args.info'
        )

        argument_patch_mixed = Patch.from_yaml(
            BASE_PATH / 'patch-with-mixed-args.info'
        )

        self.assertEqual(
            argument_patch_nodefault.arguments, {
                'arg1': None,
                'arg2': None
            }
        )
        self.assertEqual(
            argument_patch_default.arguments, {
                'arg1': 100,
                'arg2': 200
            }
        )
        self.assertEqual(
            argument_patch_mixed.arguments, {
                'arg1': None,
                'arg2': 100
            }
        )

    def test_render_noargs(self):
        """Test if the render function works correctly for patches without
        arguments."""
        argument_patch = Patch.from_yaml(
            Path(
                TEST_INPUTS_DIR /
                'patch_configs/FeaturePerfCSCollection/regression-severity.info'
            )
        )

        # As this patch has no arguments, the render function should return the
        # path to the original patch file.
        self.assertEqual(argument_patch.render(), argument_patch.path)

    def test_render_missing_args(self):
        """Test if the render function raises an error if required arguments are
        missing."""
        argument_patch = Patch.from_yaml(
            Path(
                TEST_INPUTS_DIR / 'patch_configs/patch-with-args-nodefault.info'
            )
        )

        with self.assertRaises(TemplateError) as context:
            argument_patch.render()

        self.assertEqual(
            str(context.exception),
            "Missing arguments for patch rendering: arg1, arg2"
        )

        with self.assertRaises(TemplateError) as context:
            argument_patch.render(arg1=100)

        self.assertEqual(
            str(context.exception),
            "Missing arguments for patch rendering: arg2"
        )

        with self.assertRaises(TemplateError) as context:
            argument_patch.render(arg2=200)

        self.assertEqual(
            str(context.exception),
            "Missing arguments for patch rendering: arg1"
        )

    def test_render_with_default_args(self):
        """Test if the render function works correctly for patches with default
        arguments."""
        argument_patch = Patch.from_yaml(
            Path(
                TEST_INPUTS_DIR / 'patch_configs/patch-with-default-args.info'
            )
        )

        rendered_patch = argument_patch.render()

        expected_rendered = ["100", "200"]

        self.__check_render(rendered_patch, expected_rendered)

    def test_render_with_args(self):
        """Test if the render function works correctly when providing
        arguments."""
        argument_patch = Patch.from_yaml(
            Path(
                TEST_INPUTS_DIR / 'patch_configs/patch-with-args-nodefault.info'
            )
        )

        rendered_patch = argument_patch.render(arg1=345, arg2=678)

        expected_rendered = ["345", "678"]

        self.__check_render(rendered_patch, expected_rendered)

    def test_render_with_mixed_args(self):
        """Test if the render function works correctly when providing some
        arguments."""
        argument_patch = Patch.from_yaml(
            Path(TEST_INPUTS_DIR / 'patch_configs/patch-with-mixed-args.info')
        )

        rendered_patch = argument_patch.render(arg1=678)

        expected_rendered = ["678", "100"]

        self.__check_render(rendered_patch, expected_rendered)
        pass

    def test_render_with_override_default(self):
        """Test if the render function works correctly when overriding default
        arguments."""
        argument_patch = Patch.from_yaml(
            Path(
                TEST_INPUTS_DIR / 'patch_configs/patch-with-default-args.info'
            )
        )

        rendered_patch = argument_patch.render(arg1=1337, arg2=42)

        expected_rendered = ["1337", "42"]

        self.__check_render(rendered_patch, expected_rendered)


class TestPatchProvider(unittest.TestCase):

    def test_correct_patch_config_access(self):
        """Checks if we get a correct path for accessing the PatchConfig."""
        provider = PatchProvider.create_provider_for_project(
            FeaturePerfCSCollection
        )
        self.assertIsNotNone(provider)

    def test_get_patch_by_shortname(self):
        provider = PatchProvider.create_provider_for_project(
            FeaturePerfCSCollection
        )
        self.assertIsNotNone(provider)

        patch = provider.get_by_shortname("compile-error")
        self.assertIsNotNone(patch)

        patch = provider.get_by_shortname("dummy-patch")
        self.assertIsNone(patch)

    def test_parse_regression_severity(self):
        regression_patch = Patch.from_yaml(
            Path(
                TEST_INPUTS_DIR /
                'patch_configs/FeaturePerfCSCollection/regression-severity.info'
            )
        )

        other_patch = Patch.from_yaml(
            Path(
                TEST_INPUTS_DIR /
                'patch_configs/FeaturePerfCSCollection/unrestricted-range.info'
            )
        )

        self.assertIsNotNone(regression_patch.regression_severity)
        self.assertEqual(1000, regression_patch.regression_severity)
        self.assertIsNone(other_patch.regression_severity)


class TestPatchRevisionRanges(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.patch_base_path = Path(
            TEST_INPUTS_DIR / 'patch_configs/FeaturePerfCSCollection/'
        )

        project_git_source = bb.source.Git(
            remote="https://github.com/se-sic/FeaturePerfCSCollection.git",
            local="FeaturePerfCSCollection",
            refspec="origin/HEAD",
            shallow=False,
        )

        project_git_source.fetch()

        repo = RepositoryHandle(
            Path(target_prefix() + "/FeaturePerfCSCollection")
        )

        cls.all_revisions = set(
            get_all_revisions_between(
                repo,
                get_initial_commit(repo).hash, "", ShortCommitHash
            )
        )

    def __test_patch_revisions(
        self, shortname: str, expected_revisions: set[ShortCommitHash]
    ):
        patch = Patch.from_yaml(self.patch_base_path / f"{shortname}.info")

        self.assertSetEqual(expected_revisions, patch.valid_revisions)

    def test_unrestricted_range(self):
        self.__test_patch_revisions("unrestricted-range", self.all_revisions)

    def test_include_single_revision(self):
        expected_revisions = {
            ShortCommitHash("8ca5cc28e6746eef7340064b5d843631841bf31e")
        }

        self.__test_patch_revisions(
            "include-single-revision", expected_revisions
        )

    def test_include_revision_range(self):
        expected_revisions = {
            ShortCommitHash("01f9f1f07bef22d4248e8349aba4f0c1f204607e"),
            ShortCommitHash("8ca5cc28e6746eef7340064b5d843631841bf31e"),
            ShortCommitHash("c051e44a973ee31b3baa571407694467a513ba68"),
            ShortCommitHash("162db88346b06be20faac6976f1ff9bad986accf"),
            ShortCommitHash("745424e3ae1d521ae42e7486df126075d9c37be9")
        }

        self.__test_patch_revisions(
            "include-revision-range", expected_revisions
        )

    def test_included_single_and_revision_range(self):
        expected_revisions = {
            ShortCommitHash("01f9f1f07bef22d4248e8349aba4f0c1f204607e"),
            ShortCommitHash("8ca5cc28e6746eef7340064b5d843631841bf31e"),
            ShortCommitHash("c051e44a973ee31b3baa571407694467a513ba68"),
            ShortCommitHash("162db88346b06be20faac6976f1ff9bad986accf"),
            ShortCommitHash("745424e3ae1d521ae42e7486df126075d9c37be9"),
            ShortCommitHash("27f17080376e409860405c40744887d81d6b3f34")
        }

        self.__test_patch_revisions(
            "include-single-and-revision-range", expected_revisions
        )

    def test_exclude_single_revision(self):
        expected_revisions = deepcopy(self.all_revisions)
        expected_revisions.remove(
            ShortCommitHash("8ca5cc28e6746eef7340064b5d843631841bf31e")
        )

        self.__test_patch_revisions(
            "exclude-single-revision", expected_revisions
        )

    def test_exclude_revision_range(self):
        expected_revisions = deepcopy(self.all_revisions)
        expected_revisions.difference_update({
            ShortCommitHash("01f9f1f07bef22d4248e8349aba4f0c1f204607e"),
            ShortCommitHash("8ca5cc28e6746eef7340064b5d843631841bf31e"),
            ShortCommitHash("c051e44a973ee31b3baa571407694467a513ba68"),
            ShortCommitHash("162db88346b06be20faac6976f1ff9bad986accf"),
            ShortCommitHash("745424e3ae1d521ae42e7486df126075d9c37be9")
        })

        self.__test_patch_revisions(
            "exclude-revision-range", expected_revisions
        )

    def test_exclude_single_and_revision_range(self):
        expected_revisions = deepcopy(self.all_revisions)
        expected_revisions.difference_update({
            ShortCommitHash("01f9f1f07bef22d4248e8349aba4f0c1f204607e"),
            ShortCommitHash("8ca5cc28e6746eef7340064b5d843631841bf31e"),
            ShortCommitHash("c051e44a973ee31b3baa571407694467a513ba68"),
            ShortCommitHash("162db88346b06be20faac6976f1ff9bad986accf"),
            ShortCommitHash("745424e3ae1d521ae42e7486df126075d9c37be9"),
            ShortCommitHash("27f17080376e409860405c40744887d81d6b3f34")
        })

        self.__test_patch_revisions(
            "exclude-single-and-revision-range", expected_revisions
        )

    def test_include_range_exclude_single(self):
        expected_revisions = {
            ShortCommitHash("01f9f1f07bef22d4248e8349aba4f0c1f204607e"),
            ShortCommitHash("8ca5cc28e6746eef7340064b5d843631841bf31e"),
            ShortCommitHash("c051e44a973ee31b3baa571407694467a513ba68"),
            ShortCommitHash("745424e3ae1d521ae42e7486df126075d9c37be9")
        }

        self.__test_patch_revisions(
            "include-range-exclude-single", expected_revisions
        )

    def test_include_range_exclude_range(self):
        expected_revisions = {
            ShortCommitHash("01f9f1f07bef22d4248e8349aba4f0c1f204607e"),
            ShortCommitHash("4300ea495e7f013f68e785fdde5c4ead81297999"),
            ShortCommitHash("27f17080376e409860405c40744887d81d6b3f34"),
            ShortCommitHash("32b28ee90e2475cf44d7a616101bcaba2396168d"),
            ShortCommitHash("162db88346b06be20faac6976f1ff9bad986accf"),
            ShortCommitHash("745424e3ae1d521ae42e7486df126075d9c37be9")
        }

        self.__test_patch_revisions(
            "include-range-exclude-range", expected_revisions
        )


class TestPatchSet(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        patches = {
            Patch(
                "TEST",
                "Test-ABCD",
                "",
                path=Path("test.patch"),
                tags={"A", "B", "C", "D"},
                feature_tags={"F_A", "F_B", "F_C", "F_D"}
            ),
            Patch(
                "TEST",
                "Test-A",
                "",
                path=Path("test.patch"),
                tags={"A"},
                feature_tags={"F_A"}
            ),
            Patch(
                "TEST",
                "Test-B",
                "",
                path=Path("test.patch"),
                tags={"B"},
                feature_tags={"F_B"}
            ),
            Patch(
                "TEST",
                "Test-C",
                "",
                path=Path("test.patch"),
                tags={"C"},
                feature_tags={"F_C"}
            ),
            Patch(
                "TEST",
                "Test-D",
                "",
                path=Path("test.patch"),
                tags={"D"},
                feature_tags={"F_D"}
            ),
            Patch(
                "TEST",
                "Test-AB",
                "",
                path=Path("test.patch"),
                tags={"A", "B"},
                feature_tags={"F_A", "F_B"}
            ),
            Patch(
                "TEST",
                "Test-AC",
                "",
                path=Path("test.patch"),
                tags={"A", "C"},
                feature_tags={"F_A", "F_C"}
            ),
            Patch(
                "TEST",
                "Test-AD",
                "",
                path=Path("test.patch"),
                tags={"A", "D"},
                feature_tags={"F_A", "F_D"}
            ),
            Patch(
                "TEST",
                "Test-BC",
                "",
                path=Path("test.patch"),
                tags={"B", "C"},
                feature_tags={"F_B", "F_C"}
            ),
            Patch(
                "TEST",
                "Test-BD",
                "",
                path=Path("test.patch"),
                tags={"B", "D"},
                feature_tags={"F_B", "F_D"}
            ),
            Patch(
                "TEST",
                "Test-CD",
                "",
                path=Path("test.patch"),
                tags={"C", "D"},
                feature_tags={"F_C", "F_D"}
            ),
            Patch(
                "TEST",
                "Test-ABC",
                "",
                path=Path("test.patch"),
                tags={"A", "B", "C"},
                feature_tags={"F_A", "F_B", "F_C"}
            ),
            Patch(
                "TEST",
                "Test-ABD",
                "",
                path=Path("test.patch"),
                tags={"A", "B", "D"},
                feature_tags={"F_A", "F_B", "F_D"}
            ),
            Patch(
                "TEST",
                "Test-ACD",
                "",
                path=Path("test.patch"),
                tags={"A", "C", "D"},
                feature_tags={"F_A", "F_C", "F_D"}
            ),
            Patch(
                "TEST",
                "Test-BCD",
                "",
                path=Path("test.patch"),
                tags={"B", "C", "D"},
                feature_tags={"F_B", "F_C", "F_D"}
            ),
        }

        cls.patchSet = PatchSet(patches)

    def test_bracket_single_tag(self):
        for tag in {"A", "B", "C", "D"}:
            patches = self.patchSet[tag]
            self.assertEqual(8, len(patches))

            for patch in patches:
                self.assertIn(tag, patch.shortname)

    def test_bracket_multiple_tags(self):
        tags_count = {("A", "B"): 4,
                      ("C", "B"): 4,
                      ("D", "B"): 4,
                      ("A", "B", "C"): 2,
                      ("A", "B", "C", "D"): 1}

        for tags in tags_count:
            patches = self.patchSet[tags]

            self.assertEqual(tags_count[tags], len(patches))

            for patch in patches:
                for tag in tags:
                    self.assertIn(tag, patch.tags)

    def test_all_of_single_tag(self):
        for tag in {"A", "B", "C", "D"}:
            patches = self.patchSet.all_of(tag)
            self.assertEqual(8, len(patches))

            for patch in patches:
                self.assertIn(tag, patch.shortname)

    def test_all_of_multiple_tags(self):
        tags_count = {("A", "B"): 4,
                      ("C", "B"): 4,
                      ("D", "B"): 4,
                      ("A", "B", "C"): 2,
                      ("A", "B", "C", "D"): 1}

        for tags in tags_count:
            patches = self.patchSet.all_of(tags)

            self.assertEqual(tags_count[tags], len(patches))

            for patch in patches:
                for tag in tags:
                    self.assertIn(tag, patch.tags)

    def test_any_of_single_tag(self):
        for tag in {"A", "B", "C", "D"}:
            patches = self.patchSet.any_of(tag)
            self.assertEqual(8, len(patches))

            for patch in patches:
                self.assertIn(tag, patch.shortname)

    def test_any_of_multiple_tags(self):
        tags_count = {("A", "B"): 12,
                      ("C", "B"): 12,
                      ("D", "B"): 12,
                      ("A", "B", "C"): 14,
                      ("A", "B", "C", "D"): 15}

        for tags in tags_count:
            patches = self.patchSet.any_of(tags)

            self.assertEqual(tags_count[tags], len(patches))

            for patch in patches:
                any([tag in patch.tags for tag in tags])

    def test_all_of_single_feature_tag(self):
        for tag in {"F_A", "F_B", "F_C", "F_D"}:
            patches = self.patchSet.all_of_features([tag])
            self.assertEqual(8, len(patches))

    def test_all_of_multiple_feature_tags(self):
        tags_count = {("F_A", "F_B"): 4,
                      ("F_C", "F_B"): 4,
                      ("F_D", "F_B"): 4,
                      ("F_A", "F_B", "F_C"): 2,
                      ("F_A", "F_B", "F_C", "F_D"): 1}

        for tags in tags_count:
            patches = self.patchSet.all_of_features(tags)
            self.assertEqual(tags_count[tags], len(patches))

    def test_any_of_single_feature_tag(self):
        for tag in {"F_A", "F_B", "F_C", "F_D"}:
            patches = self.patchSet.any_of_features([tag])
            self.assertEqual(8, len(patches))

    def test_any_of_multiple_feature_tags(self):
        tags_count = {("F_A", "F_B"): 12,
                      ("F_C", "F_B"): 12,
                      ("F_D", "F_B"): 12,
                      ("F_A", "F_B", "F_C"): 14,
                      ("F_A", "F_B", "F_C", "F_D"): 15}

        for tags in tags_count:
            patches = self.patchSet.any_of_features(tags)
            self.assertEqual(tags_count[tags], len(patches))

    def test_patchset_intersection(self):
        patches = self.patchSet["A"] & self.patchSet["B"]

        self.assertEqual(4, len(patches))

        patches = patches & self.patchSet["C"]
        self.assertEqual(2, len(patches))

        patches = patches & self.patchSet["D"]
        self.assertEqual(1, len(patches))

    def test_patchset_union(self):
        patches = self.patchSet["A"] | self.patchSet["B"]

        self.assertEqual(12, len(patches))

        patches = patches | self.patchSet["C"]
        self.assertEqual(14, len(patches))

        patches = patches | self.patchSet["D"]
        self.assertEqual(15, len(patches))
