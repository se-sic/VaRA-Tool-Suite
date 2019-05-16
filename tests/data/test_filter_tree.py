"""
Test VaRA filter tree.
"""

import unittest
import unittest.mock as mock

import yaml
from PyQt5.QtCore import QDateTime, Qt

from varats.data.filtertree_data import (
    AndOperator, OrOperator, NotOperator, SourceOperator, TargetOperator,
    InteractionFilter, AuthorFilter, CommitterFilter,
    AuthorDateMinFilter, AuthorDateMaxFilter, CommitDateMinFilter, CommitDateMaxFilter,
    AuthorDateDeltaMinFilter, AuthorDateDeltaMaxFilter,
    CommitDateDeltaMinFilter, CommitDateDeltaMaxFilter
)

YAML_DOC_1 = """&id009 !AndOperator
_children:
- &id002 !OrOperator
  _children:
  - &id001 !SourceOperator
    _child: !CommitterFilter
      _comment: ''
      _committer_email: doe@example.com
      _committer_name: Jane Doe
      _parent: *id001
    _comment: ''
    _parent: *id002
  - &id004 !SourceOperator
    _child: &id003 !NotOperator
      _child: !AuthorFilter
        _author_email: doe@example.com
        _author_name: Jane Doe
        _comment: ''
        _parent: *id003
      _comment: ''
      _parent: *id004
    _comment: ''
    _parent: *id002
  - &id005 !TargetOperator
    _child: !AuthorDateMinFilter
      _author_date_min: '2000-01-01T00:00:00Z'
      _comment: ''
      _parent: *id005
    _comment: ''
    _parent: *id002
  - &id006 !TargetOperator
    _child: !AuthorDateMaxFilter
      _author_date_max: '2001-01-01T00:00:00Z'
      _comment: ''
      _parent: *id006
    _comment: ''
    _parent: *id002
  - &id007 !TargetOperator
    _child: !CommitDateMinFilter
      _comment: ''
      _commit_date_min: '2002-01-01T00:00:00Z'
      _parent: *id007
    _comment: ''
    _parent: *id002
  - &id008 !TargetOperator
    _child: !CommitDateMaxFilter
      _comment: ''
      _commit_date_max: '2003-01-01T00:00:00Z'
      _parent: *id008
    _comment: ''
    _parent: *id002
  - !AuthorDateDeltaMinFilter
    _author_date_delta_min: P1DT1H
    _comment: ''
    _parent: *id002
  - !AuthorDateDeltaMaxFilter
    _author_date_delta_max: P1DT2H
    _comment: ''
    _parent: *id002
  - !CommitDateDeltaMinFilter
    _comment: ''
    _commit_date_delta_min: P1DT3H
    _parent: *id002
  - !CommitDateDeltaMaxFilter
    _comment: ''
    _commit_date_delta_max: P1DT4H
    _parent: *id002
  _comment: comment
  _parent: *id009
_comment: ''
_parent: null
"""


