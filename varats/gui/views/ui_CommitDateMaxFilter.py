# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'CommitDateMaxFilter.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_CommitDateMaxFilter(object):

    def setupUi(self, CommitDateMaxFilter):
        CommitDateMaxFilter.setObjectName("CommitDateMaxFilter")
        CommitDateMaxFilter.resize(353, 45)
        self.verticalLayout = QtWidgets.QVBoxLayout(CommitDateMaxFilter)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(CommitDateMaxFilter)
        self.label.setEnabled(True)
        self.label.setMinimumSize(QtCore.QSize(200, 0))
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.uiCommitDateMax = QtWidgets.QDateTimeEdit(CommitDateMaxFilter)
        self.uiCommitDateMax.setButtonSymbols(
            QtWidgets.QAbstractSpinBox.UpDownArrows
        )
        self.uiCommitDateMax.setCalendarPopup(True)
        self.uiCommitDateMax.setTimeSpec(QtCore.Qt.UTC)
        self.uiCommitDateMax.setObjectName("uiCommitDateMax")
        self.horizontalLayout.addWidget(self.uiCommitDateMax)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(CommitDateMaxFilter)
        QtCore.QMetaObject.connectSlotsByName(CommitDateMaxFilter)

    def retranslateUi(self, CommitDateMaxFilter):
        _translate = QtCore.QCoreApplication.translate
        CommitDateMaxFilter.setWindowTitle(
            _translate("CommitDateMaxFilter", "Form")
        )
        self.label.setText(
            _translate("CommitDateMaxFilter", "CommitDate Maximum")
        )
        self.uiCommitDateMax.setDisplayFormat(
            _translate("CommitDateMaxFilter", "dd.MM.yyyy HH:mm")
        )


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    CommitDateMaxFilter = QtWidgets.QWidget()
    ui = Ui_CommitDateMaxFilter()
    ui.setupUi(CommitDateMaxFilter)
    CommitDateMaxFilter.show()
    sys.exit(app.exec_())
