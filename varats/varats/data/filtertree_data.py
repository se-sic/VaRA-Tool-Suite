"""
This file defines all available (commit interaction) filters. When evaluated, a
filter returns either KEEP or REMOVE for a given commit interaction, depending
on wheter the interaction matches the specific filter or not. KEEP means that
the interaction matches the filters and should be kept. REMOVE means the
opposite. The filters can be arranged in a tree structure. The two basic kinds
of filters are ConcreteInteractionFilter and FilterOperator.

ConcreteInteractionFilters represent the "actual" commit interaction filters.
These types of filters cannot have children, they can only appear as leaf-nodes
in the filter tree.
They are divided in the two kinds BinaryInteractionFilter and
UnaryInteractionFilter:

- BinaryInteractionFilters filter commit interactions based on both the source
  commit and the target commit of an interaction.
  For instance, the AuthorDateDeltaMinFilter filters out all interactions where
  the time difference of the source and target commit (of the interaction) is
  smaller than the specified time duration.
  This means that in order to evaluate such a filter, both the source and the
  target commit of an interaction must be known.
- UnaryInteractionFilters filter commit interactions based on either the source
  or the target commit of an interaction.

FilterOperators can be used to combine filters or to define the scope of a
Filter. In the filter tree, they can have one or more children (they must have
at least one child).

- The SourceOperator and TargetOperator types specify the scope of their child
  filter (they can have exactly one child).
  For example, a SourceOperator with a child filter of type AuthorFilter means
  that a commit interaction is filtered based on the author of the source
  commit of the interaction.
- The types AndOperator, OrOperator, and NotOperator represent the basic
  operators of Boolean algebra. AndOperators and OrOperators can have multiple
  children, while NotOperators can only have one.
  As an example, when evaluation an AndOperator, it will return KEEP iff all of
  its child filters return KEEP, otherwise it will return REMOVE.

The complete class hierarchy of InteractionFilters can be seen below:

InteractionFilter
  ├── FilterOperator
  │     ├── AndOperator
  │     ├── OrOperator
  │     ├── NotOperator
  │     ├── SourceOperator
  │     ├── TargetOperator
  └── ConcreteInteractionFilter
        ├── UnaryInteractionFilter
        │     ├── AuthorFilter
        │     ├── CommitterFilter
        │     ├── AuthorDateMinFilter
        │     ├── AuthorDateMaxFilter
        │     ├── CommitDateMinFilter
        │     └── CommitDateMaxFilter
        └── BinaryInteractionFilter
              ├── AuthorDateDeltaMinFilter
              ├── AuthorDateDeltaMaxFilter
              ├── CommitDateDeltaMinFilter
              └── CommitDateDeltaMaxFilter
"""

import typing as tp
from copy import deepcopy

import yaml
from PyQt5.QtCore import QDateTime, Qt

from varats.base.version_header import VersionHeader


class SecretYamlObject(yaml.YAMLObject):
    hidden_fields: tp.List[str] = []
    removed_fields: tp.List[str] = []

    @classmethod
    def to_yaml(cls, dumper: tp.Any, data: tp.Any) -> tp.Any:
        new_data = deepcopy(data)
        for item in cls.hidden_fields:
            new_data.__dict__[item] = None
        for item in cls.removed_fields:
            del new_data.__dict__[item]
        return dumper.represent_yaml_object(
            cls.yaml_tag, new_data, cls, flow_style=cls.yaml_flow_style
        )


