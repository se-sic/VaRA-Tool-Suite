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
        Form.resize(871, 607)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.gridLayout.setObjectName("gridLayout")
        self.plot_down = CRBarPlotWidget(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.plot_down.sizePolicy().hasHeightForWidth())
        self.plot_down.setSizePolicy(sizePolicy)
        self.plot_down.setObjectName("plot_down")
        self.gridLayout.addWidget(self.plot_down, 2, 0, 1, 1)
        self.plot_up = CRBarPlotWidget(Form)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.plot_up.sizePolicy().hasHeightForWidth())
        self.plot_up.setSizePolicy(sizePolicy)
        self.plot_up.setObjectName("plot_up")
        self.gridLayout.addWidget(self.plot_up, 1, 0, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(40, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout.addItem(spacerItem, 3, 0, 1, 1)
        self.gridLayout_2 = QtWidgets.QGridLayout()
        self.gridLayout_2.setObjectName("gridLayout_2")
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_2.addItem(spacerItem1, 3, 0, 2, 1)
        self.loadCRButton = QtWidgets.QPushButton(Form)
        self.loadCRButton.setObjectName("loadCRButton")
        self.gridLayout_2.addWidget(self.loadCRButton, 0, 0, 1, 1)
        self.check_cf_graph = QtWidgets.QCheckBox(Form)
        self.check_cf_graph.setObjectName("check_cf_graph")
        self.gridLayout_2.addWidget(self.check_cf_graph, 1, 0, 1, 1)
        self.check_df_graph = QtWidgets.QCheckBox(Form)
        self.check_df_graph.setObjectName("check_df_graph")
        self.gridLayout_2.addWidget(self.check_df_graph, 2, 0, 1, 1)
        self.gridLayout.addLayout(self.gridLayout_2, 1, 1, 3, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.loadCRButton.setText(_translate("Form", "Load Commit Report"))
        self.check_cf_graph.setText(_translate("Form", "Show CF graph"))
        self.check_df_graph.setText(_translate("Form", "Show DF graph"))

from varats.data.commit_report import CRBarPlotWidget

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Form = QtWidgets.QWidget()
    ui = Ui_Form()
    ui.setupUi(Form)
    Form.show()
    sys.exit(app.exec_())

