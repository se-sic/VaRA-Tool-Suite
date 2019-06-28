"""
Test case study
"""

import unittest
import yaml

import varats.paper.case_study as CS

YAML_CASE_STUDY = """!CaseStudy
_CaseStudy__project_name: gzip
_CaseStudy__stages:
- !CSStage
  _CSStage__name: stage_0
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
  _CSStage__name: null
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

    def test_stage_name(self):
        """
        Check if the name of the stage is loaded correctly.
        """
        self.assertEqual(self.case_study.stages[0].name, "stage_0")
        self.assertEqual(self.case_study.stages[1].name, None)

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


class TestSampling(unittest.TestCase):
    """
    Test basic sampling test.
    """

    @classmethod
    def setUpClass(cls):
        """
        Setup case study from yaml doc.
        """
        cls.base_list = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

    def test_sample_amount(self):
        """
        Check if sampling function produces the correct amount of sample.
        """
        self.assertEqual(
            len(
                CS.sample_n(
                    CS.SamplingMethod.uniform.gen_distribution_function(), 5,
                    self.base_list)), 5)
        self.assertEqual(
            len(
                CS.sample_n(
                    CS.SamplingMethod.uniform.gen_distribution_function(), 1,
                    self.base_list)), 1)
        self.assertEqual(
            len(
                CS.sample_n(
                    CS.SamplingMethod.uniform.gen_distribution_function(), 7,
                    self.base_list)), 7)

    def test_sample_more_than_max_amount(self):
        """
        Check if sampling function produces the correct amount of sample if we
        sample more than in the initial list.
        """
        self.assertEqual(
            len(
                CS.sample_n(
                    CS.SamplingMethod.uniform.gen_distribution_function(),
                    len(self.base_list) + 1, self.base_list)),
            len(self.base_list))

        self.assertEqual(
            len(
                CS.sample_n(
                    CS.SamplingMethod.uniform.gen_distribution_function(),
                    len(self.base_list) + 666, self.base_list)),
            len(self.base_list))

    def test_sample_nothing(self):
        """
        Check if sampling function produces the correct amount of sample if we
        want nothing.
        """
        self.assertEqual(
            len(
                CS.sample_n(
                    CS.SamplingMethod.uniform.gen_distribution_function(), 0,
                    self.base_list)), 0)
