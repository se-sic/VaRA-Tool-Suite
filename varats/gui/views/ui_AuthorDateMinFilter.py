# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'AuthorDateMinFilter.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_AuthorDateMinFilter(object):

    def setupUi(self, AuthorDateMinFilter):
        AuthorDateMinFilter.setObjectName("AuthorDateMinFilter")
        AuthorDateMinFilter.resize(353, 45)
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(AuthorDateMinFilter)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(AuthorDateMinFilter)
        self.label.setEnabled(True)
        self.label.setMinimumSize(QtCore.QSize(200, 0))
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.uiAuthorDateMin = QtWidgets.QDateTimeEdit(AuthorDateMinFilter)
        self.uiAuthorDateMin.setButtonSymbols(
            QtWidgets.QAbstractSpinBox.UpDownArrows
        )
        self.uiAuthorDateMin.setCalendarPopup(True)
        self.uiAuthorDateMin.setTimeSpec(QtCore.Qt.UTC)
        self.uiAuthorDateMin.setObjectName("uiAuthorDateMin")
        self.horizontalLayout.addWidget(self.uiAuthorDateMin)
        self.verticalLayout_3.addLayout(self.horizontalLayout)

        self.retranslateUi(AuthorDateMinFilter)
        QtCore.QMetaObject.connectSlotsByName(AuthorDateMinFilter)

    def retranslateUi(self, AuthorDateMinFilter):
        _translate = QtCore.QCoreApplication.translate
        AuthorDateMinFilter.setWindowTitle(
            _translate("AuthorDateMinFilter", "Form")
        )
        self.label.setText(
            _translate("AuthorDateMinFilter", "AuthorDate Minimum")
        )
        self.uiAuthorDateMin.setDisplayFormat(
            _translate("AuthorDateMinFilter", "dd.MM.yyyy HH:mm")
        )


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    AuthorDateMinFilter = QtWidgets.QWidget()
    ui = Ui_AuthorDateMinFilter()
    ui.setupUi(AuthorDateMinFilter)
    AuthorDateMinFilter.show()
    sys.exit(app.exec_())
