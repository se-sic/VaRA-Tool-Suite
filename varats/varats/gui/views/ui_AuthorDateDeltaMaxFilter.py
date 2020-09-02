# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'AuthorDateDeltaMaxFilter.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

from varats.gui import icons_rc


class Ui_AuthorDateDeltaMaxFilter(object):

    def setupUi(self, AuthorDateDeltaMaxFilter):
        AuthorDateDeltaMaxFilter.setObjectName("AuthorDateDeltaMaxFilter")
        AuthorDateDeltaMaxFilter.resize(394, 45)
        self.verticalLayout = QtWidgets.QVBoxLayout(AuthorDateDeltaMaxFilter)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(AuthorDateDeltaMaxFilter)
        self.label.setEnabled(True)
        self.label.setMinimumSize(QtCore.QSize(200, 0))
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.uiAuthorDateDeltaMax = QtWidgets.QLineEdit(
            AuthorDateDeltaMaxFilter
        )
        self.uiAuthorDateDeltaMax.setObjectName("uiAuthorDateDeltaMax")
        self.horizontalLayout.addWidget(self.uiAuthorDateDeltaMax)
        self.uiHelp = QtWidgets.QPushButton(AuthorDateDeltaMaxFilter)
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

        self.retranslateUi(AuthorDateDeltaMaxFilter)
        QtCore.QMetaObject.connectSlotsByName(AuthorDateDeltaMaxFilter)

    def retranslateUi(self, AuthorDateDeltaMaxFilter):
        _translate = QtCore.QCoreApplication.translate
        AuthorDateDeltaMaxFilter.setWindowTitle(
            _translate("AuthorDateDeltaMaxFilter", "Form")
        )
        self.label.setText(
            _translate("AuthorDateDeltaMaxFilter", "AuthorDateDelta Maximum")
        )
        self.uiHelp.setToolTip(_translate("AuthorDateDeltaMaxFilter", "Help"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    AuthorDateDeltaMaxFilter = QtWidgets.QWidget()
    ui = Ui_AuthorDateDeltaMaxFilter()
    ui.setupUi(AuthorDateDeltaMaxFilter)
    AuthorDateDeltaMaxFilter.show()
    sys.exit(app.exec_())
