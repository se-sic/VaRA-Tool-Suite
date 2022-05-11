# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'CaseStudyGeneration.ui'
#
# Created by: PyQt5 UI code generator 5.13.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.setEnabled(True)
        MainWindow.resize(720, 443)
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
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
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
        self.per_year = QtWidgets.QRadioButton(self.strategie)
        self.per_year.setObjectName("per_year")
        self.verticalLayout.addWidget(self.per_year)
        spacerItem = QtWidgets.QSpacerItem(
            20, 22, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed
        )
        self.verticalLayout.addItem(spacerItem)
        self.label_2 = QtWidgets.QLabel(self.strategie)
        self.label_2.setObjectName("label_2")
        self.verticalLayout.addWidget(self.label_2)
        self.cs_version = QtWidgets.QSpinBox(self.strategie)
        self.cs_version.setObjectName("cs_version")
        self.verticalLayout.addWidget(self.cs_version)
        self.generate = QtWidgets.QPushButton(self.strategie)
        self.generate.setObjectName("generate")
        self.verticalLayout.addWidget(self.generate)
        spacerItem1 = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding
        )
        self.verticalLayout.addItem(spacerItem1)
        self.gridLayout.addWidget(self.strategie, 0, 1, 1, 1)
        self.projects = QtWidgets.QGroupBox(self.centralwidget)
        self.projects.setObjectName("projects")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.projects)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.project_search = QtWidgets.QLineEdit(self.projects)
        self.project_search.setClearButtonEnabled(True)
        self.project_search.setObjectName("project_search")
        self.verticalLayout_4.addWidget(self.project_search)
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
        self.gridLayout.addWidget(self.projects, 0, 0, 1, 1)
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
        self.revisions = QtWidgets.QLabel(self.revisionsPage)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.revisions.sizePolicy().hasHeightForWidth()
        )
        self.revisions.setSizePolicy(sizePolicy)
        self.revisions.setObjectName("revisions")
        self.verticalLayout_3.addWidget(self.revisions)
        self.commit_search = QtWidgets.QLineEdit(self.revisionsPage)
        self.commit_search.setClearButtonEnabled(True)
        self.commit_search.setObjectName("commit_search")
        self.verticalLayout_3.addWidget(self.commit_search)
        self.revision_list = QtWidgets.QTableView(self.revisionsPage)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(10)
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
        self.revision_list.setSortingEnabled(True)
        self.revision_list.setObjectName("revision_list")
        self.revision_list.verticalHeader().setVisible(False)
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
        self.gridLayout_2 = QtWidgets.QGridLayout(self.sample_page)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.code_commits = QtWidgets.QCheckBox(self.sample_page)
        self.code_commits.setObjectName("code_commits")
        self.gridLayout_2.addWidget(self.code_commits, 3, 0, 1, 2)
        self.num_revs = QtWidgets.QSpinBox(self.sample_page)
        self.num_revs.setProperty("value", 10)
        self.num_revs.setObjectName("num_revs")
        self.gridLayout_2.addWidget(self.num_revs, 2, 0, 1, 1)
        self.label = QtWidgets.QLabel(self.sample_page)
        self.label.setObjectName("label")
        self.gridLayout_2.addWidget(self.label, 2, 1, 1, 1)
        self.sampling_method = QtWidgets.QComboBox(self.sample_page)
        self.sampling_method.setObjectName("sampling_method")
        self.gridLayout_2.addWidget(self.sampling_method, 1, 0, 1, 2)
        spacerItem2 = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding
        )
        self.gridLayout_2.addItem(spacerItem2, 4, 0, 1, 1)
        self.strategie_forms.addWidget(self.sample_page)
        self.per_year_page = QtWidgets.QWidget()
        self.per_year_page.setObjectName("per_year_page")
        self.seperate = QtWidgets.QCheckBox(self.per_year_page)
        self.seperate.setGeometry(QtCore.QRect(0, 40, 246, 22))
        self.seperate.setObjectName("seperate")
        self.widget = QtWidgets.QWidget(self.per_year_page)
        self.widget.setGeometry(QtCore.QRect(252, 189, 16, 16))
        self.widget.setObjectName("widget")
        self.label_3 = QtWidgets.QLabel(self.per_year_page)
        self.label_3.setGeometry(QtCore.QRect(0, 0, 111, 21))
        self.label_3.setObjectName("label_3")
        self.revs_per_year = QtWidgets.QSpinBox(self.per_year_page)
        self.revs_per_year.setGeometry(QtCore.QRect(120, 0, 52, 32))
        self.revs_per_year.setObjectName("revs_per_year")
        self.strategie_forms.addWidget(self.per_year_page)
        self.gridLayout.addWidget(self.strategie_forms, 0, 2, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 720, 30))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        self.strategie_forms.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.strategie.setTitle(_translate("MainWindow", "Strategie"))
        self.select_specific.setText(
            _translate("MainWindow", "Select Revision")
        )
        self.sample.setText(_translate("MainWindow", "Sample"))
        self.per_year.setText(_translate("MainWindow", "Revisions Per Year"))
        self.label_2.setText(_translate("MainWindow", "Casestudy Version"))
        self.generate.setText(_translate("MainWindow", "Generate"))
        self.projects.setTitle(_translate("MainWindow", "Projects"))
        self.project_search.setPlaceholderText(
            _translate("MainWindow", "Search")
        )
        self.revisions.setText(_translate("MainWindow", "Revisions"))
        self.commit_search.setPlaceholderText(
            _translate("MainWindow", "Search")
        )
        self.code_commits.setToolTip(
            _translate(
                "MainWindow", "Only sample commits which add lines of code"
            )
        )
        self.code_commits.setText(_translate("MainWindow", "Only Code Commits"))
        self.label.setText(_translate("MainWindow", "Number of Revisions"))
        self.seperate.setText(
            _translate("MainWindow", "Seperate Years into different Stages")
        )
        self.label_3.setText(_translate("MainWindow", "Revisions Per Year"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())
