# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'CommitDateDeltaMinFilter.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

from varats.gui import icons_rc


class Ui_CommitDateDeltaMinFilter(object):

    def setupUi(self, CommitDateDeltaMinFilter):
        CommitDateDeltaMinFilter.setObjectName("CommitDateDeltaMinFilter")
        CommitDateDeltaMinFilter.resize(395, 45)
        self.verticalLayout = QtWidgets.QVBoxLayout(CommitDateDeltaMinFilter)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(CommitDateDeltaMinFilter)
        self.label.setEnabled(True)
        self.label.setMinimumSize(QtCore.QSize(200, 0))
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.uiCommitDateDeltaMin = QtWidgets.QLineEdit(
            CommitDateDeltaMinFilter
        )
        self.uiCommitDateDeltaMin.setObjectName("uiCommitDateDeltaMin")
        self.horizontalLayout.addWidget(self.uiCommitDateDeltaMin)
        self.uiHelp = QtWidgets.QPushButton(CommitDateDeltaMinFilter)
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

        self.retranslateUi(CommitDateDeltaMinFilter)
        QtCore.QMetaObject.connectSlotsByName(CommitDateDeltaMinFilter)

    def retranslateUi(self, CommitDateDeltaMinFilter):
        _translate = QtCore.QCoreApplication.translate
        CommitDateDeltaMinFilter.setWindowTitle(
            _translate("CommitDateDeltaMinFilter", "Form")
        )
        self.label.setText(
            _translate("CommitDateDeltaMinFilter", "CommitDateDelta Minumum")
        )
        self.uiHelp.setToolTip(_translate("CommitDateDeltaMinFilter", "Help"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    CommitDateDeltaMinFilter = QtWidgets.QWidget()
    ui = Ui_CommitDateDeltaMinFilter()
    ui.setupUi(CommitDateDeltaMinFilter)
    CommitDateDeltaMinFilter.show()
    sys.exit(app.exec_())
