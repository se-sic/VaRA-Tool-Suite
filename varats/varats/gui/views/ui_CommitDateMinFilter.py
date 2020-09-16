# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'CommitDateMinFilter.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_CommitDateMinFilter(object):

    def setupUi(self, CommitDateMinFilter):
        CommitDateMinFilter.setObjectName("CommitDateMinFilter")
        CommitDateMinFilter.resize(353, 45)
        self.verticalLayout = QtWidgets.QVBoxLayout(CommitDateMinFilter)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(CommitDateMinFilter)
        self.label.setEnabled(True)
        self.label.setMinimumSize(QtCore.QSize(200, 0))
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.uiCommitDateMin = QtWidgets.QDateTimeEdit(CommitDateMinFilter)
        self.uiCommitDateMin.setButtonSymbols(
            QtWidgets.QAbstractSpinBox.UpDownArrows
        )
        self.uiCommitDateMin.setCalendarPopup(True)
        self.uiCommitDateMin.setTimeSpec(QtCore.Qt.UTC)
        self.uiCommitDateMin.setObjectName("uiCommitDateMin")
        self.horizontalLayout.addWidget(self.uiCommitDateMin)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(CommitDateMinFilter)
        QtCore.QMetaObject.connectSlotsByName(CommitDateMinFilter)

    def retranslateUi(self, CommitDateMinFilter):
        _translate = QtCore.QCoreApplication.translate
        CommitDateMinFilter.setWindowTitle(
            _translate("CommitDateMinFilter", "Form")
        )
        self.label.setText(
            _translate("CommitDateMinFilter", "CommitDate Minimum")
        )
        self.uiCommitDateMin.setDisplayFormat(
            _translate("CommitDateMinFilter", "dd.MM.yyyy HH:mm")
        )


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    CommitDateMinFilter = QtWidgets.QWidget()
    ui = Ui_CommitDateMinFilter()
    ui.setupUi(CommitDateMinFilter)
    CommitDateMinFilter.show()
    sys.exit(app.exec_())