class InteractionFilter(SecretYamlObject):
    hidden_fields = ["_parent"]
    yaml_tag = u'!InteractionFilter'

    def __init__(
        self,
        parent: tp.Optional['InteractionFilter'] = None,
        comment: tp.Optional[str] = None
    ) -> None:

        self._comment: str = ""
        self._type = type(self).__name__
        self._parent = parent

        if comment is not None:
            self._comment = comment

    def addChild(self, child: 'InteractionFilter') -> bool:
        return False

    def insertChild(self, position: int, child: 'InteractionFilter') -> bool:
        return False

    def moveChild(self, sourceRow: int, destinationRow: int) -> bool:
        return False

    def removeChild(self, position: int) -> bool:
        return False

    def name(self) -> str:
        return type(self).__name__

    def comment(self) -> str:
        return self._comment

    def setComment(self, comment: str) -> None:
        self._comment = comment

    def parent(self) -> tp.Optional['InteractionFilter']:
        return self._parent

    def setParent(self, parent: tp.Optional['InteractionFilter']) -> None:
        self._parent = parent

    def child(self, index: int) -> tp.Optional['InteractionFilter']:
        return None

    def childCount(self) -> int:
        return 0

    def indexOfChild(self, child: 'InteractionFilter') -> int:
        num_children = self.childCount()
        for i in range(num_children):
            if self.child(i) == child:
                return i
        raise ValueError("child not found")

    def row(self) -> tp.Optional[int]:
        if self._parent is not None:
            return self._parent.indexOfChild(self)
        return None

    def log(self, prefix: str = "", is_tail: bool = True) -> str:
        output = "" + prefix + ("└── "
                                if is_tail else "├── ") + self.name() + "\n"
        num_children = self.childCount()
        for i in range(num_children - 1):
            child = self.child(i)
            if child:
                output += child.log(
                    prefix + ("    " if is_tail else "│   "), False
                )
        if num_children > 0:
            child = self.child(num_children - 1)
            if child:
                output += child.log(
                    prefix + ("    " if is_tail else "│   "), True
                )
        return output

    def __repr__(self) -> str:
        return self.log()

    def data(self, column: int) -> tp.Any:
        if column == 0:
            return self.name()
        if column == 1:
            return self.comment()
        return None

    def setData(self, column: int, value: tp.Any) -> None:
        if column == 0:
            pass
        elif column == 1:
            self.setComment(value)

    def fixParentPointers(self) -> None:
        """
        Iterate over the filter tree and set the correct _parent pointers for
        all nodes.

        Note:
            Must be called on the root node of the tree!
        """
        for i in range(self.childCount()):
            child = self.child(i)
            if child:
                child.__fixParentPointersHelper(self)

    def __fixParentPointersHelper(self, parent: 'InteractionFilter') -> None:
        self.setParent(parent)
        for i in range(self.childCount()):
            child = self.child(i)
            if child:
                child.__fixParentPointersHelper(self)

    def hasFilterTypeAsParent(self, parent_type: tp.Any) -> bool:
        """Checks if there is a node of type parent_type on the path from the
        current node to the root."""
        parent = self.parent()
        while parent is not None:
            if isinstance(parent, parent_type):
                return True
            parent = parent.parent()

        return False

    @staticmethod
    def resource() -> tp.Optional[str]:
        return None

    @staticmethod
    def getVersionHeader() -> VersionHeader:
        return VersionHeader.from_version_number("InteractionFilter", 1)


class ConcreteInteractionFilter(InteractionFilter):
    yaml_tag = u'!ConcreteInteractionFilter'

    def __init__(
        self,
        parent: tp.Optional[InteractionFilter] = None,
        comment: tp.Optional[str] = None
    ) -> None:
        super().__init__(parent, comment)


class UnaryInteractionFilter(ConcreteInteractionFilter):
    yaml_tag = u'!UnaryInteractionFilter'

    def __init__(
        self,
        parent: tp.Optional[InteractionFilter] = None,
        comment: tp.Optional[str] = None
    ) -> None:
        super().__init__(parent, comment)


class BinaryInteractionFilter(ConcreteInteractionFilter):
    yaml_tag = u'!BinaryInteractionFilter'

    def __init__(
        self,
        parent: tp.Optional[InteractionFilter] = None,
        comment: tp.Optional[str] = None
    ) -> None:
        super().__init__(parent, comment)


class AuthorFilter(UnaryInteractionFilter):
    yaml_tag = u'!AuthorFilter'

    def __init__(
        self,
        parent: tp.Optional[InteractionFilter] = None,
        comment: tp.Optional[str] = None,
        author_name: str = "",
        author_email: str = ""
    ) -> None:
        super().__init__(parent, comment)
        self._author_name = author_name
        self._author_email = author_email

    def authorName(self) -> str:
        return self._author_name

    def setAuthorName(self, author_name: str) -> None:
        self._author_name = author_name

    def authorEmail(self) -> str:
        return self._author_email

    def setAuthorEmail(self, author_email: str) -> None:
        self._author_email = author_email

    def data(self, column: int) -> tp.Any:
        val = super().data(column)

        if column == 2:
            val = self.authorName()
        elif column == 3:
            val = self.authorEmail()

        return val

    def setData(self, column: int, value: tp.Any) -> None:
        super().setData(column, value)

        if column == 2:
            self.setAuthorName(value)
        elif column == 3:
            self.setAuthorEmail(value)

    @staticmethod
    def resource() -> str:
        return ":/breeze/light/im-user.svg"


