# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'FilterProperties.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_FilterProperties(object):

    def setupUi(self, FilterProperties):
        FilterProperties.setObjectName("FilterProperties")
        FilterProperties.resize(289, 255)
        self.verticalLayout = QtWidgets.QVBoxLayout(FilterProperties)
        self.verticalLayout.setObjectName("verticalLayout")
        self.scrollArea = QtWidgets.QScrollArea(FilterProperties)
        self.scrollArea.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scrollArea.setLineWidth(0)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 277, 243))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(
            self.scrollAreaWidgetContents
        )
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_3.setSpacing(0)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.uiFilterProperties = QtWidgets.QGroupBox(
            self.scrollAreaWidgetContents
        )
        self.uiFilterProperties.setObjectName("uiFilterProperties")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.uiFilterProperties)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.layoutNode = QtWidgets.QHBoxLayout()
        self.layoutNode.setObjectName("layoutNode")
        self.verticalLayout_2.addLayout(self.layoutNode)
        self.layoutNodeSpec = QtWidgets.QHBoxLayout()
        self.layoutNodeSpec.setObjectName("layoutNodeSpec")
        self.verticalLayout_2.addLayout(self.layoutNodeSpec)
        self.layoutNodeWarning = QtWidgets.QHBoxLayout()
        self.layoutNodeWarning.setObjectName("layoutNodeWarning")
        self.verticalLayout_2.addLayout(self.layoutNodeWarning)
        spacerItem = QtWidgets.QSpacerItem(
            20, 40, QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Expanding
        )
        self.verticalLayout_2.addItem(spacerItem)
        self.verticalLayout_3.addWidget(self.uiFilterProperties)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.verticalLayout.addWidget(self.scrollArea)

        self.retranslateUi(FilterProperties)
        QtCore.QMetaObject.connectSlotsByName(FilterProperties)

    def retranslateUi(self, FilterProperties):
        _translate = QtCore.QCoreApplication.translate
        FilterProperties.setWindowTitle(_translate("FilterProperties", "Form"))
        self.uiFilterProperties.setTitle(
            _translate("FilterProperties", "Properties")
        )


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    FilterProperties = QtWidgets.QWidget()
    ui = Ui_FilterProperties()
    ui.setupUi(FilterProperties)
    FilterProperties.show()
    sys.exit(app.exec_())
