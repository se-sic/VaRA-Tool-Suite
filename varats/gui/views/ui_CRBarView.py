# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'CR-BarView.ui'
#
# Created by: PyQt5 UI code generator 5.10.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(1022, 601)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 3, 0, 1, 1)
        self.gridLayout_2 = QtWidgets.QGridLayout()
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.loadCRButton = QtWidgets.QPushButton(Form)
        self.loadCRButton.setObjectName("loadCRButton")
        self.gridLayout_2.addWidget(self.loadCRButton, 0, 0, 1, 1)
        self.treeWidget = QtWidgets.QTreeWidget(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.treeWidget.sizePolicy().hasHeightForWidth())
        self.treeWidget.setSizePolicy(sizePolicy)
        self.treeWidget.setAutoFillBackground(True)
        self.treeWidget.setObjectName("treeWidget")
        item_0 = QtWidgets.QTreeWidgetItem(self.treeWidget)
        item_0.setCheckState(1, QtCore.Qt.Unchecked)
        item_0 = QtWidgets.QTreeWidgetItem(self.treeWidget)
        item_0.setCheckState(1, QtCore.Qt.Unchecked)
        item_0 = QtWidgets.QTreeWidgetItem(self.treeWidget)
        item_1 = QtWidgets.QTreeWidgetItem(item_0)
        item_1.setCheckState(1, QtCore.Qt.Unchecked)
        item_1 = QtWidgets.QTreeWidgetItem(item_0)
        item_1.setFlags(QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsEditable|QtCore.Qt.ItemIsDragEnabled|QtCore.Qt.ItemIsUserCheckable|QtCore.Qt.ItemIsEnabled)
        self.treeWidget.header().setCascadingSectionResizes(False)
        self.treeWidget.header().setDefaultSectionSize(100)
        self.treeWidget.header().setMinimumSectionSize(26)
        self.treeWidget.header().setStretchLastSection(False)
        self.gridLayout_2.addWidget(self.treeWidget, 1, 0, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_2.addItem(spacerItem1, 2, 0, 1, 1)
        self.statusLabel = QtWidgets.QLabel(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.statusLabel.sizePolicy().hasHeightForWidth())
        self.statusLabel.setSizePolicy(sizePolicy)
        self.statusLabel.setText("")
        self.statusLabel.setObjectName("statusLabel")
        self.gridLayout_2.addWidget(self.statusLabel, 4, 0, 1, 1)
        self.infoTree = InfoTreeWidget(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.infoTree.sizePolicy().hasHeightForWidth())
        self.infoTree.setSizePolicy(sizePolicy)
        self.infoTree.setObjectName("infoTree")
        self.gridLayout_2.addWidget(self.infoTree, 3, 0, 1, 1)
        self.gridLayout.addLayout(self.gridLayout_2, 0, 1, 4, 1)
        self.fileSlider = QtWidgets.QSlider(Form)
        self.fileSlider.setOrientation(QtCore.Qt.Horizontal)
        self.fileSlider.setObjectName("fileSlider")
        self.gridLayout.addWidget(self.fileSlider, 2, 0, 1, 1)
        self.plot_down = CRBarPlotWidget(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.plot_down.sizePolicy().hasHeightForWidth())
        self.plot_down.setSizePolicy(sizePolicy)
        self.plot_down.setObjectName("plot_down")
        self.gridLayout.addWidget(self.plot_down, 1, 0, 1, 1)
        self.plot_up = CRBarPlotWidget(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.plot_up.sizePolicy().hasHeightForWidth())
        self.plot_up.setSizePolicy(sizePolicy)
        self.plot_up.setObjectName("plot_up")
        self.gridLayout.addWidget(self.plot_up, 0, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.loadCRButton.setText(_translate("Form", "Load Commit Report"))
        self.treeWidget.headerItem().setText(0, _translate("Form", "Options"))
        self.treeWidget.headerItem().setText(1, _translate("Form", "Value"))
        __sortingEnabled = self.treeWidget.isSortingEnabled()
        self.treeWidget.setSortingEnabled(False)
        self.treeWidget.topLevelItem(0).setText(0, _translate("Form", "Show CF graph"))
        self.treeWidget.topLevelItem(1).setText(0, _translate("Form", "Show DF graph"))
        self.treeWidget.topLevelItem(2).setText(0, _translate("Form", "CommitReport"))
        self.treeWidget.topLevelItem(2).child(0).setText(0, _translate("Form", "Merge reports"))
        self.treeWidget.topLevelItem(2).child(1).setText(0, _translate("Form", "Commit map"))
        self.treeWidget.setSortingEnabled(__sortingEnabled)

from varats.gui.info import InfoTreeWidget
from varats.plots.commit_report_plots import CRBarPlotWidget

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    ui = Ui_Form()
    ui.setupUi(Form)
    Form.show()
    sys.exit(app.exec_())