class CommitterFilter(UnaryInteractionFilter):
    yaml_tag = u'!CommitterFilter'

    def __init__(
        self,
        parent: tp.Optional[InteractionFilter] = None,
        comment: tp.Optional[str] = None,
        committer_name: str = "",
        committer_email: str = ""
    ) -> None:
        super().__init__(parent, comment)
        self._committer_name = committer_name
        self._committer_email = committer_email

    def committerName(self) -> str:
        return self._committer_name

    def setCommitterName(self, committer_name: str) -> None:
        self._committer_name = committer_name

    def committerEmail(self) -> str:
        return self._committer_email

    def setCommitterEmail(self, committer_email: str) -> None:
        self._committer_email = committer_email

    def data(self, column: int) -> tp.Any:
        val = super().data(column)

        if column == 2:
            val = self.committerName()
        elif column == 3:
            val = self.committerEmail()

        return val

    def setData(self, column: int, value: tp.Any) -> None:
        super().setData(column, value)

        if column == 2:
            self.setCommitterName(value)
        elif column == 3:
            self.setCommitterEmail(value)

    @staticmethod
    def resource() -> str:
        return ":/breeze/light/im-user.svg"


class AuthorDateMinFilter(UnaryInteractionFilter):
    yaml_tag = u'!AuthorDateMinFilter'

    def __init__(
        self,
        parent: tp.Optional[InteractionFilter] = None,
        comment: tp.Optional[str] = None,
        author_date_min: tp.Optional[str] = None
    ) -> None:
        super().__init__(parent, comment)
        if author_date_min:
            self._author_date_min = author_date_min
        else:
            self._author_date_min = "1970-01-01T00:00:00Z"

    def authorDateMin(self) -> QDateTime:
        return QDateTime.fromString(self._author_date_min, Qt.ISODate)

    def setAuthorDateMin(self, author_date_min: QDateTime) -> None:
        self._author_date_min = author_date_min.toString(Qt.ISODate)

    def data(self, column: int) -> tp.Any:
        val = super().data(column)

        if column == 2:
            val = self.authorDateMin()

        return val

    def setData(self, column: int, value: tp.Any) -> None:
        super().setData(column, value)

        if column == 2:
            self.setAuthorDateMin(value)

    @staticmethod
    def resource() -> str:
        return ":/breeze/light/appointment-new.svg"


class AuthorDateMaxFilter(UnaryInteractionFilter):
    yaml_tag = u'!AuthorDateMaxFilter'

    def __init__(
        self,
        parent: tp.Optional[InteractionFilter] = None,
        comment: tp.Optional[str] = None,
        author_date_max: tp.Optional[str] = None
    ) -> None:
        super().__init__(parent, comment)
        if author_date_max:
            self._author_date_max = author_date_max
        else:
            self._author_date_max = "1970-01-01T00:00:00Z"

    def authorDateMax(self) -> QDateTime:
        return QDateTime.fromString(self._author_date_max, Qt.ISODate)

    def setAuthorDateMax(self, author_date_max: QDateTime) -> None:
        self._author_date_max = author_date_max.toString(Qt.ISODate)

    def data(self, column: int) -> tp.Any:
        val = super().data(column)

        if column == 2:
            val = self.authorDateMax()

        return val

    def setData(self, column: int, value: tp.Any) -> None:
        super().setData(column, value)

        if column == 2:
            self.setAuthorDateMax(value)

    @staticmethod
    def resource() -> str:
        return ":/breeze/light/appointment-new.svg"