class TestFilterTreeElements(unittest.TestCase):
    """
    Test filter tree node types
    """

    @classmethod
    def setUpClass(cls):
        """
        Setup file and CommitReport
        """
        cls.parent_dummy = AndOperator()

        cls.author_filter = AuthorFilter(cls.parent_dummy, "comment",
                                         "Jane Doe", "doe@example.com")
        cls.committer_filter = CommitterFilter(cls.parent_dummy, "comment",
                                               "Jane Doe", "doe@example.com")
        cls.author_date_min_filter = AuthorDateMinFilter(cls.parent_dummy, "comment",
                                                         "2000-01-01T00:00:00Z")
        cls.author_date_max_filter = AuthorDateMaxFilter(cls.parent_dummy, "comment",
                                                         "2000-01-01T00:00:00Z")
        cls.commit_date_min_filter = CommitDateMinFilter(cls.parent_dummy, "comment",
                                                         "2000-01-01T00:00:00Z")
        cls.commit_date_max_filter = CommitDateMaxFilter(cls.parent_dummy, "comment",
                                                         "2000-01-01T00:00:00Z")
        cls.author_date_delta_min_filter = AuthorDateDeltaMinFilter(cls.parent_dummy, "comment",
                                                                    "P3DT12H30M")
        cls.author_date_delta_max_filter = AuthorDateDeltaMaxFilter(cls.parent_dummy, "comment",
                                                                    "P3DT12H30M")
        cls.commit_date_delta_min_filter = CommitDateDeltaMinFilter(cls.parent_dummy, "comment",
                                                                    "P3DT12H30M")
        cls.commit_date_delta_max_filter = CommitDateDeltaMaxFilter(cls.parent_dummy, "comment",
                                                                    "P3DT12H30M")

        cls.and_operator = AndOperator(cls.parent_dummy, "comment")
        cls.or_operator = OrOperator(cls.parent_dummy, "comment")
        cls.not_operator = NotOperator(cls.parent_dummy, "comment")
        cls.source_operator = SourceOperator(cls.parent_dummy, "comment")
        cls.target_operator = TargetOperator(cls.parent_dummy, "comment")

    def test_author_filter(self):
        filter_node = self.author_filter

        self.assertEqual(filter_node.name(), "AuthorFilter")
        self.assertEqual(filter_node.data(0), "AuthorFilter")

        filter_node.setData(0, "name_2")
        self.assertEqual(filter_node.name(), "AuthorFilter",
                         "Name should be read-only!")
        self.assertEqual(filter_node.data(0), "AuthorFilter",
                         "Name should be read-only!")

        self.assertEqual(filter_node.comment(), "comment")
        self.assertEqual(filter_node.data(1), "comment")

        filter_node.setComment("comment_2")
        self.assertEqual(filter_node.comment(), "comment_2")
        self.assertEqual(filter_node.data(1), "comment_2")

        filter_node.setData(1, "comment_3")
        self.assertEqual(filter_node.comment(), "comment_3")
        self.assertEqual(filter_node.data(1), "comment_3")

        self.assertIs(filter_node.parent(), self.parent_dummy)

        new_parent_dummy = OrOperator()
        filter_node.setParent(new_parent_dummy)
        self.assertIs(filter_node.parent(), new_parent_dummy)

        self.assertIs(filter_node.child(0), None)

        self.assertEqual(filter_node.childCount(), 0)

        self.assertEqual(filter_node.authorName(), "Jane Doe")
        self.assertEqual(filter_node.data(2), "Jane Doe")

        filter_node.setAuthorName("Jane Doe 2")
        self.assertEqual(filter_node.authorName(), "Jane Doe 2")
        self.assertEqual(filter_node.data(2), "Jane Doe 2")

        filter_node.setData(2, "Jane Doe 3")
        self.assertEqual(filter_node.authorName(), "Jane Doe 3")
        self.assertEqual(filter_node.data(2), "Jane Doe 3")

        self.assertEqual(filter_node.authorEmail(), "doe@example.com")
        self.assertEqual(filter_node.data(3), "doe@example.com")

        filter_node.setAuthorEmail("doe2@example.com")
        self.assertEqual(filter_node.authorEmail(), "doe2@example.com")
        self.assertEqual(filter_node.data(3), "doe2@example.com")

        filter_node.setData(3, "doe3@example.com")
        self.assertEqual(filter_node.authorEmail(), "doe3@example.com")
        self.assertEqual(filter_node.data(3), "doe3@example.com")

        self.assertEqual(filter_node.resource(), ":/breeze/light/im-user.svg")

    def test_committer_filter(self):
        filter_node = self.committer_filter

        self.assertEqual(filter_node.name(), "CommitterFilter")
        self.assertEqual(filter_node.data(0), "CommitterFilter")

        filter_node.setData(0, "name_2")
        self.assertEqual(filter_node.name(), "CommitterFilter",
                         "Name should be read-only!")
        self.assertEqual(filter_node.data(0), "CommitterFilter",
                         "Name should be read-only!")

        self.assertEqual(filter_node.comment(), "comment")
        self.assertEqual(filter_node.data(1), "comment")

        filter_node.setComment("comment_2")
        self.assertEqual(filter_node.comment(), "comment_2")
        self.assertEqual(filter_node.data(1), "comment_2")

        filter_node.setData(1, "comment_3")
        self.assertEqual(filter_node.comment(), "comment_3")
        self.assertEqual(filter_node.data(1), "comment_3")

        self.assertIs(filter_node.parent(), self.parent_dummy)

        new_parent_dummy = OrOperator()
        filter_node.setParent(new_parent_dummy)
        self.assertIs(filter_node.parent(), new_parent_dummy)

        self.assertIs(filter_node.child(0), None)

        self.assertEqual(filter_node.childCount(), 0)

        self.assertEqual(filter_node.committerName(), "Jane Doe")
        self.assertEqual(filter_node.data(2), "Jane Doe")

        filter_node.setCommitterName("Jane Doe 2")
        self.assertEqual(filter_node.committerName(), "Jane Doe 2")
        self.assertEqual(filter_node.data(2), "Jane Doe 2")

        filter_node.setData(2, "Jane Doe 3")
        self.assertEqual(filter_node.committerName(), "Jane Doe 3")
        self.assertEqual(filter_node.data(2), "Jane Doe 3")

        self.assertEqual(filter_node.committerEmail(), "doe@example.com")
        self.assertEqual(filter_node.data(3), "doe@example.com")

        filter_node.setCommitterEmail("doe2@example.com")
        self.assertEqual(filter_node.committerEmail(), "doe2@example.com")
        self.assertEqual(filter_node.data(3), "doe2@example.com")

        filter_node.setData(3, "doe3@example.com")
        self.assertEqual(filter_node.committerEmail(), "doe3@example.com")
        self.assertEqual(filter_node.data(3), "doe3@example.com")

        self.assertEqual(filter_node.resource(), ":/breeze/light/im-user.svg")

    def test_author_date_min_filter(self):
        filter_node = self.author_date_min_filter

        self.assertEqual(filter_node.name(), "AuthorDateMinFilter")
        self.assertEqual(filter_node.data(0), "AuthorDateMinFilter")

        filter_node.setData(0, "name_2")
        self.assertEqual(filter_node.name(), "AuthorDateMinFilter",
                         "Name should be read-only!")
        self.assertEqual(filter_node.data(0), "AuthorDateMinFilter",
                         "Name should be read-only!")

        self.assertEqual(filter_node.comment(), "comment")
        self.assertEqual(filter_node.data(1), "comment")

        filter_node.setComment("comment_2")
        self.assertEqual(filter_node.comment(), "comment_2")
        self.assertEqual(filter_node.data(1), "comment_2")

        filter_node.setData(1, "comment_3")
        self.assertEqual(filter_node.comment(), "comment_3")
        self.assertEqual(filter_node.data(1), "comment_3")

        self.assertIs(filter_node.parent(), self.parent_dummy)

        new_parent_dummy = OrOperator()
        filter_node.setParent(new_parent_dummy)
        self.assertIs(filter_node.parent(), new_parent_dummy)

        self.assertIs(filter_node.child(0), None)

        self.assertEqual(filter_node.childCount(), 0)

        self.assertEqual(filter_node.authorDateMin().toString(Qt.ISODate),
                         "2000-01-01T00:00:00Z")
        self.assertEqual(filter_node.data(2).toString(Qt.ISODate),
                         "2000-01-01T00:00:00Z")

        filter_node.setAuthorDateMin(QDateTime.fromString("2010-01-01T00:00:00Z", Qt.ISODate))
        self.assertEqual(filter_node.authorDateMin().toString(Qt.ISODate),
                         "2010-01-01T00:00:00Z")
        self.assertEqual(filter_node.data(2).toString(Qt.ISODate),
                         "2010-01-01T00:00:00Z")

        filter_node.setData(2, QDateTime.fromString("2015-01-01T00:00:00Z", Qt.ISODate))
        self.assertEqual(filter_node.authorDateMin().toString(Qt.ISODate),
                         "2015-01-01T00:00:00Z")
        self.assertEqual(filter_node.data(2).toString(Qt.ISODate),
                         "2015-01-01T00:00:00Z")

        self.assertEqual(filter_node.resource(), ":/breeze/light/appointment-new.svg")

    def test_author_date_max_filter(self):
        filter_node = self.author_date_max_filter

        self.assertEqual(filter_node.name(), "AuthorDateMaxFilter")
        self.assertEqual(filter_node.data(0), "AuthorDateMaxFilter")

        filter_node.setData(0, "name_2")
        self.assertEqual(filter_node.name(), "AuthorDateMaxFilter",
                         "Name should be read-only!")
        self.assertEqual(filter_node.data(0), "AuthorDateMaxFilter",
                         "Name should be read-only!")

        self.assertEqual(filter_node.comment(), "comment")
        self.assertEqual(filter_node.data(1), "comment")

        filter_node.setComment("comment_2")
        self.assertEqual(filter_node.comment(), "comment_2")
        self.assertEqual(filter_node.data(1), "comment_2")

        filter_node.setData(1, "comment_3")
        self.assertEqual(filter_node.comment(), "comment_3")
        self.assertEqual(filter_node.data(1), "comment_3")

        self.assertIs(filter_node.parent(), self.parent_dummy)

        new_parent_dummy = OrOperator()
        filter_node.setParent(new_parent_dummy)
        self.assertIs(filter_node.parent(), new_parent_dummy)

        self.assertIs(filter_node.child(0), None)

        self.assertEqual(filter_node.childCount(), 0)

        self.assertEqual(filter_node.authorDateMax().toString(Qt.ISODate),
                         "2000-01-01T00:00:00Z")
        self.assertEqual(filter_node.data(2).toString(Qt.ISODate),
                         "2000-01-01T00:00:00Z")

        filter_node.setAuthorDateMax(QDateTime.fromString("2010-01-01T00:00:00Z", Qt.ISODate))
        self.assertEqual(filter_node.authorDateMax().toString(Qt.ISODate),
                         "2010-01-01T00:00:00Z")
        self.assertEqual(filter_node.data(2).toString(Qt.ISODate),
                         "2010-01-01T00:00:00Z")

        filter_node.setData(2, QDateTime.fromString("2015-01-01T00:00:00Z", Qt.ISODate))
        self.assertEqual(filter_node.authorDateMax().toString(Qt.ISODate),
                         "2015-01-01T00:00:00Z")
        self.assertEqual(filter_node.data(2).toString(Qt.ISODate),
                         "2015-01-01T00:00:00Z")

        self.assertEqual(filter_node.resource(), ":/breeze/light/appointment-new.svg")

    def test_commit_date_min_filter(self):
        filter_node = self.commit_date_min_filter

        self.assertEqual(filter_node.name(), "CommitDateMinFilter")
        self.assertEqual(filter_node.data(0), "CommitDateMinFilter")

        filter_node.setData(0, "name_2")
        self.assertEqual(filter_node.name(), "CommitDateMinFilter",
                         "Name should be read-only!")
        self.assertEqual(filter_node.data(0), "CommitDateMinFilter",
                         "Name should be read-only!")

        self.assertEqual(filter_node.comment(), "comment")
        self.assertEqual(filter_node.data(1), "comment")

        filter_node.setComment("comment_2")
        self.assertEqual(filter_node.comment(), "comment_2")
        self.assertEqual(filter_node.data(1), "comment_2")

        filter_node.setData(1, "comment_3")
        self.assertEqual(filter_node.comment(), "comment_3")
        self.assertEqual(filter_node.data(1), "comment_3")

        self.assertIs(filter_node.parent(), self.parent_dummy)

        new_parent_dummy = OrOperator()
        filter_node.setParent(new_parent_dummy)
        self.assertIs(filter_node.parent(), new_parent_dummy)

        self.assertIs(filter_node.child(0), None)

        self.assertEqual(filter_node.childCount(), 0)

        self.assertEqual(filter_node.commitDateMin().toString(Qt.ISODate),
                         "2000-01-01T00:00:00Z")
        self.assertEqual(filter_node.data(2).toString(Qt.ISODate),
                         "2000-01-01T00:00:00Z")

        filter_node.setCommitDateMin(QDateTime.fromString("2010-01-01T00:00:00Z", Qt.ISODate))
        self.assertEqual(filter_node.commitDateMin().toString(Qt.ISODate),
                         "2010-01-01T00:00:00Z")
        self.assertEqual(filter_node.data(2).toString(Qt.ISODate),
                         "2010-01-01T00:00:00Z")

        filter_node.setData(2, QDateTime.fromString("2015-01-01T00:00:00Z", Qt.ISODate))
        self.assertEqual(filter_node.commitDateMin().toString(Qt.ISODate),
                         "2015-01-01T00:00:00Z")
        self.assertEqual(filter_node.data(2).toString(Qt.ISODate),
                         "2015-01-01T00:00:00Z")

        self.assertEqual(filter_node.resource(), ":/breeze/light/appointment-new.svg")

    def test_commit_date_max_filter(self):
        filter_node = self.commit_date_max_filter

        self.assertEqual(filter_node.name(), "CommitDateMaxFilter")
        self.assertEqual(filter_node.data(0), "CommitDateMaxFilter")

        filter_node.setData(0, "name_2")
        self.assertEqual(filter_node.name(), "CommitDateMaxFilter",
                         "Name should be read-only!")
        self.assertEqual(filter_node.data(0), "CommitDateMaxFilter",
                         "Name should be read-only!")

        self.assertEqual(filter_node.comment(), "comment")
        self.assertEqual(filter_node.data(1), "comment")

        filter_node.setComment("comment_2")
        self.assertEqual(filter_node.comment(), "comment_2")
        self.assertEqual(filter_node.data(1), "comment_2")

        filter_node.setData(1, "comment_3")
        self.assertEqual(filter_node.comment(), "comment_3")
        self.assertEqual(filter_node.data(1), "comment_3")

        self.assertIs(filter_node.parent(), self.parent_dummy)

        new_parent_dummy = OrOperator()
        filter_node.setParent(new_parent_dummy)
        self.assertIs(filter_node.parent(), new_parent_dummy)

        self.assertIs(filter_node.child(0), None)

        self.assertEqual(filter_node.childCount(), 0)

        self.assertEqual(filter_node.commitDateMax().toString(Qt.ISODate),
                         "2000-01-01T00:00:00Z")
        self.assertEqual(filter_node.data(2).toString(Qt.ISODate),
                         "2000-01-01T00:00:00Z")

        filter_node.setCommitDateMax(QDateTime.fromString("2010-01-01T00:00:00Z", Qt.ISODate))
        self.assertEqual(filter_node.commitDateMax().toString(Qt.ISODate),
                         "2010-01-01T00:00:00Z")
        self.assertEqual(filter_node.data(2).toString(Qt.ISODate),
                         "2010-01-01T00:00:00Z")

        filter_node.setData(2, QDateTime.fromString("2015-01-01T00:00:00Z", Qt.ISODate))
        self.assertEqual(filter_node.commitDateMax().toString(Qt.ISODate),
                         "2015-01-01T00:00:00Z")
        self.assertEqual(filter_node.data(2).toString(Qt.ISODate),
                         "2015-01-01T00:00:00Z")

        self.assertEqual(filter_node.resource(), ":/breeze/light/appointment-new.svg")

    def test_author_date_delta_min_filter(self):
        filter_node = self.author_date_delta_min_filter

        self.assertEqual(filter_node.name(), "AuthorDateDeltaMinFilter")
        self.assertEqual(filter_node.data(0), "AuthorDateDeltaMinFilter")

        filter_node.setData(0, "name_2")
        self.assertEqual(filter_node.name(), "AuthorDateDeltaMinFilter",
                         "Name should be read-only!")
        self.assertEqual(filter_node.data(0), "AuthorDateDeltaMinFilter",
                         "Name should be read-only!")

        self.assertEqual(filter_node.comment(), "comment")
        self.assertEqual(filter_node.data(1), "comment")

        filter_node.setComment("comment_2")
        self.assertEqual(filter_node.comment(), "comment_2")
        self.assertEqual(filter_node.data(1), "comment_2")

        filter_node.setData(1, "comment_3")
        self.assertEqual(filter_node.comment(), "comment_3")
        self.assertEqual(filter_node.data(1), "comment_3")

        self.assertIs(filter_node.parent(), self.parent_dummy)

        new_parent_dummy = OrOperator()
        filter_node.setParent(new_parent_dummy)
        self.assertIs(filter_node.parent(), new_parent_dummy)

        self.assertIs(filter_node.child(0), None)

        self.assertEqual(filter_node.childCount(), 0)

        self.assertEqual(filter_node.authorDateDeltaMin(), "P3DT12H30M")
        self.assertEqual(filter_node.data(2), "P3DT12H30M")

        filter_node.setAuthorDateDeltaMin("P23DT12H30M")
        self.assertEqual(filter_node.authorDateDeltaMin(), "P23DT12H30M")
        self.assertEqual(filter_node.data(2), "P23DT12H30M")

        filter_node.setData(2, "P42DT12H30M")
        self.assertEqual(filter_node.authorDateDeltaMin(), "P42DT12H30M")
        self.assertEqual(filter_node.data(2), "P42DT12H30M")

        self.assertEqual(filter_node.resource(), ":/breeze/light/chronometer.svg")

    def test_author_date_delta_max_filter(self):
        filter_node = self.author_date_delta_max_filter

        self.assertEqual(filter_node.name(), "AuthorDateDeltaMaxFilter")
        self.assertEqual(filter_node.data(0), "AuthorDateDeltaMaxFilter")

        filter_node.setData(0, "name_2")
        self.assertEqual(filter_node.name(), "AuthorDateDeltaMaxFilter",
                         "Name should be read-only!")
        self.assertEqual(filter_node.data(0), "AuthorDateDeltaMaxFilter",
                         "Name should be read-only!")

        self.assertEqual(filter_node.comment(), "comment")
        self.assertEqual(filter_node.data(1), "comment")

        filter_node.setComment("comment_2")
        self.assertEqual(filter_node.comment(), "comment_2")
        self.assertEqual(filter_node.data(1), "comment_2")

        filter_node.setData(1, "comment_3")
        self.assertEqual(filter_node.comment(), "comment_3")
        self.assertEqual(filter_node.data(1), "comment_3")

        self.assertIs(filter_node.parent(), self.parent_dummy)

        new_parent_dummy = OrOperator()
        filter_node.setParent(new_parent_dummy)
        self.assertIs(filter_node.parent(), new_parent_dummy)

        self.assertIs(filter_node.child(0), None)

        self.assertEqual(filter_node.childCount(), 0)

        self.assertEqual(filter_node.authorDateDeltaMax(), "P3DT12H30M")
        self.assertEqual(filter_node.data(2), "P3DT12H30M")

        filter_node.setAuthorDateDeltaMax("P23DT12H30M")
        self.assertEqual(filter_node.authorDateDeltaMax(), "P23DT12H30M")
        self.assertEqual(filter_node.data(2), "P23DT12H30M")

        filter_node.setData(2, "P42DT12H30M")
        self.assertEqual(filter_node.authorDateDeltaMax(), "P42DT12H30M")
        self.assertEqual(filter_node.data(2), "P42DT12H30M")

        self.assertEqual(filter_node.resource(), ":/breeze/light/chronometer.svg")

    def test_commit_date_delta_min_filter(self):
        filter_node = self.commit_date_delta_min_filter

        self.assertEqual(filter_node.name(), "CommitDateDeltaMinFilter")
        self.assertEqual(filter_node.data(0), "CommitDateDeltaMinFilter")

        filter_node.setData(0, "name_2")
        self.assertEqual(filter_node.name(), "CommitDateDeltaMinFilter",
                         "Name should be read-only!")
        self.assertEqual(filter_node.data(0), "CommitDateDeltaMinFilter",
                         "Name should be read-only!")

        self.assertEqual(filter_node.comment(), "comment")
        self.assertEqual(filter_node.data(1), "comment")

        filter_node.setComment("comment_2")
        self.assertEqual(filter_node.comment(), "comment_2")
        self.assertEqual(filter_node.data(1), "comment_2")

        filter_node.setData(1, "comment_3")
        self.assertEqual(filter_node.comment(), "comment_3")
        self.assertEqual(filter_node.data(1), "comment_3")

        self.assertIs(filter_node.parent(), self.parent_dummy)

        new_parent_dummy = OrOperator()
        filter_node.setParent(new_parent_dummy)
        self.assertIs(filter_node.parent(), new_parent_dummy)

        self.assertIs(filter_node.child(0), None)

        self.assertEqual(filter_node.childCount(), 0)

        self.assertEqual(filter_node.commitDateDeltaMin(), "P3DT12H30M")
        self.assertEqual(filter_node.data(2), "P3DT12H30M")

        filter_node.setCommitDateDeltaMin("P23DT12H30M")
        self.assertEqual(filter_node.commitDateDeltaMin(), "P23DT12H30M")
        self.assertEqual(filter_node.data(2), "P23DT12H30M")

        filter_node.setData(2, "P42DT12H30M")
        self.assertEqual(filter_node.commitDateDeltaMin(), "P42DT12H30M")
        self.assertEqual(filter_node.data(2), "P42DT12H30M")

        self.assertEqual(filter_node.resource(), ":/breeze/light/chronometer.svg")

    def test_commit_date_delta_max_filter(self):
        filter_node = self.commit_date_delta_max_filter

        self.assertEqual(filter_node.name(), "CommitDateDeltaMaxFilter")
        self.assertEqual(filter_node.data(0), "CommitDateDeltaMaxFilter")

        filter_node.setData(0, "name_2")
        self.assertEqual(filter_node.name(), "CommitDateDeltaMaxFilter",
                         "Name should be read-only!")
        self.assertEqual(filter_node.data(0), "CommitDateDeltaMaxFilter",
                         "Name should be read-only!")

        self.assertEqual(filter_node.comment(), "comment")
        self.assertEqual(filter_node.data(1), "comment")

        filter_node.setComment("comment_2")
        self.assertEqual(filter_node.comment(), "comment_2")
        self.assertEqual(filter_node.data(1), "comment_2")

        filter_node.setData(1, "comment_3")
        self.assertEqual(filter_node.comment(), "comment_3")
        self.assertEqual(filter_node.data(1), "comment_3")

        self.assertIs(filter_node.parent(), self.parent_dummy)

        new_parent_dummy = OrOperator()
        filter_node.setParent(new_parent_dummy)
        self.assertIs(filter_node.parent(), new_parent_dummy)

        self.assertIs(filter_node.child(0), None)

        self.assertEqual(filter_node.childCount(), 0)

        self.assertEqual(filter_node.commitDateDeltaMax(), "P3DT12H30M")
        self.assertEqual(filter_node.data(2), "P3DT12H30M")

        filter_node.setCommitDateDeltaMax("P23DT12H30M")
        self.assertEqual(filter_node.commitDateDeltaMax(), "P23DT12H30M")
        self.assertEqual(filter_node.data(2), "P23DT12H30M")

        filter_node.setData(2, "P42DT12H30M")
        self.assertEqual(filter_node.commitDateDeltaMax(), "P42DT12H30M")
        self.assertEqual(filter_node.data(2), "P42DT12H30M")

        self.assertEqual(filter_node.resource(), ":/breeze/light/chronometer.svg")

    def test_and_operator(self):
        filter_node = self.and_operator

        self.assertEqual(filter_node.name(), "AndOperator")
        self.assertEqual(filter_node.data(0), "AndOperator")

        filter_node.setData(0, "name_2")
        self.assertEqual(filter_node.name(), "AndOperator",
                         "Name should be read-only!")
        self.assertEqual(filter_node.data(0), "AndOperator",
                         "Name should be read-only!")

        self.assertEqual(filter_node.comment(), "comment")
        self.assertEqual(filter_node.data(1), "comment")

        filter_node.setComment("comment_2")
        self.assertEqual(filter_node.comment(), "comment_2")
        self.assertEqual(filter_node.data(1), "comment_2")

        filter_node.setData(1, "comment_3")
        self.assertEqual(filter_node.comment(), "comment_3")
        self.assertEqual(filter_node.data(1), "comment_3")

        self.assertIs(filter_node.parent(), self.parent_dummy)

        new_parent_dummy = OrOperator()
        filter_node.setParent(new_parent_dummy)
        self.assertIs(filter_node.parent(), new_parent_dummy)

        self.assertIs(filter_node.child(0), None)
        self.assertEqual(filter_node.childCount(), 0)

        child1 = NotOperator()
        child2 = NotOperator()
        child3 = NotOperator()

        filter_node.addChild(child1)
        self.assertEqual(filter_node.childCount(), 1)
        self.assertIs(filter_node.child(0), child1)
        self.assertIs(child1.parent(), filter_node)

        self.assertIs(filter_node.child(-1), None)
        self.assertIs(filter_node.child(1), None)

        filter_node.addChild(child2)
        self.assertEqual(filter_node.childCount(), 2)
        self.assertIs(filter_node.child(0), child1)
        self.assertIs(filter_node.child(1), child2)
        self.assertIs(child2.parent(), filter_node)

        filter_node.insertChild(1, child3)
        self.assertEqual(filter_node.childCount(), 3)
        self.assertIs(filter_node.child(0), child1)
        self.assertIs(filter_node.child(1), child3)
        self.assertIs(filter_node.child(2), child2)
        self.assertIs(child3.parent(), filter_node)

        filter_node.moveChild(1, 3)
        self.assertEqual(filter_node.childCount(), 3)
        self.assertIs(filter_node.child(0), child1)
        self.assertIs(filter_node.child(1), child2)
        self.assertIs(filter_node.child(2), child3)

        filter_node.removeChild(1)
        self.assertEqual(filter_node.childCount(), 2)
        self.assertIs(filter_node.child(0), child1)
        self.assertIs(filter_node.child(1), child3)
        self.assertIs(child2.parent(), None)

        self.assertEqual(filter_node.resource(), ":/operators/and-operator.svg")

    def test_or_operator(self):
        filter_node = self.or_operator

        self.assertEqual(filter_node.name(), "OrOperator")
        self.assertEqual(filter_node.data(0), "OrOperator")

        filter_node.setData(0, "name_2")
        self.assertEqual(filter_node.name(), "OrOperator",
                         "Name should be read-only!")
        self.assertEqual(filter_node.data(0), "OrOperator",
                         "Name should be read-only!")

        self.assertEqual(filter_node.comment(), "comment")
        self.assertEqual(filter_node.data(1), "comment")

        filter_node.setComment("comment_2")
        self.assertEqual(filter_node.comment(), "comment_2")
        self.assertEqual(filter_node.data(1), "comment_2")

        filter_node.setData(1, "comment_3")
        self.assertEqual(filter_node.comment(), "comment_3")
        self.assertEqual(filter_node.data(1), "comment_3")

        self.assertIs(filter_node.parent(), self.parent_dummy)

        new_parent_dummy = OrOperator()
        filter_node.setParent(new_parent_dummy)
        self.assertIs(filter_node.parent(), new_parent_dummy)

        self.assertIs(filter_node.child(0), None)
        self.assertEqual(filter_node.childCount(), 0)

        child1 = NotOperator()
        child2 = NotOperator()
        child3 = NotOperator()

        filter_node.addChild(child1)
        self.assertEqual(filter_node.childCount(), 1)
        self.assertIs(filter_node.child(0), child1)
        self.assertIs(child1.parent(), filter_node)

        self.assertIs(filter_node.child(-1), None)
        self.assertIs(filter_node.child(1), None)

        filter_node.addChild(child2)
        self.assertEqual(filter_node.childCount(), 2)
        self.assertIs(filter_node.child(0), child1)
        self.assertIs(filter_node.child(1), child2)
        self.assertIs(child2.parent(), filter_node)

        filter_node.insertChild(1, child3)
        self.assertEqual(filter_node.childCount(), 3)
        self.assertIs(filter_node.child(0), child1)
        self.assertIs(filter_node.child(1), child3)
        self.assertIs(filter_node.child(2), child2)
        self.assertIs(child3.parent(), filter_node)

        filter_node.moveChild(1, 3)
        self.assertEqual(filter_node.childCount(), 3)
        self.assertIs(filter_node.child(0), child1)
        self.assertIs(filter_node.child(1), child2)
        self.assertIs(filter_node.child(2), child3)

        filter_node.removeChild(1)
        self.assertEqual(filter_node.childCount(), 2)
        self.assertIs(filter_node.child(0), child1)
        self.assertIs(filter_node.child(1), child3)
        self.assertIs(child2.parent(), None)

        self.assertEqual(filter_node.resource(), ":/operators/or-operator.svg")

    def test_not_operator(self):
        filter_node = self.not_operator

        self.assertEqual(filter_node.name(), "NotOperator")
        self.assertEqual(filter_node.data(0), "NotOperator")

        filter_node.setData(0, "name_2")
        self.assertEqual(filter_node.name(), "NotOperator",
                         "Name should be read-only!")
        self.assertEqual(filter_node.data(0), "NotOperator",
                         "Name should be read-only!")

        self.assertEqual(filter_node.comment(), "comment")
        self.assertEqual(filter_node.data(1), "comment")

        filter_node.setComment("comment_2")
        self.assertEqual(filter_node.comment(), "comment_2")
        self.assertEqual(filter_node.data(1), "comment_2")

        filter_node.setData(1, "comment_3")
        self.assertEqual(filter_node.comment(), "comment_3")
        self.assertEqual(filter_node.data(1), "comment_3")

        self.assertIs(filter_node.parent(), self.parent_dummy)

        new_parent_dummy = OrOperator()
        filter_node.setParent(new_parent_dummy)
        self.assertIs(filter_node.parent(), new_parent_dummy)

        self.assertIs(filter_node.child(0), None)
        self.assertEqual(filter_node.childCount(), 0)

        child1 = AndOperator()
        child2 = AndOperator()

        filter_node.addChild(child1)
        self.assertEqual(filter_node.childCount(), 1)
        self.assertIs(filter_node.child(0), child1)
        self.assertIs(child1.parent(), filter_node)

        self.assertIs(filter_node.child(-1), None)
        self.assertIs(filter_node.child(1), None)

        filter_node.removeChild(0)
        self.assertIs(filter_node.child(0), None)
        self.assertEqual(filter_node.childCount(), 0)
        self.assertIs(child1.parent(), None)

        filter_node.insertChild(0, child2)
        self.assertEqual(filter_node.childCount(), 1)
        self.assertIs(filter_node.child(0), child2)
        self.assertIs(child2.parent(), filter_node)

        self.assertEqual(filter_node.resource(), ":/operators/not-operator.svg")

    def test_source_operator(self):
        filter_node = self.source_operator

        self.assertEqual(filter_node.name(), "SourceOperator")
        self.assertEqual(filter_node.data(0), "SourceOperator")

        filter_node.setData(0, "name_2")
        self.assertEqual(filter_node.name(), "SourceOperator",
                         "Name should be read-only!")
        self.assertEqual(filter_node.data(0), "SourceOperator",
                         "Name should be read-only!")

        self.assertEqual(filter_node.comment(), "comment")
        self.assertEqual(filter_node.data(1), "comment")

        filter_node.setComment("comment_2")
        self.assertEqual(filter_node.comment(), "comment_2")
        self.assertEqual(filter_node.data(1), "comment_2")

        filter_node.setData(1, "comment_3")
        self.assertEqual(filter_node.comment(), "comment_3")
        self.assertEqual(filter_node.data(1), "comment_3")

        self.assertIs(filter_node.parent(), self.parent_dummy)

        new_parent_dummy = OrOperator()
        filter_node.setParent(new_parent_dummy)
        self.assertIs(filter_node.parent(), new_parent_dummy)

        self.assertIs(filter_node.child(0), None)
        self.assertEqual(filter_node.childCount(), 0)

        child1 = NotOperator()
        child2 = NotOperator()

        filter_node.addChild(child1)
        self.assertEqual(filter_node.childCount(), 1)
        self.assertIs(filter_node.child(0), child1)
        self.assertIs(child1.parent(), filter_node)

        self.assertIs(filter_node.child(-1), None)
        self.assertIs(filter_node.child(1), None)

        filter_node.removeChild(0)
        self.assertIs(filter_node.child(0), None)
        self.assertEqual(filter_node.childCount(), 0)
        self.assertIs(child1.parent(), None)

        filter_node.insertChild(0, child2)
        self.assertEqual(filter_node.childCount(), 1)
        self.assertIs(filter_node.child(0), child2)
        self.assertIs(child2.parent(), filter_node)

        self.assertEqual(filter_node.resource(), ":/operators/source-operator.svg")

    def test_target_operator(self):
        filter_node = self.target_operator

        self.assertEqual(filter_node.name(), "TargetOperator")
        self.assertEqual(filter_node.data(0), "TargetOperator")

        filter_node.setData(0, "name_2")
        self.assertEqual(filter_node.name(), "TargetOperator",
                         "Name should be read-only!")
        self.assertEqual(filter_node.data(0), "TargetOperator",
                         "Name should be read-only!")

        self.assertEqual(filter_node.comment(), "comment")
        self.assertEqual(filter_node.data(1), "comment")

        filter_node.setComment("comment_2")
        self.assertEqual(filter_node.comment(), "comment_2")
        self.assertEqual(filter_node.data(1), "comment_2")

        filter_node.setData(1, "comment_3")
        self.assertEqual(filter_node.comment(), "comment_3")
        self.assertEqual(filter_node.data(1), "comment_3")

        self.assertIs(filter_node.parent(), self.parent_dummy)

        new_parent_dummy = OrOperator()
        filter_node.setParent(new_parent_dummy)
        self.assertIs(filter_node.parent(), new_parent_dummy)

        self.assertIs(filter_node.child(0), None)
        self.assertEqual(filter_node.childCount(), 0)

        child1 = NotOperator()
        child2 = NotOperator()

        filter_node.addChild(child1)
        self.assertEqual(filter_node.childCount(), 1)
        self.assertIs(filter_node.child(0), child1)
        self.assertIs(child1.parent(), filter_node)

        self.assertIs(filter_node.child(-1), None)
        self.assertIs(filter_node.child(1), None)

        filter_node.removeChild(0)
        self.assertIs(filter_node.child(0), None)
        self.assertEqual(filter_node.childCount(), 0)
        self.assertIs(child1.parent(), None)

        filter_node.insertChild(0, child2)
        self.assertEqual(filter_node.childCount(), 1)
        self.assertIs(filter_node.child(0), child2)
        self.assertIs(child2.parent(), filter_node)

        self.assertEqual(filter_node.resource(), ":/operators/target-operator.svg")


