# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'FilterUnaryWarning.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_FilterUnaryWarning(object):

    def setupUi(self, FilterUnaryWarning):
        FilterUnaryWarning.setObjectName("FilterUnaryWarning")
        FilterUnaryWarning.resize(716, 121)
        self.verticalLayout = QtWidgets.QVBoxLayout(FilterUnaryWarning)
        self.verticalLayout.setObjectName("verticalLayout")
        self.uiWarningLabel = QtWidgets.QLabel(FilterUnaryWarning)
        self.uiWarningLabel.setEnabled(True)
        self.uiWarningLabel.setWordWrap(True)
        self.uiWarningLabel.setObjectName("uiWarningLabel")
        self.verticalLayout.addWidget(self.uiWarningLabel)

        self.retranslateUi(FilterUnaryWarning)
        QtCore.QMetaObject.connectSlotsByName(FilterUnaryWarning)

    def retranslateUi(self, FilterUnaryWarning):
        _translate = QtCore.QCoreApplication.translate
        FilterUnaryWarning.setWindowTitle(
            _translate("FilterUnaryWarning", "Form")
        )
        self.uiWarningLabel.setText(
            _translate(
                "FilterUnaryWarning",
                "<html><head/><body><p><span style=\" font-weight:600;\">Currently, this filter applies to source and target, therefore, only interactions where both satisfy the filter are included.</span></p></body></html>"
            )
        )


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    FilterUnaryWarning = QtWidgets.QWidget()
    ui = Ui_FilterUnaryWarning()
    ui.setupUi(FilterUnaryWarning)
    FilterUnaryWarning.show()
    sys.exit(app.exec_())