class CommitDateMinFilter(UnaryInteractionFilter):
    yaml_tag = u'!CommitDateMinFilter'

    def __init__(
        self,
        parent: tp.Optional[InteractionFilter] = None,
        comment: tp.Optional[str] = None,
        commit_date_min: tp.Optional[str] = None
    ) -> None:
        super().__init__(parent, comment)
        if commit_date_min:
            self._commit_date_min = commit_date_min
        else:
            self._commit_date_min = "1970-01-01T00:00:00Z"

    def commitDateMin(self) -> QDateTime:
        return QDateTime.fromString(self._commit_date_min, Qt.ISODate)

    def setCommitDateMin(self, commit_date_min: QDateTime) -> None:
        self._commit_date_min = commit_date_min.toString(Qt.ISODate)

    def data(self, column: int) -> tp.Any:
        val = super().data(column)

        if column == 2:
            val = self.commitDateMin()

        return val

    def setData(self, column: int, value: tp.Any) -> None:
        super().setData(column, value)

        if column == 2:
            self.setCommitDateMin(value)

    @staticmethod
    def resource() -> str:
        return ":/breeze/light/appointment-new.svg"


class CommitDateMaxFilter(UnaryInteractionFilter):
    yaml_tag = u'!CommitDateMaxFilter'

    def __init__(
        self,
        parent: tp.Optional[InteractionFilter] = None,
        comment: tp.Optional[str] = None,
        commit_date_max: tp.Optional[str] = None
    ) -> None:
        super().__init__(parent, comment)
        if commit_date_max:
            self._commit_date_max = commit_date_max
        else:
            self._commit_date_max = "1970-01-01T00:00:00Z"

    def commitDateMax(self) -> QDateTime:
        return QDateTime.fromString(self._commit_date_max, Qt.ISODate)

    def setCommitDateMax(self, commit_date_max: QDateTime) -> None:
        self._commit_date_max = commit_date_max.toString(Qt.ISODate)

    def data(self, column: int) -> tp.Any:
        val = super().data(column)

        if column == 2:
            val = self.commitDateMax()

        return val

    def setData(self, column: int, value: tp.Any) -> None:
        super().setData(column, value)

        if column == 2:
            self.setCommitDateMax(value)

    @staticmethod
    def resource() -> str:
        return ":/breeze/light/appointment-new.svg"


class AuthorDateDeltaMinFilter(BinaryInteractionFilter):
    yaml_tag = u'!AuthorDateDeltaMinFilter'

    def __init__(
        self,
        parent: tp.Optional[InteractionFilter] = None,
        comment: tp.Optional[str] = None,
        author_date_delta_min: tp.Optional[str] = None
    ) -> None:
        super().__init__(parent, comment)
        self._author_date_delta_min = author_date_delta_min

    def authorDateDeltaMin(self) -> tp.Optional[str]:
        return self._author_date_delta_min

    def setAuthorDateDeltaMin(self, author_date_delta_min: str) -> None:
        self._author_date_delta_min = author_date_delta_min

    def data(self, column: int) -> tp.Any:
        val = super().data(column)

        if column == 2:
            val = self.authorDateDeltaMin()

        return val

    def setData(self, column: int, value: tp.Any) -> None:
        super().setData(column, value)

        if column == 2:
            self.setAuthorDateDeltaMin(value)

    @staticmethod
    def resource() -> str:
        return ":/breeze/light/chronometer.svg"


class AuthorDateDeltaMaxFilter(BinaryInteractionFilter):
    yaml_tag = u'!AuthorDateDeltaMaxFilter'

    def __init__(
        self,
        parent: tp.Optional[InteractionFilter] = None,
        comment: tp.Optional[str] = None,
        author_date_delta_max: tp.Optional[str] = None
    ) -> None:
        super().__init__(parent, comment)
        self._author_date_delta_max = author_date_delta_max

    def authorDateDeltaMax(self) -> tp.Optional[str]:
        return self._author_date_delta_max

    def setAuthorDateDeltaMax(self, author_date_delta_max: str) -> None:
        self._author_date_delta_max = author_date_delta_max

    def data(self, column: int) -> tp.Any:
        val = super().data(column)

        if column == 2:
            val = self.authorDateDeltaMax()

        return val

    def setData(self, column: int, value: tp.Any) -> None:
        super().setData(column, value)

        if column == 2:
            self.setAuthorDateDeltaMax(value)

    @staticmethod
    def resource() -> str:
        return ":/breeze/light/chronometer.svg"


