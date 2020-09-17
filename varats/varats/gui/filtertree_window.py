import os
from threading import Lock

import yaml
from PyQt5.QtCore import QModelIndex
from PyQt5.QtGui import QCloseEvent, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QDataWidgetMapper,
    QFileDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
    QWidget,
)

from varats.base.version_header import VersionHeader
from varats.data.filtertree_data import (
    AndOperator,
    SourceOperator,
    TargetOperator,
    UnaryInteractionFilter,
)
from varats.gui import icons_rc  # noqa # pylint: disable=unused-import
from varats.gui.filtertree_model import FilterTreeModel
from varats.gui.views.ui_AuthorDateDeltaMaxFilter import (
    Ui_AuthorDateDeltaMaxFilter,
)
from varats.gui.views.ui_AuthorDateDeltaMinFilter import (
    Ui_AuthorDateDeltaMinFilter,
)
from varats.gui.views.ui_AuthorDateMaxFilter import Ui_AuthorDateMaxFilter
from varats.gui.views.ui_AuthorDateMinFilter import Ui_AuthorDateMinFilter
from varats.gui.views.ui_AuthorFilterProperties import Ui_AuthorFilterProperties
from varats.gui.views.ui_CommitDateDeltaMaxFilter import (
    Ui_CommitDateDeltaMaxFilter,
)
from varats.gui.views.ui_CommitDateDeltaMinFilter import (
    Ui_CommitDateDeltaMinFilter,
)
from varats.gui.views.ui_CommitDateMaxFilter import Ui_CommitDateMaxFilter
from varats.gui.views.ui_CommitDateMinFilter import Ui_CommitDateMinFilter
from varats.gui.views.ui_CommitterFilterProperties import (
    Ui_CommitterFilterProperties,
)
from varats.gui.views.ui_FilterMain import Ui_FilterEditor
from varats.gui.views.ui_FilterNodeProperties import Ui_FilterNodeProperties
from varats.gui.views.ui_FilterProperties import Ui_FilterProperties
from varats.gui.views.ui_FilterUnaryWarning import Ui_FilterUnaryWarning


def _showTimeDurationHelp() -> None:
    help_text = "The time duration must be specified as an ISO 8601 time duration string.\n\n" \
        "Format: P[n]Y[n]M[n]DT[n]H[n]M[n]S\n\n" \
        "- [n] specifies the value of the date/time element that follows the value.\n" \
        "- P always has to be the first character.\n" \
        "- T separates the date component from the time component.\n\n" \
        "Allowed date/time elements:\n" \
        "  - Y: year designator\n" \
        "  - M: month designator\n" \
        "  - D: day designator\n" \
        "  - H: hour designator\n" \
        "  - M: minute designator\n" \
        "  - S: second designator\n\n" \
        "Example:\n" \
        "\"P3DT12H30M\" represents a duration of \"three days, twelve hours and thirty minutes\".\n"

    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setInformativeText(help_text)
    msg.setWindowTitle("Help")
    msg.exec_()


