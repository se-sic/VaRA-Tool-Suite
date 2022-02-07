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
        MainWindow.resize(815, 608)
        MainWindow.setDocumentMode(False)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.strategie = QtWidgets.QGroupBox(self.centralwidget)
        self.strategie.setGeometry(QtCore.QRect(280, 0, 151, 151))
        self.strategie.setObjectName("strategie")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.strategie)
        self.verticalLayout.setObjectName("verticalLayout")
        self.selectspecific = QtWidgets.QRadioButton(self.strategie)
        self.selectspecific.setChecked(True)
        self.selectspecific.setObjectName("selectspecific")
        self.verticalLayout.addWidget(self.selectspecific)
        self.sample = QtWidgets.QRadioButton(self.strategie)
        self.sample.setObjectName("sample")
        self.verticalLayout.addWidget(self.sample)
        self.revisions = QtWidgets.QWidget(self.centralwidget)
        self.revisions.setEnabled(True)
        self.revisions.setGeometry(QtCore.QRect(430, 0, 341, 541))
        self.revisions.setAutoFillBackground(False)
        self.revisions.setObjectName("revisions")
        self.revision_list = QtWidgets.QListWidget(self.revisions)
        self.revision_list.setEnabled(True)
        self.revision_list.setGeometry(QtCore.QRect(0, 0, 341, 421))
        self.revision_list.setObjectName("RevisionList")
        self.revision_details = QtWidgets.QTextBrowser(self.revisions)
        self.revision_details.setGeometry(QtCore.QRect(0, 420, 341, 121))
        self.revision_details.setObjectName("revisiondetails")
        self.generate = QtWidgets.QPushButton(self.centralwidget)
        self.generate.setGeometry(QtCore.QRect(280, 150, 151, 34))
        self.generate.setObjectName("generate")
        self.widget_2 = QtWidgets.QWidget(self.centralwidget)
        self.widget_2.setGeometry(QtCore.QRect(0, 0, 281, 551))
        self.widget_2.setObjectName("widget_2")
        self.project_list = QtWidgets.QListWidget(self.widget_2)
        self.project_list.setGeometry(QtCore.QRect(0, 0, 281, 421))
        self.project_list.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )
        self.project_list.setObjectName("ProjectList")
        self.project_details = QtWidgets.QTextBrowser(self.widget_2)
        self.project_details.setGeometry(QtCore.QRect(0, 420, 281, 121))
        self.project_details.setObjectName("ProjectDetails")
        self.sampling_strategie = QtWidgets.QGroupBox(self.centralwidget)
        self.sampling_strategie.setEnabled(False)
        self.sampling_strategie.setVisible(False)
        self.sampling_strategie.setGeometry(QtCore.QRect(430, 0, 221, 191))
        self.sampling_strategie.setObjectName("groupBox")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.sampling_strategie)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.UniformSampling = QtWidgets.QRadioButton(self.sampling_strategie)
        self.UniformSampling.setObjectName("UniformSampling")
        self.verticalLayout_2.addWidget(self.UniformSampling)
        self.HalfnormalSampling = QtWidgets.QRadioButton(
            self.sampling_strategie
        )
        self.HalfnormalSampling.setObjectName("HalfnormalSampling")
        self.verticalLayout_2.addWidget(self.HalfnormalSampling)
        self.revisions.raise_()
        self.sampling_strategie.raise_()
        self.generate.raise_()
        self.widget_2.raise_()
        self.sampling_strategie.raise_()
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 815, 30))
        self.menubar.setObjectName("menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        self.selectspecific.toggled['bool'].connect(self.revisions.setVisible)
        self.selectspecific.toggled['bool'].connect(self.revisions.setEnabled)
        self.sample.toggled['bool'].connect(self.sampling_strategie.setVisible)
        self.sample.toggled['bool'].connect(self.sampling_strategie.setEnabled)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.sampling_strategie.setTitle(_translate("MainWindow", "Strategie"))
        self.selectspecific.setText(_translate("MainWindow", "Select Revision"))
        self.sample.setText(_translate("MainWindow", "Sample"))
        self.generate.setText(_translate("MainWindow", "Generate"))
        self.sampling_strategie.setTitle(
            _translate("MainWindow", "Sampling Method")
        )
        self.UniformSampling.setText(
            _translate("MainWindow", "UniformSampling")
        )
        self.HalfnormalSampling.setText(
            _translate("MainWindow", "Halfnormal Sampling")
        )
