# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'CR-BarView.ui'
#
# Created by: PyQt5 UI code generator 5.12.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

from varats.gui.info import InfoTreeWidget
from varats.gui.options import OptionTreeWidget
from varats.plots.commit_report_plots import CRBarPlotWidget


class Ui_Form(object):

    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(1022, 601)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        spacerItem = QtWidgets.QSpacerItem(
            40, 0, QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum
        )
        self.gridLayout.addItem(spacerItem, 3, 0, 1, 1)
        self.fileSlider = QtWidgets.QSlider(Form)
        self.fileSlider.setOrientation(QtCore.Qt.Horizontal)
        self.fileSlider.setObjectName("fileSlider")
        self.gridLayout.addWidget(self.fileSlider, 2, 0, 1, 1)
        self.gridLayout_2 = QtWidgets.QGridLayout()
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.loadCRButton = QtWidgets.QPushButton(Form)
        self.loadCRButton.setObjectName("loadCRButton")
        self.gridLayout_2.addWidget(self.loadCRButton, 0, 0, 1, 1)
        self.optionsTree = OptionTreeWidget(Form)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.optionsTree.sizePolicy().hasHeightForWidth()
        )
        self.optionsTree.setSizePolicy(sizePolicy)
        self.optionsTree.setAutoFillBackground(True)
        self.optionsTree.setObjectName("optionsTree")
        self.optionsTree.header().setCascadingSectionResizes(False)
        self.optionsTree.header().setDefaultSectionSize(100)
        self.optionsTree.header().setMinimumSectionSize(26)
        self.optionsTree.header().setStretchLastSection(False)
        self.gridLayout_2.addWidget(self.optionsTree, 1, 0, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding
        )
        self.gridLayout_2.addItem(spacerItem1, 2, 0, 1, 1)
        self.statusLabel = QtWidgets.QLabel(Form)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.statusLabel.sizePolicy().hasHeightForWidth()
        )
        self.statusLabel.setSizePolicy(sizePolicy)
        self.statusLabel.setText("")
        self.statusLabel.setObjectName("statusLabel")
        self.gridLayout_2.addWidget(self.statusLabel, 4, 0, 1, 1)
        self.infoTree = InfoTreeWidget(Form)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.infoTree.sizePolicy().hasHeightForWidth()
        )
        self.infoTree.setSizePolicy(sizePolicy)
        self.infoTree.setObjectName("infoTree")
        self.gridLayout_2.addWidget(self.infoTree, 3, 0, 1, 1)
        self.gridLayout.addLayout(self.gridLayout_2, 0, 2, 4, 1)
        self.playerW = QtWidgets.QWidget(Form)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.playerW.sizePolicy().hasHeightForWidth()
        )
        self.playerW.setSizePolicy(sizePolicy)
        self.playerW.setObjectName("playerW")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.playerW)
        self.horizontalLayout.setContentsMargins(4, 0, 4, 0)
        self.horizontalLayout.setSpacing(4)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.stopButton = QtWidgets.QPushButton(self.playerW)
        self.stopButton.setObjectName("stopButton")
        self.horizontalLayout.addWidget(self.stopButton)
        self.playButton = QtWidgets.QPushButton(self.playerW)
        self.playButton.setObjectName("playButton")
        self.horizontalLayout.addWidget(self.playButton)
        self.gridLayout.addWidget(self.playerW, 2, 1, 1, 1)
        self.plot_down = CRBarPlotWidget(Form)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.plot_down.sizePolicy().hasHeightForWidth()
        )
        self.plot_down.setSizePolicy(sizePolicy)
        self.plot_down.setObjectName("plot_down")
        self.gridLayout.addWidget(self.plot_down, 1, 0, 1, 2)
        self.plot_up = CRBarPlotWidget(Form)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.plot_up.sizePolicy().hasHeightForWidth()
        )
        self.plot_up.setSizePolicy(sizePolicy)
        self.plot_up.setObjectName("plot_up")
        self.gridLayout.addWidget(self.plot_up, 0, 0, 1, 2)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.loadCRButton.setText(_translate("Form", "Load Commit Report"))
        self.stopButton.setText(_translate("Form", "||"))
        self.playButton.setText(_translate("Form", ">"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    ui = Ui_Form()
    ui.setupUi(Form)
    Form.show()
    sys.exit(app.exec_())