class PropertiesEditor(QWidget, Ui_FilterProperties):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self._model = None

        self._node_editor = NodeEditor(self)
        self._filter_unary_warning = FilterUnaryWarning(self)
        self._author_filter_editor = AuthorFilterEditor(self)
        self._committer_filter_editor = CommitterFilterEditor(self)
        self._author_date_min_filter_editor = AuthorDateMinFilterEditor(self)
        self._author_date_max_filter_editor = AuthorDateMaxFilterEditor(self)
        self._commit_date_min_filter_editor = CommitDateMinFilterEditor(self)
        self._commit_date_max_filter_editor = CommitDateMaxFilterEditor(self)
        self._author_date_delta_min_filter_editor = AuthorDateDeltaMinFilterEditor(
            self
        )
        self._author_date_delta_max_filter_editor = AuthorDateDeltaMaxFilterEditor(
            self
        )
        self._commit_date_delta_min_filter_editor = CommitDateDeltaMinFilterEditor(
            self
        )
        self._commit_date_delta_max_filter_editor = CommitDateDeltaMaxFilterEditor(
            self
        )

        self.layoutNode.addWidget(self._node_editor)
        self.layoutNodeWarning.addWidget(self._filter_unary_warning)
        self.layoutNodeSpec.addWidget(self._author_filter_editor)
        self.layoutNodeSpec.addWidget(self._committer_filter_editor)
        self.layoutNodeSpec.addWidget(self._author_date_min_filter_editor)
        self.layoutNodeSpec.addWidget(self._author_date_max_filter_editor)
        self.layoutNodeSpec.addWidget(self._commit_date_min_filter_editor)
        self.layoutNodeSpec.addWidget(self._commit_date_max_filter_editor)
        self.layoutNodeSpec.addWidget(self._author_date_delta_min_filter_editor)
        self.layoutNodeSpec.addWidget(self._author_date_delta_max_filter_editor)
        self.layoutNodeSpec.addWidget(self._commit_date_delta_min_filter_editor)
        self.layoutNodeSpec.addWidget(self._commit_date_delta_max_filter_editor)

        self._setEditorsInvisible()

    def setSelection(self, current: QModelIndex, old: QModelIndex) -> None:
        node = current.internalPointer()

        self._setEditorsInvisible()

        if node is not None:
            if node.name() == 'AndOperator':
                pass
            if node.name() == 'OrOperator':
                pass
            if node.name() == 'NotOperator':
                pass
            if node.name() == 'SourceOperator':
                pass
            if node.name() == 'TargetOperator':
                pass
            if node.name() == 'AuthorFilter':
                self._author_filter_editor.setVisible(True)
            if node.name() == 'CommitterFilter':
                self._committer_filter_editor.setVisible(True)
            if node.name() == 'AuthorDateMinFilter':
                self._author_date_min_filter_editor.setVisible(True)
            if node.name() == 'AuthorDateMaxFilter':
                self._author_date_max_filter_editor.setVisible(True)
            if node.name() == 'CommitDateMinFilter':
                self._commit_date_min_filter_editor.setVisible(True)
            if node.name() == 'CommitDateMaxFilter':
                self._commit_date_max_filter_editor.setVisible(True)
            if node.name() == 'AuthorDateDeltaMinFilter':
                self._author_date_delta_min_filter_editor.setVisible(True)
            if node.name() == 'AuthorDateDeltaMaxFilter':
                self._author_date_delta_max_filter_editor.setVisible(True)
            if node.name() == 'CommitDateDeltaMinFilter':
                self._commit_date_delta_min_filter_editor.setVisible(True)
            if node.name() == 'CommitDateDeltaMaxFilter':
                self._commit_date_delta_max_filter_editor.setVisible(True)

        self._node_editor.setSelection(current)

        self._author_filter_editor.setSelection(current)
        self._filter_unary_warning.setSelection(current)
        self._committer_filter_editor.setSelection(current)
        self._author_date_min_filter_editor.setSelection(current)
        self._author_date_max_filter_editor.setSelection(current)
        self._commit_date_min_filter_editor.setSelection(current)
        self._commit_date_max_filter_editor.setSelection(current)
        self._author_date_delta_min_filter_editor.setSelection(current)
        self._author_date_delta_max_filter_editor.setSelection(current)
        self._commit_date_delta_min_filter_editor.setSelection(current)
        self._commit_date_delta_max_filter_editor.setSelection(current)

    def setModel(self, model) -> None:
        self._model = model

        self._node_editor.setModel(model)
        self._filter_unary_warning.setModel(model)
        self._author_filter_editor.setModel(model)
        self._committer_filter_editor.setModel(model)
        self._author_date_min_filter_editor.setModel(model)
        self._author_date_max_filter_editor.setModel(model)
        self._commit_date_min_filter_editor.setModel(model)
        self._commit_date_max_filter_editor.setModel(model)
        self._author_date_delta_min_filter_editor.setModel(model)
        self._author_date_delta_max_filter_editor.setModel(model)
        self._commit_date_delta_min_filter_editor.setModel(model)
        self._commit_date_delta_max_filter_editor.setModel(model)

    def _setEditorsInvisible(self):
        self._author_filter_editor.setVisible(False)
        self._committer_filter_editor.setVisible(False)
        self._author_date_min_filter_editor.setVisible(False)
        self._author_date_max_filter_editor.setVisible(False)
        self._commit_date_min_filter_editor.setVisible(False)
        self._commit_date_max_filter_editor.setVisible(False)
        self._author_date_delta_min_filter_editor.setVisible(False)
        self._author_date_delta_max_filter_editor.setVisible(False)
        self._commit_date_delta_min_filter_editor.setVisible(False)
        self._commit_date_delta_max_filter_editor.setVisible(False)


