# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ExampleView.ui'
#
# Created by: PyQt5 UI code generator 5.12.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_example_view(object):

    def setupUi(self, example_view):
        example_view.setObjectName("example_view")
        example_view.resize(640, 480)
        self.tableView = QtWidgets.QTableView(example_view)
        self.tableView.setGeometry(QtCore.QRect(330, 160, 256, 192))
        self.tableView.setObjectName("tableView")
        self.graphicsView = QtWidgets.QGraphicsView(example_view)
        self.graphicsView.setGeometry(QtCore.QRect(50, 80, 256, 192))
        self.graphicsView.setObjectName("graphicsView")

        self.retranslateUi(example_view)
        QtCore.QMetaObject.connectSlotsByName(example_view)

    def retranslateUi(self, example_view):
        _translate = QtCore.QCoreApplication.translate
        example_view.setWindowTitle(_translate("example_view", "Form"))


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    example_view = QtWidgets.QWidget()
    ui = Ui_example_view()
    ui.setupUi(example_view)
    example_view.show()
    sys.exit(app.exec_())
