"""Test case study."""
import typing as tp
import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile

import varats.paper.case_study as CS
from varats.base.sampling_method import UniformSamplingMethod
from varats.mapping.commit_map import CommitMap

YAML_CASE_STUDY = """---
DocType: CaseStudy
Version: 1
...
---
project_name: gzip
version: 1
stages:
- name: stage_0
  revisions:
  - commit_hash: b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a
    commit_id: 41
    config_ids: [0, 1]
  - commit_hash: 7620b817357d6f14356afd004ace2da426cf8c36
    commit_id: 494
    config_ids: [2]
  - commit_hash: 622e9b1d024da1343b83fc47fb1891e1d245add3
    commit_id: 431
  - commit_hash: 8798d5c4fd520dcf91f36ebfa60bc5f3dca550d9
    commit_id: 421
  - commit_hash: 2e654f9963154e5af9d3081fc871d54d783a1270
    commit_id: 360
  - commit_hash: edfad78619d52479e02228a5789a2e98d7b0f9f6
    commit_id: 307
  - commit_hash: a3db5806d012082b9e25cc36d09f19cd736a468f
    commit_id: 279
  - commit_hash: e75f428c0ddc90a7011cfda82a7114a16c537e34
    commit_id: 190
  - commit_hash: 1e7e3769dc4efd55249c475470152acbcf804bb3
    commit_id: 144
  - commit_hash: 9872ba420c99323195e96cafe56ff247c3011ad5
    commit_id: 56
- name: null
  revisions:
  - commit_hash: 7620b817357d6f14356afd004ace2da426cf8c36
    commit_id: 494
...
---
0: '{''foo'': ''foo: True'', ''bar'': ''bar: False'', ''bazz'': ''bazz: bazz-value''}'
1: '{}'
2: '{}'
...
"""

GIT_LOG_OUT = """7620b817357d6f14356afd004ace2da426cf8c36
622e9b1d024da1343b83fc47fb1891e1d245add3
8798d5c4fd520dcf91f36ebfa60bc5f3dca550d9
2e654f9963154e5af9d3081fc871d54d783a1270
edfad78619d52479e02228a5789a2e98d7b0f9f6
a3db5806d012082b9e25cc36d09f19cd736a468f
e75f428c0ddc90a7011cfda82a7114a16c537e34
1e7e3769dc4efd55249c475470152acbcf804bb3
9872ba420c99323195e96cafe56ff247c3011ad5
b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a"""


def mocked_create_lazy_commit_map_loader(
    project_name: str,  # pylint: disable=unused-argument
    cmap_path: tp.Optional[Path] = None,  # pylint: disable=unused-argument
    end: str = "HEAD",  # pylint: disable=unused-argument
    start: tp.Optional[str] = None
):  # pylint: disable=unused-argument
    """
    Mock function to replace a lazy commit map loader callback.

    Args:
        project_name: name of the project
        cmap_path: path to commit map file
        end: commit to end loading, e.g, HEAD
        start: commit from which to start loading
    """

    def get_test_case_study_cmap() -> CommitMap:

        def format_stream():
            for number, line in enumerate(reversed(GIT_LOG_OUT.split('\n'))):
                yield "{}, {}\n".format(number, line)

        return CommitMap(format_stream())

    return get_test_case_study_cmap


