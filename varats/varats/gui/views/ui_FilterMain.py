# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'FilterMain.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

from varats.gui import icons_rc
from varats.gui.deselectable_tree_view import DeselectableQTreeView


class Ui_FilterEditor(object):

    def setupUi(self, FilterEditor):
        FilterEditor.setObjectName("FilterEditor")
        FilterEditor.resize(501, 499)
        self.uiCentralWidget = QtWidgets.QWidget(FilterEditor)
        self.uiCentralWidget.setObjectName("uiCentralWidget")
        self.layoutMain = QtWidgets.QVBoxLayout(self.uiCentralWidget)
        self.layoutMain.setObjectName("layoutMain")
        self.frame = QtWidgets.QFrame(self.uiCentralWidget)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.frame.sizePolicy().hasHeightForWidth()
        )
        self.frame.setSizePolicy(sizePolicy)
        self.frame.setBaseSize(QtCore.QSize(0, 0))
        self.frame.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.frame)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setSpacing(6)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.uiTree = DeselectableQTreeView(self.frame)
        self.uiTree.setObjectName("uiTree")
        self.horizontalLayout.addWidget(self.uiTree)
        self.frame_2 = QtWidgets.QFrame(self.frame)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.frame_2.sizePolicy().hasHeightForWidth()
        )
        self.frame_2.setSizePolicy(sizePolicy)
        self.frame_2.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.frame_2.setFrameShadow(QtWidgets.QFrame.Plain)
        self.frame_2.setLineWidth(1)
        self.frame_2.setObjectName("frame_2")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.frame_2)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.uiHelp = QtWidgets.QPushButton(self.frame_2)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(50)
        sizePolicy.setVerticalStretch(30)
        sizePolicy.setHeightForWidth(
            self.uiHelp.sizePolicy().hasHeightForWidth()
        )
        self.uiHelp.setSizePolicy(sizePolicy)
        self.uiHelp.setMaximumSize(QtCore.QSize(50, 30))
        self.uiHelp.setText("")
        icon = QtGui.QIcon()
        icon.addPixmap(
            QtGui.QPixmap(":/breeze/light/help-about.svg"), QtGui.QIcon.Normal,
            QtGui.QIcon.Off
        )
        self.uiHelp.setIcon(icon)
        self.uiHelp.setObjectName("uiHelp")
        self.verticalLayout_3.addWidget(self.uiHelp)
        spacerItem = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding
        )
        self.verticalLayout_3.addItem(spacerItem)
        self.uiAddButton = QtWidgets.QPushButton(self.frame_2)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(50)
        sizePolicy.setVerticalStretch(30)
        sizePolicy.setHeightForWidth(
            self.uiAddButton.sizePolicy().hasHeightForWidth()
        )
        self.uiAddButton.setSizePolicy(sizePolicy)
        self.uiAddButton.setMaximumSize(QtCore.QSize(50, 30))
        self.uiAddButton.setText("")
        icon1 = QtGui.QIcon()
        icon1.addPixmap(
            QtGui.QPixmap(":/breeze/light/list-add.svg"), QtGui.QIcon.Normal,
            QtGui.QIcon.Off
        )
        self.uiAddButton.setIcon(icon1)
        self.uiAddButton.setObjectName("uiAddButton")
        self.verticalLayout_3.addWidget(self.uiAddButton)
        self.uiRemoveButton = QtWidgets.QPushButton(self.frame_2)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(30)
        sizePolicy.setVerticalStretch(30)
        sizePolicy.setHeightForWidth(
            self.uiRemoveButton.sizePolicy().hasHeightForWidth()
        )
        self.uiRemoveButton.setSizePolicy(sizePolicy)
        self.uiRemoveButton.setMinimumSize(QtCore.QSize(0, 0))
        self.uiRemoveButton.setMaximumSize(QtCore.QSize(50, 30))
        self.uiRemoveButton.setText("")
        icon2 = QtGui.QIcon()
        icon2.addPixmap(
            QtGui.QPixmap(":/breeze/light/edit-delete.svg"), QtGui.QIcon.Normal,
            QtGui.QIcon.Off
        )
        self.uiRemoveButton.setIcon(icon2)
        self.uiRemoveButton.setObjectName("uiRemoveButton")
        self.verticalLayout_3.addWidget(self.uiRemoveButton)
        self.uiUpButton = QtWidgets.QPushButton(self.frame_2)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(30)
        sizePolicy.setVerticalStretch(30)
        sizePolicy.setHeightForWidth(
            self.uiUpButton.sizePolicy().hasHeightForWidth()
        )
        self.uiUpButton.setSizePolicy(sizePolicy)
        self.uiUpButton.setMaximumSize(QtCore.QSize(50, 30))
        self.uiUpButton.setText("")
        icon3 = QtGui.QIcon()
        icon3.addPixmap(
            QtGui.QPixmap(":/breeze/light/go-up.svg"), QtGui.QIcon.Normal,
            QtGui.QIcon.Off
        )
        self.uiUpButton.setIcon(icon3)
        self.uiUpButton.setObjectName("uiUpButton")
        self.verticalLayout_3.addWidget(self.uiUpButton)
        self.uiDownButton = QtWidgets.QPushButton(self.frame_2)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(30)
        sizePolicy.setVerticalStretch(30)
        sizePolicy.setHeightForWidth(
            self.uiDownButton.sizePolicy().hasHeightForWidth()
        )
        self.uiDownButton.setSizePolicy(sizePolicy)
        self.uiDownButton.setMaximumSize(QtCore.QSize(50, 30))
        self.uiDownButton.setText("")
        icon4 = QtGui.QIcon()
        icon4.addPixmap(
            QtGui.QPixmap(":/breeze/light/go-down.svg"), QtGui.QIcon.Normal,
            QtGui.QIcon.Off
        )
        self.uiDownButton.setIcon(icon4)
        self.uiDownButton.setObjectName("uiDownButton")
        self.verticalLayout_3.addWidget(self.uiDownButton)
        spacerItem1 = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding
        )
        self.verticalLayout_3.addItem(spacerItem1)
        self.horizontalLayout.addWidget(self.frame_2)
        self.layoutMain.addWidget(self.frame)
        FilterEditor.setCentralWidget(self.uiCentralWidget)
        self.uiMenubar = QtWidgets.QMenuBar(FilterEditor)
        self.uiMenubar.setGeometry(QtCore.QRect(0, 0, 501, 29))
        self.uiMenubar.setObjectName("uiMenubar")
        self.menu_File = QtWidgets.QMenu(self.uiMenubar)
        self.menu_File.setObjectName("menu_File")
        self.menuHelp = QtWidgets.QMenu(self.uiMenubar)
        self.menuHelp.setObjectName("menuHelp")
        FilterEditor.setMenuBar(self.uiMenubar)
        self.uiActionOpen = QtWidgets.QAction(FilterEditor)
        icon5 = QtGui.QIcon()
        icon5.addPixmap(
            QtGui.QPixmap(":/breeze/light/document-open.svg"),
            QtGui.QIcon.Normal, QtGui.QIcon.Off
        )
        self.uiActionOpen.setIcon(icon5)
        self.uiActionOpen.setObjectName("uiActionOpen")
        self.uiActionSave = QtWidgets.QAction(FilterEditor)
        icon6 = QtGui.QIcon()
        icon6.addPixmap(
            QtGui.QPixmap(":/breeze/light/document-save.svg"),
            QtGui.QIcon.Normal, QtGui.QIcon.Off
        )
        self.uiActionSave.setIcon(icon6)
        self.uiActionSave.setObjectName("uiActionSave")
        self.uiActionSaveAs = QtWidgets.QAction(FilterEditor)
        icon7 = QtGui.QIcon()
        icon7.addPixmap(
            QtGui.QPixmap(":/breeze/light/document-save-as.svg"),
            QtGui.QIcon.Normal, QtGui.QIcon.Off
        )
        self.uiActionSaveAs.setIcon(icon7)
        self.uiActionSaveAs.setObjectName("uiActionSaveAs")
        self.uiActionExit = QtWidgets.QAction(FilterEditor)
        icon8 = QtGui.QIcon()
        icon8.addPixmap(
            QtGui.QPixmap(":/breeze/light/application-exit.svg"),
            QtGui.QIcon.Normal, QtGui.QIcon.Off
        )
        self.uiActionExit.setIcon(icon8)
        self.uiActionExit.setObjectName("uiActionExit")
        self.uiActionHelp = QtWidgets.QAction(FilterEditor)
        self.uiActionHelp.setIcon(icon)
        self.uiActionHelp.setObjectName("uiActionHelp")
        self.menu_File.addAction(self.uiActionOpen)
        self.menu_File.addSeparator()
        self.menu_File.addAction(self.uiActionSave)
        self.menu_File.addAction(self.uiActionSaveAs)
        self.menu_File.addSeparator()
        self.menu_File.addAction(self.uiActionExit)
        self.menuHelp.addAction(self.uiActionHelp)
        self.uiMenubar.addAction(self.menu_File.menuAction())
        self.uiMenubar.addAction(self.menuHelp.menuAction())

        self.retranslateUi(FilterEditor)
        QtCore.QMetaObject.connectSlotsByName(FilterEditor)

    def retranslateUi(self, FilterEditor):
        _translate = QtCore.QCoreApplication.translate
        FilterEditor.setWindowTitle(_translate("FilterEditor", "MainWindow"))
        self.uiHelp.setToolTip(_translate("FilterEditor", "Help"))
        self.uiAddButton.setToolTip(
            _translate("FilterEditor", "Add a new node")
        )
        self.uiRemoveButton.setToolTip(
            _translate("FilterEditor", "Delete node")
        )
        self.uiUpButton.setToolTip(_translate("FilterEditor", "Move node up"))
        self.uiDownButton.setToolTip(
            _translate("FilterEditor", "Move node down")
        )
        self.menu_File.setTitle(_translate("FilterEditor", "&File"))
        self.menuHelp.setTitle(_translate("FilterEditor", "&Help"))
        self.uiActionOpen.setText(_translate("FilterEditor", "&Open"))
        self.uiActionSave.setText(_translate("FilterEditor", "&Save"))
        self.uiActionSaveAs.setText(_translate("FilterEditor", "Save &As..."))
        self.uiActionExit.setText(_translate("FilterEditor", "&Quit"))
        self.uiActionHelp.setText(_translate("FilterEditor", "&Help"))
        self.uiActionHelp.setToolTip(_translate("FilterEditor", "Help"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    FilterEditor = QtWidgets.QMainWindow()
    ui = Ui_FilterEditor()
    ui.setupUi(FilterEditor)
    FilterEditor.show()
    sys.exit(app.exec_())
