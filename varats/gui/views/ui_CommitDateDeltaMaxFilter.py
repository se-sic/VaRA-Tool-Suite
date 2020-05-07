# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'CommitDateDeltaMaxFilter.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

from varats.gui import icons_rc


class Ui_CommitDateDeltaMaxFilter(object):

    def setupUi(self, CommitDateDeltaMaxFilter):
        CommitDateDeltaMaxFilter.setObjectName("CommitDateDeltaMaxFilter")
        CommitDateDeltaMaxFilter.resize(400, 45)
        self.verticalLayout = QtWidgets.QVBoxLayout(CommitDateDeltaMaxFilter)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(CommitDateDeltaMaxFilter)
        self.label.setEnabled(True)
        self.label.setMinimumSize(QtCore.QSize(200, 0))
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.uiCommitDateDeltaMax = QtWidgets.QLineEdit(
            CommitDateDeltaMaxFilter
        )
        self.uiCommitDateDeltaMax.setObjectName("uiCommitDateDeltaMax")
        self.horizontalLayout.addWidget(self.uiCommitDateDeltaMax)
        self.uiHelp = QtWidgets.QPushButton(CommitDateDeltaMaxFilter)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed
        )
        sizePolicy.setHorizontalStretch(30)
        sizePolicy.setVerticalStretch(30)
        sizePolicy.setHeightForWidth(
            self.uiHelp.sizePolicy().hasHeightForWidth()
        )
        self.uiHelp.setSizePolicy(sizePolicy)
        self.uiHelp.setMaximumSize(QtCore.QSize(30, 30))
        self.uiHelp.setText("")
        icon = QtGui.QIcon()
        icon.addPixmap(
            QtGui.QPixmap(":/breeze/light/help-about.svg"), QtGui.QIcon.Normal,
            QtGui.QIcon.Off
        )
        self.uiHelp.setIcon(icon)
        self.uiHelp.setObjectName("uiHelp")
        self.horizontalLayout.addWidget(self.uiHelp)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(CommitDateDeltaMaxFilter)
        QtCore.QMetaObject.connectSlotsByName(CommitDateDeltaMaxFilter)

    def retranslateUi(self, CommitDateDeltaMaxFilter):
        _translate = QtCore.QCoreApplication.translate
        CommitDateDeltaMaxFilter.setWindowTitle(
            _translate("CommitDateDeltaMaxFilter", "Form")
        )
        self.label.setText(
            _translate("CommitDateDeltaMaxFilter", "CommitDateDelta Maximum")
        )
        self.uiHelp.setToolTip(_translate("CommitDateDeltaMaxFilter", "Help"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    CommitDateDeltaMaxFilter = QtWidgets.QWidget()
    ui = Ui_CommitDateDeltaMaxFilter()
    ui.setupUi(CommitDateDeltaMaxFilter)
    CommitDateDeltaMaxFilter.show()
    sys.exit(app.exec_())
