# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'BuildMenu.ui'
#
# Created by: PyQt5 UI code generator 5.12.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_BuildSetup(object):

    def setupUi(self, BuildSetup):
        BuildSetup.setObjectName("BuildSetup")
        BuildSetup.resize(640, 480)
        self.gridLayout = QtWidgets.QGridLayout(BuildSetup)
        self.gridLayout.setObjectName("gridLayout")
        self.advancedMode = QtWidgets.QPushButton(BuildSetup)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.advancedMode.sizePolicy().hasHeightForWidth()
        )
        self.advancedMode.setSizePolicy(sizePolicy)
        self.advancedMode.setObjectName("advancedMode")
        self.gridLayout.addWidget(self.advancedMode, 2, 0, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(
            40, 20, QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Minimum
        )
        self.gridLayout.addItem(spacerItem, 2, 1, 1, 1)
        self.widget = QtWidgets.QWidget(BuildSetup)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.widget.sizePolicy().hasHeightForWidth()
        )
        self.widget.setSizePolicy(sizePolicy)
        self.widget.setObjectName("widget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.widget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.sourceLabel = QtWidgets.QLabel(self.widget)
        self.sourceLabel.setObjectName("sourceLabel")
        self.verticalLayout.addWidget(self.sourceLabel)
        self.sourcePath = QtWidgets.QLineEdit(self.widget)
        self.sourcePath.setObjectName("sourcePath")
        self.verticalLayout.addWidget(self.sourcePath)
        self.installLabel = QtWidgets.QLabel(self.widget)
        self.installLabel.setObjectName("installLabel")
        self.verticalLayout.addWidget(self.installLabel)
        self.installPath = QtWidgets.QLineEdit(self.widget)
        self.installPath.setObjectName("installPath")
        self.verticalLayout.addWidget(self.installPath)
        spacerItem1 = QtWidgets.QSpacerItem(
            20, 140, QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding
        )
        self.verticalLayout.addItem(spacerItem1)
        self.textOutput = QtWidgets.QTextEdit(self.widget)
        self.textOutput.setObjectName("textOutput")
        self.verticalLayout.addWidget(self.textOutput)
        self.progressBar = QtWidgets.QProgressBar(self.widget)
        self.progressBar.setProperty("value", 24)
        self.progressBar.setObjectName("progressBar")
        self.verticalLayout.addWidget(self.progressBar)
        self.statusLabel = QtWidgets.QLabel(self.widget)
        self.statusLabel.setText("")
        self.statusLabel.setObjectName("statusLabel")
        self.verticalLayout.addWidget(self.statusLabel)
        self.gridLayout.addWidget(self.widget, 0, 0, 1, 2)
        self.widget_2 = QtWidgets.QWidget(BuildSetup)
        self.widget_2.setMinimumSize(QtCore.QSize(0, 0))
        self.widget_2.setObjectName("widget_2")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.widget_2)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.initButton = QtWidgets.QPushButton(self.widget_2)
        self.initButton.setObjectName("initButton")
        self.verticalLayout_2.addWidget(self.initButton)
        self.updateButton = QtWidgets.QPushButton(self.widget_2)
        self.updateButton.setObjectName("updateButton")
        self.verticalLayout_2.addWidget(self.updateButton)
        self.widget_4 = QtWidgets.QWidget(self.widget_2)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.widget_4.sizePolicy().hasHeightForWidth()
        )
        self.widget_4.setSizePolicy(sizePolicy)
        self.widget_4.setObjectName("widget_4")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.widget_4)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.llvmLabel = QtWidgets.QLabel(self.widget_4)
        self.llvmLabel.setObjectName("llvmLabel")
        self.gridLayout_2.addWidget(self.llvmLabel, 0, 0, 1, 1)
        self.llvmStatus = QtWidgets.QLabel(self.widget_4)
        self.llvmStatus.setObjectName("llvmStatus")
        self.gridLayout_2.addWidget(self.llvmStatus, 0, 1, 1, 1)
        self.clangLabel = QtWidgets.QLabel(self.widget_4)
        self.clangLabel.setObjectName("clangLabel")
        self.gridLayout_2.addWidget(self.clangLabel, 1, 0, 1, 1)
        self.clangStatus = QtWidgets.QLabel(self.widget_4)
        self.clangStatus.setObjectName("clangStatus")
        self.gridLayout_2.addWidget(self.clangStatus, 1, 1, 1, 1)
        self.varaLabel = QtWidgets.QLabel(self.widget_4)
        self.varaLabel.setObjectName("varaLabel")
        self.gridLayout_2.addWidget(self.varaLabel, 2, 0, 1, 1)
        self.varaStatus = QtWidgets.QLabel(self.widget_4)
        self.varaStatus.setObjectName("varaStatus")
        self.gridLayout_2.addWidget(self.varaStatus, 2, 1, 1, 1)
        self.verticalLayout_2.addWidget(self.widget_4)
        self.buildButton = QtWidgets.QPushButton(self.widget_2)
        self.buildButton.setObjectName("buildButton")
        self.verticalLayout_2.addWidget(self.buildButton)
        self.widget_3 = QtWidgets.QWidget(self.widget_2)
        self.widget_3.setObjectName("widget_3")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.widget_3)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.checkDev = QtWidgets.QCheckBox(self.widget_3)
        self.checkDev.setObjectName("checkDev")
        self.verticalLayout_3.addWidget(self.checkDev)
        self.checkOpt = QtWidgets.QCheckBox(self.widget_3)
        self.checkOpt.setObjectName("checkOpt")
        self.verticalLayout_3.addWidget(self.checkOpt)
        self.verticalLayout_2.addWidget(self.widget_3)
        spacerItem2 = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding
        )
        self.verticalLayout_2.addItem(spacerItem2)
        self.gridLayout.addWidget(self.widget_2, 0, 2, 3, 1)

        self.retranslateUi(BuildSetup)
        QtCore.QMetaObject.connectSlotsByName(BuildSetup)

    def retranslateUi(self, BuildSetup):
        _translate = QtCore.QCoreApplication.translate
        BuildSetup.setWindowTitle(_translate("BuildSetup", "VaRA build setup"))
        self.advancedMode.setText(_translate("BuildSetup", "Toggle Dev View"))
        self.sourceLabel.setText(_translate("BuildSetup", "VaRA source path"))
        self.installLabel.setText(_translate("BuildSetup", "VaRA install path"))
        self.initButton.setText(_translate("BuildSetup", "Init"))
        self.updateButton.setText(_translate("BuildSetup", "Update"))
        self.llvmLabel.setText(_translate("BuildSetup", "llvm"))
        self.llvmStatus.setText(_translate("BuildSetup", "undef"))
        self.clangLabel.setText(_translate("BuildSetup", "clang"))
        self.clangStatus.setText(_translate("BuildSetup", "undef"))
        self.varaLabel.setText(_translate("BuildSetup", "VaRA"))
        self.varaStatus.setText(_translate("BuildSetup", "undef"))
        self.buildButton.setText(_translate("BuildSetup", "Build"))
        self.checkDev.setText(_translate("BuildSetup", "Dev"))
        self.checkOpt.setText(_translate("BuildSetup", "Opt"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    BuildSetup = QtWidgets.QWidget()
    ui = Ui_BuildSetup()
    ui.setupUi(BuildSetup)
    BuildSetup.show()
    sys.exit(app.exec_())