class NodeEditor(QWidget, Ui_FilterNodeProperties):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self._data_mapper = QDataWidgetMapper()

    def setModel(self, model):
        self._model = model
        self._data_mapper.setModel(model)
        self._data_mapper.addMapping(self.uiName, 0)
        self._data_mapper.addMapping(self.uiComment, 1)

    def setSelection(self, current: QModelIndex) -> None:
        parent = current.parent()
        self._data_mapper.setRootIndex(parent)
        self._data_mapper.setCurrentModelIndex(current)


class FilterUnaryWarning(QWidget, Ui_FilterUnaryWarning):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

    def setModel(self, model):
        self._model = model
        self.uiWarningLabel.hide()

    def setSelection(self, current: QModelIndex) -> None:
        node = self._model.getNode(current)
        if issubclass(type(node), UnaryInteractionFilter):
            if node.hasFilterTypeAsParent(
                SourceOperator
            ) or node.hasFilterTypeAsParent(TargetOperator):
                self.uiWarningLabel.hide()
            else:
                self.uiWarningLabel.show()
        else:
            self.uiWarningLabel.hide()


class AuthorFilterEditor(QWidget, Ui_AuthorFilterProperties):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self._data_mapper = QDataWidgetMapper()

    def setModel(self, model):
        self._model = model
        self._data_mapper.setModel(model)
        self._data_mapper.addMapping(self.uiAuthorName, 2)
        self._data_mapper.addMapping(self.uiAuthorEmail, 3)

    def setSelection(self, current: QModelIndex) -> None:
        parent = current.parent()
        self._data_mapper.setRootIndex(parent)
        self._data_mapper.setCurrentModelIndex(current)


class CommitterFilterEditor(QWidget, Ui_CommitterFilterProperties):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self._data_mapper = QDataWidgetMapper()

    def setModel(self, model):
        self._model = model
        self._data_mapper.setModel(model)
        self._data_mapper.addMapping(self.uiCommitterName, 2)
        self._data_mapper.addMapping(self.uiCommitterEmail, 3)

    def setSelection(self, current: QModelIndex) -> None:
        parent = current.parent()
        self._data_mapper.setRootIndex(parent)
        self._data_mapper.setCurrentModelIndex(current)


class AuthorDateMinFilterEditor(QWidget, Ui_AuthorDateMinFilter):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self._data_mapper = QDataWidgetMapper()

    def setModel(self, model):
        self._model = model
        self._data_mapper.setModel(model)
        self._data_mapper.addMapping(self.uiAuthorDateMin, 2)

    def setSelection(self, current: QModelIndex) -> None:
        parent = current.parent()
        self._data_mapper.setRootIndex(parent)
        self._data_mapper.setCurrentModelIndex(current)


class AuthorDateMaxFilterEditor(QWidget, Ui_AuthorDateMaxFilter):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self._data_mapper = QDataWidgetMapper()

    def setModel(self, model):
        self._model = model
        self._data_mapper.setModel(model)
        self._data_mapper.addMapping(self.uiAuthorDateMax, 2)

    def setSelection(self, current: QModelIndex) -> None:
        parent = current.parent()
        self._data_mapper.setRootIndex(parent)
        self._data_mapper.setCurrentModelIndex(current)


class CommitDateMinFilterEditor(QWidget, Ui_CommitDateMinFilter):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self._data_mapper = QDataWidgetMapper()

    def setModel(self, model):
        self._model = model
        self._data_mapper.setModel(model)
        self._data_mapper.addMapping(self.uiCommitDateMin, 2)

    def setSelection(self, current: QModelIndex) -> None:
        parent = current.parent()
        self._data_mapper.setRootIndex(parent)
        self._data_mapper.setCurrentModelIndex(current)


class CommitDateMaxFilterEditor(QWidget, Ui_CommitDateMaxFilter):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self._data_mapper = QDataWidgetMapper()

    def setModel(self, model):
        self._model = model
        self._data_mapper.setModel(model)
        self._data_mapper.addMapping(self.uiCommitDateMax, 2)

    def setSelection(self, current: QModelIndex) -> None:
        parent = current.parent()
        self._data_mapper.setRootIndex(parent)
        self._data_mapper.setCurrentModelIndex(current)


