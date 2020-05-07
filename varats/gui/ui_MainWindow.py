# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'MainWindow.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1024, 576)
        icon = QtGui.QIcon()
        icon.addPixmap(
            QtGui.QPixmap("../../../icons/straus64.png"), QtGui.QIcon.Normal,
            QtGui.QIcon.Off
        )
        MainWindow.setWindowIcon(icon)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)
        self.tabWidget.setTabsClosable(True)
        self.tabWidget.setMovable(True)
        self.tabWidget.setObjectName("tabWidget")
        self.gridLayout.addWidget(self.tabWidget, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1024, 29))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuConfig = QtWidgets.QMenu(self.menuFile)
        self.menuConfig.setObjectName("menuConfig")
        self.menuView = QtWidgets.QMenu(self.menubar)
        self.menuView.setObjectName("menuView")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setEnabled(True)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionQuit = QtWidgets.QAction(MainWindow)
        self.actionQuit.setObjectName("actionQuit")
        self.actionExampleView = QtWidgets.QAction(MainWindow)
        self.actionExampleView.setObjectName("actionExampleView")
        self.actionCR_BarView = QtWidgets.QAction(MainWindow)
        self.actionCR_BarView.setObjectName("actionCR_BarView")
        self.actionSetup = QtWidgets.QAction(MainWindow)
        self.actionSetup.setObjectName("actionSetup")
        self.actionDownload_VaRA = QtWidgets.QAction(MainWindow)
        self.actionDownload_VaRA.setObjectName("actionDownload_VaRA")
        self.actionUpdate_VaRA = QtWidgets.QAction(MainWindow)
        self.actionUpdate_VaRA.setObjectName("actionUpdate_VaRA")
        self.actionShow_VaRA_status = QtWidgets.QAction(MainWindow)
        self.actionShow_VaRA_status.setObjectName("actionShow_VaRA_status")
        self.actionVaRA_Setup = QtWidgets.QAction(MainWindow)
        self.actionVaRA_Setup.setObjectName("actionVaRA_Setup")
        self.actionSave_Config = QtWidgets.QAction(MainWindow)
        self.actionSave_Config.setObjectName("actionSave_Config")
        self.actionCreate_BenchBuild_Config = QtWidgets.QAction(MainWindow)
        self.actionCreate_BenchBuild_Config.setObjectName(
            "actionCreate_BenchBuild_Config"
        )
        self.actionInteractionFilter_Editor = QtWidgets.QAction(MainWindow)
        self.actionInteractionFilter_Editor.setObjectName(
            "actionInteractionFilter_Editor"
        )
        self.menuConfig.addAction(self.actionCreate_BenchBuild_Config)
        self.menuConfig.addAction(self.actionSave_Config)
        self.menuFile.addAction(self.actionVaRA_Setup)
        self.menuFile.addAction(self.actionInteractionFilter_Editor)
        self.menuFile.addAction(self.menuConfig.menuAction())
        self.menuFile.addAction(self.actionQuit)
        self.menuView.addAction(self.actionExampleView)
        self.menuView.addAction(self.actionCR_BarView)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuView.menuAction())

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(-1)
        self.actionQuit.triggered.connect(MainWindow.close)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "VaRA-TS"))
        self.menuFile.setTitle(_translate("MainWindow", "File"))
        self.menuConfig.setTitle(_translate("MainWindow", "Config"))
        self.menuView.setTitle(_translate("MainWindow", "View"))
        self.actionQuit.setText(_translate("MainWindow", "Quit"))
        self.actionQuit.setShortcut(_translate("MainWindow", "Ctrl+Q"))
        self.actionExampleView.setText(_translate("MainWindow", "ExampleView"))
        self.actionCR_BarView.setText(_translate("MainWindow", "CR-BarView"))
        self.actionSetup.setText(_translate("MainWindow", "Setup"))
        self.actionDownload_VaRA.setText(
            _translate("MainWindow", "Initialize VaRA")
        )
        self.actionDownload_VaRA.setToolTip(
            _translate("MainWindow", "Downloads and builds VaRA")
        )
        self.actionUpdate_VaRA.setText(_translate("MainWindow", "Update VaRA"))
        self.actionShow_VaRA_status.setText(
            _translate("MainWindow", "Show VaRA status")
        )
        self.actionVaRA_Setup.setText(_translate("MainWindow", "VaRA Setup"))
        self.actionVaRA_Setup.setShortcut(_translate("MainWindow", "Ctrl+B"))
        self.actionSave_Config.setText(
            _translate("MainWindow", "Save VaRA Config")
        )
        self.actionCreate_BenchBuild_Config.setText(
            _translate("MainWindow", "Create BenchBuild Config")
        )
        self.actionInteractionFilter_Editor.setText(
            _translate("MainWindow", "InteractionFilter Editor")
        )


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
