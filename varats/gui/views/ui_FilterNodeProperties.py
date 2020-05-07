# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'FilterNodeProperties.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_FilterNodeProperties(object):

    def setupUi(self, FilterNodeProperties):
        FilterNodeProperties.setObjectName("FilterNodeProperties")
        FilterNodeProperties.resize(266, 84)
        self.verticalLayout = QtWidgets.QVBoxLayout(FilterNodeProperties)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtWidgets.QLabel(FilterNodeProperties)
        self.label.setMinimumSize(QtCore.QSize(200, 0))
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.uiName = QtWidgets.QLineEdit(FilterNodeProperties)
        self.uiName.setReadOnly(True)
        self.uiName.setObjectName("uiName")
        self.horizontalLayout.addWidget(self.uiName)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label_2 = QtWidgets.QLabel(FilterNodeProperties)
        self.label_2.setMinimumSize(QtCore.QSize(200, 0))
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_2.addWidget(self.label_2)
        self.uiComment = QtWidgets.QLineEdit(FilterNodeProperties)
        self.uiComment.setMaxLength(150)
        self.uiComment.setObjectName("uiComment")
        self.horizontalLayout_2.addWidget(self.uiComment)
        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.retranslateUi(FilterNodeProperties)
        QtCore.QMetaObject.connectSlotsByName(FilterNodeProperties)

    def retranslateUi(self, FilterNodeProperties):
        _translate = QtCore.QCoreApplication.translate
        FilterNodeProperties.setWindowTitle(
            _translate("FilterNodeProperties", "Form")
        )
        self.label.setText(_translate("FilterNodeProperties", "Name"))
        self.uiName.setToolTip(
            _translate("FilterNodeProperties", "Type of the node")
        )
        self.label_2.setText(_translate("FilterNodeProperties", "Comment"))
        self.uiComment.setToolTip(
            _translate(
                "FilterNodeProperties",
                "Arbitrary user comment that describes the node"
            )
        )


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    FilterNodeProperties = QtWidgets.QWidget()
    ui = Ui_FilterNodeProperties()
    ui.setupUi(FilterNodeProperties)
    FilterNodeProperties.show()
    sys.exit(app.exec_())
