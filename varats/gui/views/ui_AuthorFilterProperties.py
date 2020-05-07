# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'AuthorFilterProperties.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_AuthorFilterProperties(object):

    def setupUi(self, AuthorFilterProperties):
        AuthorFilterProperties.setObjectName("AuthorFilterProperties")
        AuthorFilterProperties.resize(266, 84)
        self.verticalLayout = QtWidgets.QVBoxLayout(AuthorFilterProperties)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(AuthorFilterProperties)
        self.label.setEnabled(True)
        self.label.setMinimumSize(QtCore.QSize(200, 0))
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.uiAuthorName = QtWidgets.QLineEdit(AuthorFilterProperties)
        self.uiAuthorName.setReadOnly(False)
        self.uiAuthorName.setObjectName("uiAuthorName")
        self.horizontalLayout.addWidget(self.uiAuthorName)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label_2 = QtWidgets.QLabel(AuthorFilterProperties)
        self.label_2.setMinimumSize(QtCore.QSize(200, 0))
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_2.addWidget(self.label_2)
        self.uiAuthorEmail = QtWidgets.QLineEdit(AuthorFilterProperties)
        self.uiAuthorEmail.setMaxLength(150)
        self.uiAuthorEmail.setObjectName("uiAuthorEmail")
        self.horizontalLayout_2.addWidget(self.uiAuthorEmail)
        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.retranslateUi(AuthorFilterProperties)
        QtCore.QMetaObject.connectSlotsByName(AuthorFilterProperties)

    def retranslateUi(self, AuthorFilterProperties):
        _translate = QtCore.QCoreApplication.translate
        AuthorFilterProperties.setWindowTitle(
            _translate("AuthorFilterProperties", "Form")
        )
        self.label.setText(_translate("AuthorFilterProperties", "Author Name"))
        self.label_2.setText(
            _translate("AuthorFilterProperties", "Author Email")
        )


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    AuthorFilterProperties = QtWidgets.QWidget()
    ui = Ui_AuthorFilterProperties()
    ui.setupUi(AuthorFilterProperties)
    AuthorFilterProperties.show()
    sys.exit(app.exec_())
