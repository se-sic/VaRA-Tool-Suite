"""Option module, providing different options to manage user modifications."""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHeaderView,
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
)


class OptionTreeWidget(QTreeWidget):  # type: ignore
    """A Widget to manage different user options."""
    GRP_CR = "CommitReport"
    OPT_CR_MR = "Merge reports"
    OPT_CR_RORDER = "Report Order"
    OPT_CR_CMAP = "Commit map"
    OPT_CR_PT = "Play time"

    OPT_SCF = "Show CF graph"
    OPT_SDF = "Show DF graph"

    def __init__(self, parent) -> None:
        super(OptionTreeWidget, self).__init__(parent)
        self.headerItem().setText(0, "Options")
        self.headerItem().setText(1, "Value")
        self.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.Interactive)
        self.header().setCascadingSectionResizes(False)
        self.header().setDefaultSectionSize(100)
        self.header().setMinimumSectionSize(26)
        self.header().setStretchLastSection(False)

        self.itemDoubleClicked.connect(self._handle_item_double_click)

        self.__scf = QTreeWidgetItem(self)
        self.__scf.setCheckState(1, Qt.Unchecked)
        self.__scf.setText(0, self.OPT_SCF)

        self.__sdf = QTreeWidgetItem(self)
        self.__sdf.setText(0, self.OPT_SDF)
        self.__sdf.setCheckState(1, Qt.Unchecked)

        grp = QTreeWidgetItem(self)
        grp.setText(0, self.GRP_CR)

        self.__mr = QTreeWidgetItem(grp)
        self.__mr.setCheckState(1, Qt.Unchecked)
        self.__mr.setText(0, self.OPT_CR_MR)

        self.__cm = QTreeWidgetItem(grp)
        self.__cm.setText(0, self.OPT_CR_CMAP)

        # Add QBox item so select order function
        drop_item = QTreeWidgetItem(grp)
        self.__combo_box = QComboBox()
        self.__combo_box.addItem("---")
        self.__combo_box.addItem("Linear History")
        self.setItemWidget(drop_item, 1, self.__combo_box)
        drop_item.setText(0, self.OPT_CR_RORDER)

        play_time_item = QTreeWidgetItem(grp)
        play_time_item.setText(0, self.OPT_CR_PT)
        self.__pt_lineedit = QLineEdit()
        valid = QIntValidator()
        valid.bottom = 10
        valid.top = 50000
        self.__pt_lineedit.setValidator(valid)
        self.setItemWidget(play_time_item, 1, self.__pt_lineedit)
        self.__pt_lineedit.insert(str(5000))

    @property
    def merge_report_checkstate(self):
        """Check state of merge report option."""
        return self.__mr.checkState(1)

    @property
    def show_cf_checkstate(self):
        """Check state of show cf plot option."""
        return self.__scf.checkState(1)

    @property
    def show_df_checkstate(self):
        """Check state of show df plot option."""
        return self.__sdf.checkState(1)

    @property
    def report_order(self):
        """Get current combo box selection."""
        return self.__combo_box.currentText()

    @property
    def play_time(self):
        """Get current play time."""
        return int(self.__pt_lineedit.text())

    def connect_cb_cic(self, func):
        """Register a callback for the combo box currentIndexChanged signal."""
        self.__combo_box.currentIndexChanged.connect(func)

    def _handle_item_double_click(self, item, col):
        if item is self.__cm and col == 1:
            path = self._get_file()
            self.__cm.setText(1, path)

    def _get_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load CommitReport file",
            "",
            "All Files (*)",
            options=options
        )
        return file_path
