from PyQt5.QtWidgets import QTreeView


class DeselectableQTreeView(QTreeView):

    def mousePressEvent(self, event):
        self.selectionModel().clear()
        QTreeView.mousePressEvent(self, event)
