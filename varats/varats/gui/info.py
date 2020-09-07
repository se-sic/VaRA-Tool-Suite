"""Info module, providing different ways to represent information in the GUI."""

from PyQt5.QtWidgets import QHeaderView, QTreeWidget, QTreeWidgetItem


class InfoTreeWidget(QTreeWidget):
    """Info Widget to show additional informations for commit reports etc."""

    def __init__(self, parent):
        super(InfoTreeWidget, self).__init__(parent)
        self.headerItem().setText(0, "Info")
        self.headerItem().setText(1, "Value")
        self.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.Interactive)
        self.header().setCascadingSectionResizes(False)
        self.header().setDefaultSectionSize(100)
        self.header().setMinimumSectionSize(26)
        self.header().setStretchLastSection(False)

        self.__c_hash = QTreeWidgetItem(self)
        self.__c_hash.setText(0, "Hash")
        self.c_hash = "---"
        self.__h_id = QTreeWidgetItem(self)
        self.__h_id.setText(0, "History ID")
        self.h_id = "---"

    @property
    def c_hash(self):
        """Last commit hash of current CommitReport."""
        self.__c_hash.text(1)

    @c_hash.setter
    def c_hash(self, c_hash):
        self.__c_hash.setText(1, c_hash)

    @property
    def h_id(self):
        """Commit history ID."""
        return self.__h_id.text(1)

    @h_id.setter
    def h_id(self, h_id):
        self.__h_id.setText(1, str(h_id))
