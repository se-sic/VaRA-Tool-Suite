"""An ExampleView that shows how graphs can be shown with VaRA-TS."""

from PyQt5.QtWidgets import QWidget

from varats.gui.views.ui_ExampleView import Ui_example_view


class ExampleView(QWidget, Ui_example_view):
    """Example data representation."""

    def __init__(self):
        super().__init__()

        self.setupUi(self)