class AuthorDateDeltaMinFilterEditor(QWidget, Ui_AuthorDateDeltaMinFilter):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self._data_mapper = QDataWidgetMapper()
        self.uiHelp.clicked.connect(_showTimeDurationHelp)

    def setModel(self, model):
        self._model = model
        self._data_mapper.setModel(model)
        self._data_mapper.addMapping(self.uiAuthorDateDeltaMin, 2)

    def setSelection(self, current: QModelIndex) -> None:
        parent = current.parent()
        self._data_mapper.setRootIndex(parent)
        self._data_mapper.setCurrentModelIndex(current)


class AuthorDateDeltaMaxFilterEditor(QWidget, Ui_AuthorDateDeltaMaxFilter):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self._data_mapper = QDataWidgetMapper()
        self.uiHelp.clicked.connect(_showTimeDurationHelp)

    def setModel(self, model):
        self._model = model
        self._data_mapper.setModel(model)
        self._data_mapper.addMapping(self.uiAuthorDateDeltaMax, 2)

    def setSelection(self, current: QModelIndex) -> None:
        parent = current.parent()
        self._data_mapper.setRootIndex(parent)
        self._data_mapper.setCurrentModelIndex(current)


class CommitDateDeltaMinFilterEditor(QWidget, Ui_CommitDateDeltaMinFilter):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self._data_mapper = QDataWidgetMapper()
        self.uiHelp.clicked.connect(_showTimeDurationHelp)

    def setModel(self, model):
        self._model = model
        self._data_mapper.setModel(model)
        self._data_mapper.addMapping(self.uiCommitDateDeltaMin, 2)

    def setSelection(self, current: QModelIndex) -> None:
        parent = current.parent()
        self._data_mapper.setRootIndex(parent)
        self._data_mapper.setCurrentModelIndex(current)


class CommitDateDeltaMaxFilterEditor(QWidget, Ui_CommitDateDeltaMaxFilter):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self._data_mapper = QDataWidgetMapper()
        self.uiHelp.clicked.connect(_showTimeDurationHelp)

    def setModel(self, model):
        self._model = model
        self._data_mapper.setModel(model)
        self._data_mapper.addMapping(self.uiCommitDateDeltaMax, 2)

    def setSelection(self, current: QModelIndex) -> None:
        parent = current.parent()
        self._data_mapper.setRootIndex(parent)
        self._data_mapper.setCurrentModelIndex(current)


