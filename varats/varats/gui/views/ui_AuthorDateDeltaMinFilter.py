# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'AuthorDateDeltaMinFilter.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

from varats.gui import icons_rc


class Ui_AuthorDateDeltaMinFilter(object):

    def setupUi(self, AuthorDateDeltaMinFilter):
        AuthorDateDeltaMinFilter.setObjectName("AuthorDateDeltaMinFilter")
        AuthorDateDeltaMinFilter.resize(393, 45)
        self.verticalLayout = QtWidgets.QVBoxLayout(AuthorDateDeltaMinFilter)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(AuthorDateDeltaMinFilter)
        self.label.setEnabled(True)
        self.label.setMinimumSize(QtCore.QSize(200, 0))
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.uiAuthorDateDeltaMin = QtWidgets.QLineEdit(
            AuthorDateDeltaMinFilter
        )
        self.uiAuthorDateDeltaMin.setObjectName("uiAuthorDateDeltaMin")
        self.horizontalLayout.addWidget(self.uiAuthorDateDeltaMin)
        self.uiHelp = QtWidgets.QPushButton(AuthorDateDeltaMinFilter)
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

        self.retranslateUi(AuthorDateDeltaMinFilter)
        QtCore.QMetaObject.connectSlotsByName(AuthorDateDeltaMinFilter)

    def retranslateUi(self, AuthorDateDeltaMinFilter):
        _translate = QtCore.QCoreApplication.translate
        AuthorDateDeltaMinFilter.setWindowTitle(
            _translate("AuthorDateDeltaMinFilter", "Form")
        )
        self.label.setText(
            _translate("AuthorDateDeltaMinFilter", "AuthorDateDelta Minumum")
        )
        self.uiHelp.setToolTip(_translate("AuthorDateDeltaMinFilter", "Help"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    AuthorDateDeltaMinFilter = QtWidgets.QWidget()
    ui = Ui_AuthorDateDeltaMinFilter()
    ui.setupUi(AuthorDateDeltaMinFilter)
    AuthorDateDeltaMinFilter.show()
    sys.exit(app.exec_())
