import random
import logging

from avalon.vendor.Qt import QtWidgets
from avalon.vendor import qtawesome
import colorbleed.maya.lib as lib

from . import commands


class App(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.log = logging.getLogger(__name__)

        self.setWindowTitle("Assign Look 1.0")
        self.resize(300, 300)

        self.apply_button = None
        self.refresh_button = None
        self.random_button = None
        self.list_view = None

        self.setup_ui()
        self.apply_settings()

    def setup_ui(self):
        """Build the UI"""

        main_layout = QtWidgets.QVBoxLayout()
        list_view = QtWidgets.QListWidget()
        apply_box = QtWidgets.QHBoxLayout()
        apply_button = QtWidgets.QPushButton("Apply")

        refresh_icon = qtawesome.icon("fa.refresh", color="white")
        refresh_button = QtWidgets.QPushButton(refresh_icon, "")
        refresh_button.setFixedWidth(25)

        apply_box.addWidget(apply_button)
        apply_box.addWidget(refresh_button)

        main_layout.addWidget(list_view)
        main_layout.addLayout(apply_box)

        self.apply_button = apply_button
        self.refresh_button = refresh_button
        self.list_view = list_view

        self.setLayout(main_layout)

    def apply_settings(self):
        """Apply settings and connect buttons to actions"""
        extended = QtWidgets.QAbstractItemView.ExtendedSelection
        self.list_view.setSelectionMode(extended)

        self.apply_button.clicked.connect(self.apply_look)
        self.refresh_button.clicked.connect(self.populate_list_view)

    def _get_selected_looks(self):
        """Get selected names from the list view widget
        Returns:
            list
        """

        looks = []
        selected_indexes = self.list_view.selectedIndexes()
        for index in selected_indexes:
            item = self.list_view.itemFromIndex(index)
            looks.append(item.text())

        return looks

    def populate_list_view(self):
        """Populate the view with the assets found from the selection"""

        # clear list
        self.list_view.clear()

        # create hash for look up
        node_hashes = commands.create_asset_id_hash(commands.selection())
        looks = commands.fetch_looks(node_hashes.keys())
        for look in looks:
            QtWidgets.QListWidgetItem(look, self.list_view)

    def apply_look(self):
        """Apply the look based on the selected looks

        When multiple looks are selected the assignment will be done with
        a random choice to ensure a single look is passed to the nodes
        """

        looks = self._get_selected_looks()
        if not looks:
            self.log.error("No look selected")
            return

        selection = commands.selection()
        look = random.choice(looks)
        lib.assign_look(selection, subset=look)


def main():
    global application
    application = App()
    application.show()


if __name__ == "__main__":
    main()