class FilterWindow(QMainWindow, Ui_FilterEditor):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self._filename = ""
        self._file_basename = ""
        self._lock = Lock()

        self.updateWindowTitle()

        root_node = AndOperator()
        self._model = FilterTreeModel(root_node)
        self.uiTree.setModel(self._model)

        menu = QMenu()
        menu.addAction(
            QIcon(QPixmap(":/operators/and-operator.svg")), 'And Operator',
            self.addAndNode
        )
        menu.addAction(
            QIcon(QPixmap(":/operators/or-operator.svg")), 'Or Operator',
            self.addOrNode
        )
        menu.addAction(
            QIcon(QPixmap(":/operators/not-operator.svg")), 'Not Operator',
            self.addNotNode
        )
        menu.addSeparator()
        menu.addAction(
            QIcon(QPixmap(":/operators/source-operator.svg")),
            'Source Operator', self.addSourceNode
        )
        menu.addAction(
            QIcon(QPixmap(":/operators/target-operator.svg")),
            'Target Operator', self.addTargetNode
        )
        menu.addSeparator()
        menu.addAction(
            QIcon(QPixmap(":/breeze/light/im-user.svg")), 'Committer Filter',
            self.addCommitterFilterNode
        )
        menu.addAction(
            QIcon(QPixmap(":/breeze/light/im-user.svg")), 'Author Filter',
            self.addAuthorFilterNode
        )
        menu.addSeparator()
        menu.addAction(
            QIcon(QPixmap(":/breeze/light/appointment-new.svg")),
            'AuthorDate Min Filter', self.addAuthorDateMinFilterNode
        )
        menu.addAction(
            QIcon(QPixmap(":/breeze/light/appointment-new.svg")),
            'AuthorDate Max Filter', self.addAuthorDateMaxFilterNode
        )
        menu.addAction(
            QIcon(QPixmap(":/breeze/light/appointment-new.svg")),
            'CommitDate Min Filter', self.addCommitDateMinFilterNode
        )
        menu.addAction(
            QIcon(QPixmap(":/breeze/light/appointment-new.svg")),
            'CommitDate Max Filter', self.addCommitDateMaxFilterNode
        )
        menu.addSeparator()
        menu.addAction(
            QIcon(QPixmap(":/breeze/light/chronometer.svg")),
            'AuthorDateDelta Min Filter', self.addAuthorDateDeltaMinFilterNode
        )
        menu.addAction(
            QIcon(QPixmap(":/breeze/light/chronometer.svg")),
            'AuthorDateDelta Max Filter', self.addAuthorDateDeltaMaxFilterNode
        )
        menu.addAction(
            QIcon(QPixmap(":/breeze/light/chronometer.svg")),
            'CommitDateDelta Min Filter', self.addCommitDateDeltaMinFilterNode
        )
        menu.addAction(
            QIcon(QPixmap(":/breeze/light/chronometer.svg")),
            'CommitDateDelta Max Filter', self.addCommitDateDeltaMaxFilterNode
        )

        self.uiAddButton.setMenu(menu)

        self.uiRemoveButton.clicked.connect(self.removeNode)

        self.uiUpButton.clicked.connect(self.moveRowUp)
        self.uiDownButton.clicked.connect(self.moveRowDown)

        self.uiActionOpen.setShortcut("Ctrl+O")
        self.uiActionOpen.triggered.connect(self.openFile)

        self.uiActionSave.setShortcut("Ctrl+S")
        self.uiActionSave.triggered.connect(self.saveFile)

        self.uiActionSaveAs.setShortcut("Ctrl+Shift+S")
        self.uiActionSaveAs.triggered.connect(self.saveFileAs)

        self.uiActionExit.setShortcut("Ctrl+Q")
        self.uiActionExit.triggered.connect(self.close)

        self.uiActionHelp.triggered.connect(self.showHelp)
        self.uiHelp.clicked.connect(self.showHelp)

        self._prop_editor = PropertiesEditor(self)
        self.layoutMain.addWidget(self._prop_editor)

        self._prop_editor.setModel(self._model)

        self.uiTree.selectionModel().currentChanged.connect(
            self._prop_editor.setSelection
        )
        self.uiTree.selectionModel().currentChanged.connect(
            self._model.setSelection
        )

        self.uiTree.setColumnWidth(0, 250)

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.isWindowModified():
            reply = QMessageBox.question(
                self, "Warning", "Discard unsaved changes?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                event.accept()
            else:
                event.ignore()

    def updateWindowTitle(self) -> None:
        self.setWindowTitle(
            "[*]{} - InteractionFilter Editor".
            format(self._file_basename if self._file_basename else "Untitled")
        )

    def addAndNode(self):
        with self._lock:
            modified = self._model.addAndNode()
            self.uiTree.selectionModel().clear()
            if modified:
                self.setWindowModified(True)

    def addOrNode(self):
        with self._lock:
            modified = self._model.addOrNode()
            self.uiTree.selectionModel().clear()
            if modified:
                self.setWindowModified(True)

    def addNotNode(self):
        with self._lock:
            modified = self._model.addNotNode()
            self.uiTree.selectionModel().clear()
            if modified:
                self.setWindowModified(True)

    def addSourceNode(self):
        with self._lock:
            modified = self._model.addSourceNode()
            self.uiTree.selectionModel().clear()
            if modified:
                self.setWindowModified(True)

    def addTargetNode(self):
        with self._lock:
            modified = self._model.addTargetNode()
            self.uiTree.selectionModel().clear()
            if modified:
                self.setWindowModified(True)

    def addAuthorFilterNode(self):
        with self._lock:
            modified = self._model.addAuthorFilterNode()
            self.uiTree.selectionModel().clear()
            if modified:
                self.setWindowModified(True)

    def addCommitterFilterNode(self):
        with self._lock:
            modified = self._model.addCommitterFilterNode()
            self.uiTree.selectionModel().clear()
            if modified:
                self.setWindowModified(True)

    def addAuthorDateMinFilterNode(self):
        with self._lock:
            modified = self._model.addAuthorDateMinFilterNode()
            self.uiTree.selectionModel().clear()
            if modified:
                self.setWindowModified(True)

    def addAuthorDateMaxFilterNode(self):
        with self._lock:
            modified = self._model.addAuthorDateMaxFilterNode()
            self.uiTree.selectionModel().clear()
            if modified:
                self.setWindowModified(True)

    def addCommitDateMinFilterNode(self):
        with self._lock:
            modified = self._model.addCommitDateMinFilterNode()
            self.uiTree.selectionModel().clear()
            if modified:
                self.setWindowModified(True)

    def addCommitDateMaxFilterNode(self):
        with self._lock:
            modified = self._model.addCommitDateMaxFilterNode()
            self.uiTree.selectionModel().clear()
            if modified:
                self.setWindowModified(True)

    def addAuthorDateDeltaMinFilterNode(self):
        with self._lock:
            modified = self._model.addAuthorDateDeltaMinFilterNode()
            self.uiTree.selectionModel().clear()
            if modified:
                self.setWindowModified(True)

    def addAuthorDateDeltaMaxFilterNode(self):
        with self._lock:
            modified = self._model.addAuthorDateDeltaMaxFilterNode()
            self.uiTree.selectionModel().clear()
            if modified:
                self.setWindowModified(True)

    def addCommitDateDeltaMinFilterNode(self):
        with self._lock:
            modified = self._model.addCommitDateDeltaMinFilterNode()
            self.uiTree.selectionModel().clear()
            if modified:
                self.setWindowModified(True)

    def addCommitDateDeltaMaxFilterNode(self):
        with self._lock:
            modified = self._model.addCommitDateDeltaMaxFilterNode()
            self.uiTree.selectionModel().clear()
            if modified:
                self.setWindowModified(True)

    def moveRowUp(self):
        with self._lock:
            modified = self._model.moveRowUp()
            if modified:
                self.setWindowModified(True)

    def moveRowDown(self):
        with self._lock:
            modified = self._model.moveRowDown()
            if modified:
                self.setWindowModified(True)

    def removeNode(self):
        with self._lock:
            modified = self._model.removeNode()
            self.uiTree.selectionModel().clear()
            if modified:
                self.setWindowModified(True)

    def openFile(self) -> None:
        if self.isWindowModified():
            reply = QMessageBox.question(
                self, "Warning", "Discard unsaved changes?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        filename = QFileDialog.getOpenFileName(self)
        if not filename[0]:
            return

        # TODO (julianbreiteneicher): Warn user (documentation?) that we (have to) use the unsafe loader?
        try:
            with open(filename[0], 'r') as yaml_file:
                documents = yaml_file.read().split("---")
                version_header = VersionHeader(yaml.load(documents[0]))
                version_header.raise_if_not_type("InteractionFilter")
                version_header.raise_if_version_is_less_than(1)

                root_node = yaml.load(documents[1], Loader=yaml.Loader)
                root_node.fixParentPointers()
            self._filename = filename[0]
            self._file_basename = os.path.basename(filename[0])
            self._model.reInit(root_node)
            self.setWindowModified(False)
            self.updateWindowTitle()
        except Exception as e:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setInformativeText(str(e))
            msg.setWindowTitle("Error")
            msg.exec_()
            raise e

    def saveFile(self) -> None:
        if self._filename:
            with open(self._filename, 'w') as yaml_file:
                root_node = self._model.getRootNode()
                version_header = root_node.getVersionHeader().get_dict()
                yaml.dump_all([version_header, root_node], yaml_file)
                self.setWindowModified(False)
        else:
            self.saveFileAs()

    def saveFileAs(self) -> None:
        filename = QFileDialog.getSaveFileName(self)
        if not filename[0]:
            return
        try:
            with open(filename[0], 'w') as yaml_file:
                root_node = self._model.getRootNode()
                version_header = root_node.getVersionHeader().get_dict()
                yaml.dump_all([version_header, root_node], yaml_file)
            self._filename = filename[0]
            self._file_basename = os.path.basename(filename[0])
            self.setWindowModified(False)
            self.updateWindowTitle()
        except Exception as e:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setInformativeText(str(e))
            msg.setWindowTitle("Error")
            msg.exec_()

    @staticmethod
    def showHelp(self) -> None:
        help_text = "This editor can be used to create a custom interaction filter.\n\n" \
            "By using the buttons on the right side you can add, delete and move filter elements.\n\n" \
            "The filter is structured as a tree.\n" \
            "If you add multiple root nodes to the structure, they are automatically connected with an AND operator.\n\n" \
            "To add an element as the child of a parent element simply select the parent and click the add button.\n"
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setInformativeText(help_text)
        msg.setWindowTitle("Help")
        msg.exec_()
