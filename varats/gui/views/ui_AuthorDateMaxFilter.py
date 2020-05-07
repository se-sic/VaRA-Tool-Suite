# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'AuthorDateMaxFilter.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_AuthorDateMaxFilter(object):

    def setupUi(self, AuthorDateMaxFilter):
        AuthorDateMaxFilter.setObjectName("AuthorDateMaxFilter")
        AuthorDateMaxFilter.resize(353, 45)
        self.verticalLayout = QtWidgets.QVBoxLayout(AuthorDateMaxFilter)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(AuthorDateMaxFilter)
        self.label.setEnabled(True)
        self.label.setMinimumSize(QtCore.QSize(200, 0))
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.uiAuthorDateMax = QtWidgets.QDateTimeEdit(AuthorDateMaxFilter)
        self.uiAuthorDateMax.setButtonSymbols(
            QtWidgets.QAbstractSpinBox.UpDownArrows
        )
        self.uiAuthorDateMax.setCalendarPopup(True)
        self.uiAuthorDateMax.setTimeSpec(QtCore.Qt.UTC)
        self.uiAuthorDateMax.setObjectName("uiAuthorDateMax")
        self.horizontalLayout.addWidget(self.uiAuthorDateMax)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(AuthorDateMaxFilter)
        QtCore.QMetaObject.connectSlotsByName(AuthorDateMaxFilter)

    def retranslateUi(self, AuthorDateMaxFilter):
        _translate = QtCore.QCoreApplication.translate
        AuthorDateMaxFilter.setWindowTitle(
            _translate("AuthorDateMaxFilter", "Form")
        )
        self.label.setText(
            _translate("AuthorDateMaxFilter", "AuthorDate Maximum")
        )
        self.uiAuthorDateMax.setDisplayFormat(
            _translate("AuthorDateMaxFilter", "dd.MM.yyyy HH:mm")
        )


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    AuthorDateMaxFilter = QtWidgets.QWidget()
    ui = Ui_AuthorDateMaxFilter()
    ui.setupUi(AuthorDateMaxFilter)
    AuthorDateMaxFilter.show()
    sys.exit(app.exec_())
