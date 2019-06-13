"""
Test case study
"""

import unittest
import yaml

YAML_CASE_STUDY = """!CaseStudy
_CaseStudy__project_name: gzip
_CaseStudy__stages:
- !CSStage
  _CSStage__revisions:
  - !HashIDTuple
    _HashIDTuple__commit_hash: 7620b817357d6f14356afd004ace2da426cf8c36
    _HashIDTuple__commit_id: 494
  - !HashIDTuple
    _HashIDTuple__commit_hash: 622e9b1d024da1343b83fc47fb1891e1d245add3
    _HashIDTuple__commit_id: 431
  - !HashIDTuple
    _HashIDTuple__commit_hash: 8798d5c4fd520dcf91f36ebfa60bc5f3dca550d9
    _HashIDTuple__commit_id: 421
  - !HashIDTuple
    _HashIDTuple__commit_hash: 2e654f9963154e5af9d3081fc871d54d783a1270
    _HashIDTuple__commit_id: 360
  - !HashIDTuple
    _HashIDTuple__commit_hash: edfad78619d52479e02228a5789a2e98d7b0f9f6
    _HashIDTuple__commit_id: 307
  - !HashIDTuple
    _HashIDTuple__commit_hash: a3db5806d012082b9e25cc36d09f19cd736a468f
    _HashIDTuple__commit_id: 279
  - !HashIDTuple
    _HashIDTuple__commit_hash: e75f428c0ddc90a7011cfda82a7114a16c537e34
    _HashIDTuple__commit_id: 190
  - !HashIDTuple
    _HashIDTuple__commit_hash: 1e7e3769dc4efd55249c475470152acbcf804bb3
    _HashIDTuple__commit_id: 144
  - !HashIDTuple
    _HashIDTuple__commit_hash: 9872ba420c99323195e96cafe56ff247c3011ad5
    _HashIDTuple__commit_id: 56
  - !HashIDTuple
    _HashIDTuple__commit_hash: b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a
    _HashIDTuple__commit_id: 41
- !CSStage
  _CSStage__revisions:
  - !HashIDTuple
    _HashIDTuple__commit_hash: 7620b817357d6f14356afd004ace2da426cf8c36
    _HashIDTuple__commit_id: 494
_CaseStudy__version: 1
"""


class TestCaseStudy(unittest.TestCase):
    """
    Test basic CaseStudy functionality.
    """

    @classmethod
    def setUpClass(cls):
        """
        Setup case study from yaml doc.
        """
        cls.case_study = yaml.safe_load(YAML_CASE_STUDY)

    def test_project_name(self):
        """
        Check if project name is loaded correctly.
        """
        self.assertEqual(self.case_study.project_name, "gzip")

    def test_num_revisions(self):
        """
        Check if all revisions were loaded correctly.
        """
        self.assertEqual(len(self.case_study.revisions), 10)

    def test_version(self):
        """
        Check if all revisions were loaded correctly.
        """
        self.assertEqual(self.case_study.version, 1)

    def test_has_revisions(self):
        """
        Check if certain revisions were loaded correctly.
        """
        self.assertTrue(
            self.case_study.has_revision(
                "b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a"))
        self.assertTrue(self.case_study.has_revision("b8b25e7f15"))
        self.assertTrue(self.case_study.has_revision("a3db5806d01"))
        self.assertTrue(self.case_study.has_revision("a3"))

        self.assertFalse(
            self.case_study.has_revision(
                "42b25e7f1593f6dcc20660ff9fb1ed59ede15b7a"))
        self.assertFalse(self.case_study.has_revision("42"))

    def test_gen_filter(self):
        """
        Check if the project generates a revision filter.
        """
        revision_filter = self.case_study.get_revision_filter()
        self.assertTrue(
            revision_filter("b8b25e7f1593f6dcc20660ff9fb1ed59ede15b7a"))
        self.assertTrue(revision_filter("b8b25e7f15"))

        self.assertFalse(
            revision_filter("42b25e7f1593f6dcc20660ff9fb1ed59ede15b7a"))
        self.assertFalse(revision_filter("42"))