class CommitDateDeltaMinFilter(BinaryInteractionFilter):
    yaml_tag = u'!CommitDateDeltaMinFilter'

    def __init__(
        self,
        parent: tp.Optional[InteractionFilter] = None,
        comment: tp.Optional[str] = None,
        commit_date_delta_min: tp.Optional[str] = None
    ) -> None:
        super().__init__(parent, comment)
        self._commit_date_delta_min = commit_date_delta_min

    def commitDateDeltaMin(self) -> tp.Optional[str]:
        return self._commit_date_delta_min

    def setCommitDateDeltaMin(self, commit_date_delta_min: str) -> None:
        self._commit_date_delta_min = commit_date_delta_min

    def data(self, column: int) -> tp.Any:
        val = super().data(column)

        if column == 2:
            val = self.commitDateDeltaMin()

        return val

    def setData(self, column: int, value: tp.Any) -> None:
        super().setData(column, value)

        if column == 2:
            self.setCommitDateDeltaMin(value)

    @staticmethod
    def resource() -> str:
        return ":/breeze/light/chronometer.svg"


class CommitDateDeltaMaxFilter(BinaryInteractionFilter):
    yaml_tag = u'!CommitDateDeltaMaxFilter'

    def __init__(
        self,
        parent: tp.Optional[InteractionFilter] = None,
        comment: tp.Optional[str] = None,
        commit_date_delta_max: tp.Optional[str] = None
    ) -> None:
        super().__init__(parent, comment)
        self._commit_date_delta_max = commit_date_delta_max

    def commitDateDeltaMax(self) -> tp.Optional[str]:
        return self._commit_date_delta_max

    def setCommitDateDeltaMax(self, commit_date_delta_max: str) -> None:
        self._commit_date_delta_max = commit_date_delta_max

    def data(self, column: int) -> tp.Any:
        val = super().data(column)

        if column == 2:
            val = self.commitDateDeltaMax()

        return val

    def setData(self, column: int, value: tp.Any) -> None:
        super().setData(column, value)

        if column == 2:
            self.setCommitDateDeltaMax(value)

    @staticmethod
    def resource() -> str:
        return ":/breeze/light/chronometer.svg"


class FilterOperator(InteractionFilter):
    yaml_tag = u'!FilterOperator'

    def __init__(
        self,
        parent: tp.Optional[InteractionFilter] = None,
        comment: tp.Optional[str] = None
    ) -> None:
        super().__init__(parent, comment)


class AndOperator(FilterOperator):
    yaml_tag = u'!AndOperator'

    def __init__(
        self,
        parent: tp.Optional[InteractionFilter] = None,
        comment: tp.Optional[str] = None,
        children: tp.Optional[tp.List[InteractionFilter]] = None
    ) -> None:
        super().__init__(parent, comment)
        self._children: tp.List[InteractionFilter] = []
        if children is not None:
            self._children = children

    def addChild(self, child: InteractionFilter) -> bool:
        self._children.append(child)
        child.setParent(self)
        return True

    def insertChild(self, position: int, child: InteractionFilter) -> bool:
        if position < 0 or position > len(self._children):
            return False

        self._children.insert(position, child)
        child.setParent(self)
        return True

    def moveChild(self, sourceRow: int, destinationRow: int) -> bool:
        num_children = len(self._children)
        if (
            sourceRow < 0 or sourceRow > num_children or destinationRow < 0 or
            destinationRow > num_children
        ):
            return False

        if destinationRow > sourceRow:
            destinationRow -= 1

        node = self._children.pop(sourceRow)
        self._children.insert(destinationRow, node)
        return True

    def removeChild(self, position: int) -> bool:
        if position < 0 or position > len(self._children):
            return False

        child = self._children.pop(position)
        child.setParent(None)
        return True

    def child(self, index: int) -> tp.Optional[InteractionFilter]:
        if index < 0 or index >= len(self._children):
            return None
        return self._children[index]

    def childCount(self) -> int:
        return len(self._children)

    @staticmethod
    def resource() -> str:
        return ":/operators/and-operator.svg"