class TestFilterTreeYamlLoad(unittest.TestCase):
    """
    Test filter tree loading from yaml file.
    """

    @classmethod
    def setUpClass(cls):
        with mock.patch('builtins.open',
                        new=mock.mock_open(read_data=YAML_DOC_1)):
            cls.root_node = yaml.load(open("path/to/open"), Loader=yaml.Loader)

    def test_filter_tree_yaml_load(self):
        node0 = self.root_node

        self.assertEqual(node0.name(), "AndOperator")
        self.assertEqual(node0.comment(), "")
        self.assertIs(node0.parent(), None)
        self.assertEqual(node0.childCount(), 1)

        node1 = node0.child(0)

        self.assertEqual(node1.name(), "OrOperator")
        self.assertEqual(node1.comment(), "comment")
        self.assertIs(node1.parent(), node0)
        self.assertEqual(node1.childCount(), 10)

        node2 = node1.child(0)
        node3 = node1.child(1)
        node4 = node1.child(2)
        node5 = node1.child(3)
        node6 = node1.child(4)
        node7 = node1.child(5)
        node8 = node1.child(6)
        node9 = node1.child(7)
        node10 = node1.child(8)
        node11 = node1.child(9)

        self.assertEqual(node2.name(), "SourceOperator")
        self.assertEqual(node2.comment(), "")
        self.assertIs(node2.parent(), node1)
        self.assertEqual(node2.childCount(), 1)

        self.assertEqual(node3.name(), "SourceOperator")
        self.assertEqual(node3.comment(), "")
        self.assertIs(node3.parent(), node1)
        self.assertEqual(node3.childCount(), 1)

        self.assertEqual(node4.name(), "TargetOperator")
        self.assertEqual(node4.comment(), "")
        self.assertIs(node4.parent(), node1)
        self.assertEqual(node4.childCount(), 1)

        self.assertEqual(node5.name(), "TargetOperator")
        self.assertEqual(node5.comment(), "")
        self.assertIs(node5.parent(), node1)
        self.assertEqual(node5.childCount(), 1)

        self.assertEqual(node6.name(), "TargetOperator")
        self.assertEqual(node6.comment(), "")
        self.assertIs(node6.parent(), node1)
        self.assertEqual(node6.childCount(), 1)

        self.assertEqual(node7.name(), "TargetOperator")
        self.assertEqual(node7.comment(), "")
        self.assertIs(node7.parent(), node1)
        self.assertEqual(node7.childCount(), 1)

        self.assertEqual(node8.name(), "AuthorDateDeltaMinFilter")
        self.assertEqual(node8.comment(), "")
        self.assertIs(node8.parent(), node1)
        self.assertEqual(node8.childCount(), 0)
        self.assertEqual(node8.authorDateDeltaMin(), "P1DT1H")

        self.assertEqual(node9.name(), "AuthorDateDeltaMaxFilter")
        self.assertEqual(node9.comment(), "")
        self.assertIs(node9.parent(), node1)
        self.assertEqual(node9.childCount(), 0)
        self.assertEqual(node9.authorDateDeltaMax(), "P1DT2H")

        self.assertEqual(node10.name(), "CommitDateDeltaMinFilter")
        self.assertEqual(node10.comment(), "")
        self.assertIs(node10.parent(), node1)
        self.assertEqual(node10.childCount(), 0)
        self.assertEqual(node10.commitDateDeltaMin(), "P1DT3H")

        self.assertEqual(node11.name(), "CommitDateDeltaMaxFilter")
        self.assertEqual(node11.comment(), "")
        self.assertIs(node11.parent(), node1)
        self.assertEqual(node11.childCount(), 0)
        self.assertEqual(node11.commitDateDeltaMax(), "P1DT4H")

        node12 = node2.child(0)
        node13 = node3.child(0)
        node14 = node4.child(0)
        node15 = node5.child(0)
        node16 = node6.child(0)
        node17 = node7.child(0)

        self.assertEqual(node12.name(), "CommitterFilter")
        self.assertEqual(node12.comment(), "")
        self.assertIs(node12.parent(), node2)
        self.assertEqual(node12.childCount(), 0)
        self.assertEqual(node12.committerName(), "Jane Doe")
        self.assertEqual(node12.committerEmail(), "doe@example.com")

        self.assertEqual(node13.name(), "NotOperator")
        self.assertEqual(node13.comment(), "")
        self.assertIs(node13.parent(), node3)
        self.assertEqual(node13.childCount(), 1)

        self.assertEqual(node14.name(), "AuthorDateMinFilter")
        self.assertEqual(node14.comment(), "")
        self.assertIs(node14.parent(), node4)
        self.assertEqual(node14.childCount(), 0)
        self.assertEqual(node14.authorDateMin().toString(Qt.ISODate),
                         "2000-01-01T00:00:00Z")

        self.assertEqual(node15.name(), "AuthorDateMaxFilter")
        self.assertEqual(node15.comment(), "")
        self.assertIs(node15.parent(), node5)
        self.assertEqual(node15.childCount(), 0)
        self.assertEqual(node15.authorDateMax().toString(Qt.ISODate),
                         "2001-01-01T00:00:00Z")

        self.assertEqual(node16.name(), "CommitDateMinFilter")
        self.assertEqual(node16.comment(), "")
        self.assertIs(node16.parent(), node6)
        self.assertEqual(node16.childCount(), 0)
        self.assertEqual(node16.commitDateMin().toString(Qt.ISODate),
                         "2002-01-01T00:00:00Z")

        self.assertEqual(node17.name(), "CommitDateMaxFilter")
        self.assertEqual(node17.comment(), "")
        self.assertIs(node17.parent(), node7)
        self.assertEqual(node17.childCount(), 0)
        self.assertEqual(node17.commitDateMax().toString(Qt.ISODate),
                         "2003-01-01T00:00:00Z")

        node18 = node13.child(0)

        self.assertEqual(node18.name(), "AuthorFilter")
        self.assertEqual(node18.comment(), "")
        self.assertIs(node18.parent(), node13)
        self.assertEqual(node18.childCount(), 0)
        self.assertEqual(node18.authorName(), "Jane Doe")
        self.assertEqual(node18.authorEmail(), "doe@example.com")

