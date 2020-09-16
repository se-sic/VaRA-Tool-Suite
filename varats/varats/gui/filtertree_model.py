from PyQt5.QtCore import QAbstractItemModel, QModelIndex, Qt
from PyQt5.QtGui import QIcon, QPixmap

from varats.data.filtertree_data import (
    AndOperator,
    AuthorDateDeltaMaxFilter,
    AuthorDateDeltaMinFilter,
    AuthorDateMaxFilter,
    AuthorDateMinFilter,
    AuthorFilter,
    CommitDateDeltaMaxFilter,
    CommitDateDeltaMinFilter,
    CommitDateMaxFilter,
    CommitDateMinFilter,
    CommitterFilter,
    InteractionFilter,
    NotOperator,
    OrOperator,
    SourceOperator,
    TargetOperator,
)


class FilterTreeModel(QAbstractItemModel):

    def __init__(self, root, parent=None) -> None:
        super().__init__(parent)
        self._root_node = root
        self._selection = QModelIndex()

    def reInit(self, root) -> None:
        self.beginResetModel()
        self._root_node = root
        self._selection = None
        self.endResetModel()
        self.dataChanged.emit(QModelIndex(), QModelIndex())

    def getRootNode(self) -> InteractionFilter:
        return self._root_node

    def rowCount(self, parent):
        if not parent.isValid():
            parent_node = self._root_node
        else:
            parent_node = parent.internalPointer()

        return parent_node.childCount()

    @staticmethod
    def columnCount(parent):
        return 2

    @staticmethod
    def data(index, role):
        if not index.isValid():
            return None

        node = index.internalPointer()

        if role == Qt.DisplayRole or role == Qt.EditRole:
            return node.data(index.column())

        if role == Qt.DecorationRole:
            if index.column() == 0:
                resource_name = node.resource()
                return QIcon(
                    QPixmap(resource_name).scaled(
                        12, 12, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                )

    def setData(self, index, value, role=Qt.EditRole):
        """
        :param index: QModelIndex
        :param value: QVariant
        :param role: int
        """
        if index.isValid():
            node = index.internalPointer()
            if role == Qt.EditRole:
                node.setData(index.column(), value)
                self.dataChanged.emit(index, index)
                return True
        return False

    @staticmethod
    def headerData(section, orientation, role):
        if role == Qt.DisplayRole:
            if section == 0:
                return "Name"
            if section == 1:
                return "Comment"

    @staticmethod
    def flags(index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def parent(self, index):
        """
        Returns the parent of the node with the given QModelIndex.

        :param index: QModelIndex
        :returns: QModelIndex
        """
        node = self.getNode(index)
        parent_node = node.parent()

        if parent_node == self._root_node:
            return QModelIndex()

        return self.createIndex(parent_node.row(), 0, parent_node)

    def index(self, row, column, parent):
        """Returns a QModelIndex that corresponds to the given row, column and
        parent node."""
        parent_node = self.getNode(parent)
        child_item = parent_node.child(row)

        if child_item:
            return self.createIndex(row, column, child_item)
        else:
            return QModelIndex()

    def getNode(self, index):
        """
        Return the node object for a given QModelIndex.

        :param index: QModelIndex
        :returns: Corresponding InteractionFilter object
        """
        if index and index.isValid():
            node = index.internalPointer()
            if node:
                return node

        return self._root_node

    def insertRows(
        self,
        node_type,
        position: int,
        rows: int,
        parent: QModelIndex = QModelIndex()
    ) -> bool:
        """
        :param parent: QModelIndex
        """
        parent_node = self.getNode(parent)
        parent_num_children = parent_node.childCount()

        parent = self.index(parent.row(), 0, parent.parent())

        if (position < 0 or parent_node.childCount() < position or rows < 0):
            return False

        self.beginInsertRows(
            parent, parent_num_children, parent_num_children + rows - 1
        )

        for _ in range(rows):
            child_node = node_type(parent_node)
            success = parent_node.insertChild(position, child_node)

        self.endInsertRows()

        return success

    def moveRows(
        self, sourceParent, sourceRow, count, destinationParent,
        destinationChild
    ) -> bool:
        """
        :param sourceParent: QModelIndex
        :param sourceRow: int
        :param count: int
        :param destinationParent: QModelIndex
        :param destinationChild: int
        """
        source_parent_node = self.getNode(sourceParent)
        dest_parent_node = self.getNode(destinationParent)

        if (
            sourceRow < 0 or source_parent_node.childCount() <= sourceRow or
            destinationChild < 0 or
            destinationChild > dest_parent_node.childCount() or count < 1
        ):
            return False

        self.beginMoveRows(
            sourceParent, sourceRow, sourceRow + count - 1, destinationParent,
            destinationChild
        )

        if sourceParent == destinationParent:
            for i in range(count):
                success = source_parent_node.moveChild(
                    sourceRow + i, destinationChild + i
                )
        else:
            raise AssertionError(
                "Moving nodes to a different parent is currently not implemented."
            )

        self.endMoveRows()

        return success

    def removeRows(
        self, position: int, rows: int, parent=QModelIndex()
    ) -> bool:
        """
        :param parent: QModelIndex
        """
        parent_node = self.getNode(parent)

        if (
            position < 0 or parent_node.childCount() < position + rows or
            rows < 1
        ):
            return False

        self.beginRemoveRows(parent, position, position + rows - 1)

        for _ in range(rows):
            success = parent_node.removeChild(position)

        self.endRemoveRows()

        return success

    def setSelection(self, current, old):
        """
        :param current: QModelIndex
        :param old: QModelIndex
        """
        self._selection = current

    def addAndNode(self) -> bool:
        num_children = self.getNode(self._selection).childCount()
        return self.insertRows(AndOperator, num_children, 1, self._selection)

    def addOrNode(self) -> bool:
        num_children = self.getNode(self._selection).childCount()
        return self.insertRows(OrOperator, num_children, 1, self._selection)

    def addNotNode(self) -> bool:
        num_children = self.getNode(self._selection).childCount()
        return self.insertRows(NotOperator, num_children, 1, self._selection)

    def addSourceNode(self) -> bool:
        num_children = self.getNode(self._selection).childCount()
        return self.insertRows(SourceOperator, num_children, 1, self._selection)

    def addTargetNode(self) -> bool:
        num_children = self.getNode(self._selection).childCount()
        return self.insertRows(TargetOperator, num_children, 1, self._selection)

    def addCommitterFilterNode(self) -> bool:
        num_children = self.getNode(self._selection).childCount()
        return self.insertRows(
            CommitterFilter, num_children, 1, self._selection
        )

    def addAuthorFilterNode(self) -> bool:
        num_children = self.getNode(self._selection).childCount()
        return self.insertRows(AuthorFilter, num_children, 1, self._selection)

    def addAuthorDateMinFilterNode(self) -> bool:
        num_children = self.getNode(self._selection).childCount()
        return self.insertRows(
            AuthorDateMinFilter, num_children, 1, self._selection
        )

    def addAuthorDateMaxFilterNode(self) -> bool:
        num_children = self.getNode(self._selection).childCount()
        return self.insertRows(
            AuthorDateMaxFilter, num_children, 1, self._selection
        )

    def addCommitDateMinFilterNode(self) -> bool:
        num_children = self.getNode(self._selection).childCount()
        return self.insertRows(
            CommitDateMinFilter, num_children, 1, self._selection
        )

    def addCommitDateMaxFilterNode(self) -> bool:
        num_children = self.getNode(self._selection).childCount()
        return self.insertRows(
            CommitDateMaxFilter, num_children, 1, self._selection
        )

    def addAuthorDateDeltaMinFilterNode(self) -> bool:
        num_children = self.getNode(self._selection).childCount()
        return self.insertRows(
            AuthorDateDeltaMinFilter, num_children, 1, self._selection
        )

    def addAuthorDateDeltaMaxFilterNode(self) -> bool:
        num_children = self.getNode(self._selection).childCount()
        return self.insertRows(
            AuthorDateDeltaMaxFilter, num_children, 1, self._selection
        )

    def addCommitDateDeltaMinFilterNode(self) -> bool:
        num_children = self.getNode(self._selection).childCount()
        return self.insertRows(
            CommitDateDeltaMinFilter, num_children, 1, self._selection
        )

    def addCommitDateDeltaMaxFilterNode(self) -> bool:
        num_children = self.getNode(self._selection).childCount()
        return self.insertRows(
            CommitDateDeltaMaxFilter, num_children, 1, self._selection
        )

    def moveRowUp(self) -> bool:
        selected_node = self.getNode(self._selection)
        if selected_node == self._root_node:
            return False
        parent_index = self._selection.parent()
        row = selected_node.row()
        return self.moveRows(parent_index, row, 1, parent_index, row - 1)

    def moveRowDown(self) -> bool:
        if not self._selection.isValid:
            return False
        selected_node = self.getNode(self._selection)
        if selected_node == self._root_node:
            return False
        row = selected_node.row()
        parent_index = self._selection.parent()
        return self.moveRows(parent_index, row, 1, parent_index, row + 2)

    def removeNode(self) -> bool:
        selection = self._selection
        return self.removeRows(selection.row(), 1, selection.parent())
