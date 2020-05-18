# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'CommitterFilterProperties.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_CommitterFilterProperties(object):

    def setupUi(self, CommitterFilterProperties):
        CommitterFilterProperties.setObjectName("CommitterFilterProperties")
        CommitterFilterProperties.resize(266, 84)
        self.verticalLayout = QtWidgets.QVBoxLayout(CommitterFilterProperties)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(CommitterFilterProperties)
        self.label.setEnabled(True)
        self.label.setMinimumSize(QtCore.QSize(200, 0))
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.uiCommitterName = QtWidgets.QLineEdit(CommitterFilterProperties)
        self.uiCommitterName.setReadOnly(False)
        self.uiCommitterName.setObjectName("uiCommitterName")
        self.horizontalLayout.addWidget(self.uiCommitterName)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label_2 = QtWidgets.QLabel(CommitterFilterProperties)
        self.label_2.setMinimumSize(QtCore.QSize(200, 0))
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_2.addWidget(self.label_2)
        self.uiCommitterEmail = QtWidgets.QLineEdit(CommitterFilterProperties)
        self.uiCommitterEmail.setMaxLength(150)
        self.uiCommitterEmail.setObjectName("uiCommitterEmail")
        self.horizontalLayout_2.addWidget(self.uiCommitterEmail)
        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.retranslateUi(CommitterFilterProperties)
        QtCore.QMetaObject.connectSlotsByName(CommitterFilterProperties)

    def retranslateUi(self, CommitterFilterProperties):
        _translate = QtCore.QCoreApplication.translate
        CommitterFilterProperties.setWindowTitle(
            _translate("CommitterFilterProperties", "Form")
        )
        self.label.setText(
            _translate("CommitterFilterProperties", "Committer Name")
        )
        self.label_2.setText(
            _translate("CommitterFilterProperties", "Committer Email")
        )


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    CommitterFilterProperties = QtWidgets.QWidget()
    ui = Ui_CommitterFilterProperties()
    ui.setupUi(CommitterFilterProperties)
    CommitterFilterProperties.show()
    sys.exit(app.exec_())