class TestCaseStudy(unittest.TestCase):
    """Test basic CaseStudy functionality."""

    @classmethod
    def setUpClass(cls):
        """Setup case study from yaml doc."""

        with NamedTemporaryFile('w') as yaml_file:
            yaml_file.write(YAML_CASE_STUDY)
            yaml_file.seek(0)
            cls.case_study = CS.load_case_study_from_file(Path(yaml_file.name))

    def test_project_name(self):
        """Check if project name is loaded correctly."""
        self.assertEqual(self.case_study.project_name, "gzip")

    def test_num_revisions(self):
        """Check if all revisions were loaded correctly."""
        self.assertEqual(len(self.case_study.revisions), 10)

    def test_stage_name(self):
        """Check if the name of the stage is loaded correctly."""
        self.assertEqual(self.case_study.stages[0].name, "stage_0")
        self.assertEqual(self.case_study.stages[1].name, None)

    def test_version(self):
        """Check if all revisions were loaded correctly."""
        self.assertEqual(self.case_study.version, 1)

    def test_has_revisions(self):
        """Check if certain revisions were loaded correctly."""
        self.assertTrue(
            self.case_study.
            has_revision("b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a")
        )
        self.assertTrue(self.case_study.has_revision("b8b25e7f15"))
        self.assertTrue(self.case_study.has_revision("a3db5806d01"))
        self.assertTrue(self.case_study.has_revision("a3"))

        self.assertFalse(
            self.case_study.
            has_revision("42b25e7f1593f6dcc20660ff9fb1ed59ede15b7a")
        )
        self.assertFalse(self.case_study.has_revision("42"))

    def test_gen_filter(self):
        """Check if the project generates a revision filter."""
        revision_filter = self.case_study.get_revision_filter()
        self.assertTrue(
            revision_filter("b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a")
        )
        self.assertTrue(revision_filter("b8b25e7f15"))

        self.assertFalse(
            revision_filter("42b25e7f1593f6dcc20660ff9fb1ed59ede15b7a")
        )
        self.assertFalse(revision_filter("42"))

    def test_get_config_ids_for_rev(self):
        """Checks if the correct config IDs are fetched for the different
        revisions."""
        self.assertEqual(
            self.case_study.get_config_ids_for_revision(
                'b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a'
            ), [0, 1]
        )
        self.assertEqual(
            self.case_study.get_config_ids_for_revision(
                '8798d5c4fd520dcf91f36ebfa60bc5f3dca550d9'
            ), [-1]
        )

    def test_get_config_ids_for_multiple_revs(self):
        """Checks if the correct config IDs are fetched for the different
        revisions if a revisions is part of more than one stage."""
        self.assertEqual(
            self.case_study.get_config_ids_for_revision(
                '7620b817357d6f14356afd004ace2da426cf8c36'
            ), [2]
        )

    def test_get_config_ids_for_rev_in_stage(self):
        """Checks if the correct config IDs are fetched for the different
        revisions."""
        self.assertEqual(
            self.case_study.get_config_ids_for_revision_in_stage(
                '7620b817357d6f14356afd004ace2da426cf8c36', 0
            ), [2]
        )
        self.assertEqual(
            self.case_study.get_config_ids_for_revision_in_stage(
                '7620b817357d6f14356afd004ace2da426cf8c36', 1
            ), [-1]
        )


class TestSampling(unittest.TestCase):
    """Test basic sampling test."""

    @classmethod
    def setUpClass(cls):
        """Setup case study from yaml doc."""
        cls.base_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

    def test_sample_amount(self):
        """Check if sampling function produces the correct amount of sample."""
        self.assertEqual(
            len(UniformSamplingMethod().sample_n(self.base_list, 5)), 5
        )
        self.assertEqual(
            len(UniformSamplingMethod().sample_n(self.base_list, 1)), 1
        )
        self.assertEqual(
            len(UniformSamplingMethod().sample_n(self.base_list, 7)), 7
        )

    def test_sample_more_than_max_amount(self):
        """Check if sampling function produces the correct amount of sample if
        we sample more than in the initial list."""
        self.assertEqual(
            len(
                UniformSamplingMethod().sample_n(
                    self.base_list,
                    len(self.base_list) + 1
                )
            ), len(self.base_list)
        )

        self.assertEqual(
            len(
                UniformSamplingMethod().sample_n(
                    self.base_list,
                    len(self.base_list) + 666
                )
            ), len(self.base_list)
        )

    def test_sample_nothing(self):
        """Check if sampling function produces the correct amount of sample if
        we want nothing."""
        self.assertEqual(
            len(UniformSamplingMethod().sample_n(self.base_list, 0)), 0
        )