class OrOperator(FilterOperator):
    yaml_tag = u'!OrOperator'

    def __init__(
        self,
        parent: tp.Optional[InteractionFilter] = None,
        comment: tp.Optional[str] = None,
        children: tp.Optional[tp.List[InteractionFilter]] = None
    ) -> None:
        super().__init__(parent, comment)
        self._children: tp.List[InteractionFilter] = []
        if children is not None:
            self._children = children

    def addChild(self, child: InteractionFilter) -> bool:
        self._children.append(child)
        child.setParent(self)
        return True

    def insertChild(self, position: int, child: InteractionFilter) -> bool:
        if position < 0 or position > len(self._children):
            return False

        self._children.insert(position, child)
        child.setParent(self)
        return True

    def moveChild(self, sourceRow: int, destinationRow: int) -> bool:
        num_children = len(self._children)
        if (
            sourceRow < 0 or sourceRow > num_children or destinationRow < 0 or
            destinationRow > num_children
        ):
            return False

        if destinationRow > sourceRow:
            destinationRow -= 1

        node = self._children.pop(sourceRow)
        self._children.insert(destinationRow, node)
        return True

    def removeChild(self, position: int) -> bool:
        if position < 0 or position > len(self._children):
            return False

        child = self._children.pop(position)
        child.setParent(None)
        return True

    def child(self, index: int) -> tp.Optional[InteractionFilter]:
        if index < 0 or index >= len(self._children):
            return None
        return self._children[index]

    def childCount(self) -> int:
        return len(self._children)

    @staticmethod
    def resource() -> str:
        return ":/operators/or-operator.svg"


class NotOperator(FilterOperator):
    yaml_tag = u'!NotOperator'

    def __init__(
        self,
        parent: tp.Optional[InteractionFilter] = None,
        comment: tp.Optional[str] = None,
        child: tp.Optional[InteractionFilter] = None
    ) -> None:
        super().__init__(parent, comment)
        self._child = child

    def addChild(self, child: InteractionFilter) -> bool:
        if self._child is not None:
            return False

        self._child = child
        child.setParent(self)
        return True

    def insertChild(self, position: int, child: InteractionFilter) -> bool:
        if self._child is not None or position != 0:
            return False

        self._child = child
        child.setParent(self)
        return True

    def removeChild(self, position: int) -> bool:
        if position != 0:
            return False

        if self._child:
            self._child.setParent(None)
        self._child = None
        return True

    def child(self, index: int = 0) -> tp.Optional[InteractionFilter]:
        if index == 0:
            return self._child
        return None

    def childCount(self) -> int:
        if self._child is None:
            return 0
        return 1

    @staticmethod
    def resource() -> str:
        return ":/operators/not-operator.svg"


class SourceOperator(FilterOperator):
    yaml_tag = u'!SourceOperator'

    def __init__(
        self,
        parent: tp.Optional[InteractionFilter] = None,
        comment: tp.Optional[str] = None,
        child: tp.Optional[InteractionFilter] = None
    ) -> None:
        super().__init__(parent, comment)
        self._child = child

    def addChild(self, child: InteractionFilter) -> bool:
        if self._child is not None:
            return False

        self._child = child
        child.setParent(self)
        return True

    def insertChild(self, position: int, child: InteractionFilter) -> bool:
        if self._child is not None or position != 0:
            return False

        self._child = child
        child.setParent(self)
        return True

    def removeChild(self, position: int) -> bool:
        if position != 0:
            return False

        if self._child:
            self._child.setParent(None)
        self._child = None
        return True

    def child(self, index: int = 0) -> tp.Optional[InteractionFilter]:
        if index == 0:
            return self._child
        return None

    def childCount(self) -> int:
        if self._child is None:
            return 0
        return 1

    @staticmethod
    def resource() -> str:
        return ":/operators/source-operator.svg"


class TargetOperator(FilterOperator):
    yaml_tag = u'!TargetOperator'

    def __init__(
        self,
        parent: tp.Optional[InteractionFilter] = None,
        comment: tp.Optional[str] = None,
        child: tp.Optional[InteractionFilter] = None
    ) -> None:
        super().__init__(parent, comment)
        self._child = child

    def addChild(self, child: InteractionFilter) -> bool:
        if self._child is not None:
            return False

        self._child = child
        child.setParent(self)
        return True

    def insertChild(self, position: int, child: InteractionFilter) -> bool:
        if self._child is not None or position != 0:
            return False

        self._child = child
        child.setParent(self)
        return True

    def removeChild(self, position: int) -> bool:
        if position != 0:
            return False

        if self._child:
            self._child.setParent(None)
        self._child = None
        return True

    def child(self, index: int = 0) -> tp.Optional[InteractionFilter]:
        if index == 0:
            return self._child
        return None

    def childCount(self) -> int:
        if self._child is None:
            return 0
        return 1

    @staticmethod
    def resource() -> str:
        return ":/operators/target-operator.svg"
