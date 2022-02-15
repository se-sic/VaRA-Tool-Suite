# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Mainwindow.ui'
#
# Created by: PyQt5 UI code generator 5.13.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.setEnabled(True)
        MainWindow.resize(698, 379)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            MainWindow.sizePolicy().hasHeightForWidth()
        )
        MainWindow.setSizePolicy(sizePolicy)
        MainWindow.setMinimumSize(QtCore.QSize(0, 0))
        MainWindow.setDocumentMode(False)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.projects = QtWidgets.QGroupBox(self.centralwidget)
        self.projects.setObjectName("projects")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.projects)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.project_list = QtWidgets.QListWidget(self.projects)
        self.project_list.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )
        self.project_list.setObjectName("project_list")
        self.verticalLayout_4.addWidget(self.project_list)
        self.project_details = QtWidgets.QTextBrowser(self.projects)
        self.project_details.setMaximumSize(QtCore.QSize(16777189, 100))
        self.project_details.setObjectName("project_details")
        self.verticalLayout_4.addWidget(self.project_details)
        self.horizontalLayout.addWidget(self.projects)
        self.strategie = QtWidgets.QGroupBox(self.centralwidget)
        self.strategie.setObjectName("strategie")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.strategie)
        self.verticalLayout.setObjectName("verticalLayout")
        self.select_specific = QtWidgets.QRadioButton(self.strategie)
        self.select_specific.setChecked(True)
        self.select_specific.setObjectName("select_specific")
        self.verticalLayout.addWidget(self.select_specific)
        self.sample = QtWidgets.QRadioButton(self.strategie)
        self.sample.setObjectName("sample")
        self.verticalLayout.addWidget(self.sample)
        spacerItem = QtWidgets.QSpacerItem(
            20, 22, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed
        )
        self.verticalLayout.addItem(spacerItem)
        self.generate = QtWidgets.QPushButton(self.strategie)
        self.generate.setObjectName("generate")
        self.verticalLayout.addWidget(self.generate)
        spacerItem1 = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding
        )
        self.verticalLayout.addItem(spacerItem1)
        self.horizontalLayout.addWidget(self.strategie)
        self.strategie_forms = QtWidgets.QStackedWidget(self.centralwidget)
        self.strategie_forms.setEnabled(True)
        self.strategie_forms.setMinimumSize(QtCore.QSize(100, 0))
        self.strategie_forms.setAutoFillBackground(False)
        self.strategie_forms.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.strategie_forms.setMidLineWidth(0)
        self.strategie_forms.setObjectName("strategie_forms")
        self.revisionsPage = QtWidgets.QWidget()
        self.revisionsPage.setObjectName("revisionsPage")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.revisionsPage)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.revision_list = QtWidgets.QTableWidget(self.revisionsPage)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.revision_list.sizePolicy().hasHeightForWidth()
        )
        self.revision_list.setSizePolicy(sizePolicy)
        font = QtGui.QFont()
        font.setFamily("Monospace")
        self.revision_list.setFont(font)
        self.revision_list.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )
        self.revision_list.setDefaultDropAction(QtCore.Qt.TargetMoveAction)
        self.revision_list.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self.revision_list.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows
        )
        self.revision_list.setShowGrid(True)
        self.revision_list.setColumnCount(3)
        self.revision_list.setObjectName("revision_list")
        self.revision_list.setRowCount(0)
        item = QtWidgets.QTableWidgetItem()
        font = QtGui.QFont()
        font.setFamily("Monospace")
        item.setFont(font)
        self.revision_list.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        self.revision_list.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        self.revision_list.setHorizontalHeaderItem(2, item)
        self.revision_list.verticalHeader().setVisible(False)
        self.revision_list.verticalHeader().setHighlightSections(False)
        self.verticalLayout_3.addWidget(self.revision_list)
        self.revision_details = QtWidgets.QTextBrowser(self.revisionsPage)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.MinimumExpanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.revision_details.sizePolicy().hasHeightForWidth()
        )
        self.revision_details.setSizePolicy(sizePolicy)
        self.revision_details.setMaximumSize(QtCore.QSize(16777215, 100))
        self.revision_details.setObjectName("revision_details")
        self.verticalLayout_3.addWidget(self.revision_details)
        self.strategie_forms.addWidget(self.revisionsPage)
        self.sample_page = QtWidgets.QWidget()
        self.sample_page.setObjectName("sample_page")
        self.formLayout = QtWidgets.QFormLayout(self.sample_page)
        self.formLayout.setObjectName("formLayout")
        self.sampling_method = QtWidgets.QComboBox(self.sample_page)
        self.sampling_method.setObjectName("sampling_method")
        self.formLayout.setWidget(
            0, QtWidgets.QFormLayout.SpanningRole, self.sampling_method
        )
        self.label = QtWidgets.QLabel(self.sample_page)
        self.label.setObjectName("label")
        self.formLayout.setWidget(
            1, QtWidgets.QFormLayout.LabelRole, self.label
        )
        self.num_revs = QtWidgets.QSpinBox(self.sample_page)
        self.num_revs.setProperty("value", 10)
        self.num_revs.setObjectName("num_revs")
        self.formLayout.setWidget(
            1, QtWidgets.QFormLayout.FieldRole, self.num_revs
        )
        self.strategie_forms.addWidget(self.sample_page)
        self.horizontalLayout.addWidget(self.strategie_forms)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 698, 30))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        self.strategie_forms.setCurrentIndex(1)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.strategie.setTitle(_translate("MainWindow", "Strategie"))
        self.select_specific.setText(
            _translate("MainWindow", "Select Revision")
        )
        self.sample.setText(_translate("MainWindow", "Sample"))
        self.generate.setText(_translate("MainWindow", "Generate"))
        item = self.revision_list.horizontalHeaderItem(0)
        item.setText(_translate("MainWindow", "Commit Hash"))
        item = self.revision_list.horizontalHeaderItem(1)
        item.setText(_translate("MainWindow", "Author"))
        item = self.revision_list.horizontalHeaderItem(2)
        item.setText(_translate("MainWindow", "Date"))
        self.label.setText(_translate("MainWindow", "Number of Revisions"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
