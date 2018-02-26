import sys
import logging

from avalon import style
from avalon.tools import lib as tools_lib
from avalon.vendor.Qt import QtWidgets, QtCore

import mayalookassigner.widgets as widgets
import mayalookassigner.commands as commands

module = sys.modules[__name__]
module.window = None


class App(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.log = logging.getLogger(__name__)

        self.setObjectName("lookManager")
        self.setWindowTitle("Look Manager 1.2")
        self.resize(900, 500)

        self.setup_ui()

        self.setup_connections()

    def setup_ui(self):
        """Build the UI"""

        main_layout = QtWidgets.QHBoxLayout()
        splitter = QtWidgets.QSplitter()

        # Assets overview
        asset_outliner = widgets.AssetOutliner()

        # Look manager part
        look_main_widget = QtWidgets.QWidget()
        look_manager_layout = QtWidgets.QVBoxLayout()
        look_manager_layout.setSpacing(10)

        look_outliner = widgets.LookOutliner()  # Database look overview
        queue_widget = widgets.QueueWidget()  # Queue list overview
        queue_widget.stack.setCurrentIndex(0)

        look_manager_layout.addWidget(look_outliner)
        look_manager_layout.addWidget(queue_widget)
        look_main_widget.setLayout(look_manager_layout)

        load_save_buttons_layout = QtWidgets.QHBoxLayout()
        load_queue_btn = QtWidgets.QPushButton("Load Queue from File")
        save_queue_btn = QtWidgets.QPushButton("Save Queue to File")
        load_save_buttons_layout.addWidget(load_queue_btn)
        load_save_buttons_layout.addWidget(save_queue_btn)

        look_manager_layout.addLayout(load_save_buttons_layout)

        # Build up widgets
        splitter.addWidget(asset_outliner)
        splitter.addWidget(look_main_widget)
        main_layout.addWidget(splitter)

        # Set column width
        asset_outliner.view.setColumnWidth(0, 200)
        look_outliner.view.setColumnWidth(0, 200)
        queue_widget.view.setColumnWidth(0, 200)

        # Open widgets
        self.asset_outliner = asset_outliner
        self.look_outliner = look_outliner
        self.queue = queue_widget

        # Open Buttons
        self.save_queue = save_queue_btn
        self.load_queue = load_queue_btn

        self.setLayout(main_layout)

    def setup_connections(self):
        """Connect interactive widgets with actions"""

        self.asset_outliner.selection_changed.connect(
            self.on_asset_selection_changed)

        self.look_outliner.menu_queue_action.connect(self.on_queue_selected)
        self.look_outliner.menu_apply_action.connect(self.on_process_selected)

        self.save_queue.clicked.connect(self.queue.save_queue)
        self.load_queue.clicked.connect(self.queue.load_queue)

    def refresh(self):
        """Refresh the content"""

        # Get all containers and information
        self.asset_outliner.clear()
        found_items = self.asset_outliner.get_all_assets()
        if not found_items:
            self.look_outliner.clear()

    def on_asset_selection_changed(self):
        """Get selected items from asset loader and fill look outliner"""

        items = self.asset_outliner.get_look_from_selected_items()
        self.look_outliner.clear()
        self.look_outliner.add_items(items)

    def on_process_selected(self):
        """Process all selected looks for the selected assets"""

        assets = self.asset_outliner.get_selected_items()
        assert assets, "No assets selected"
        looks = self.look_outliner.get_selected_items()
        items = self.queue.create_items(looks, assets)

        for item in items:
            commands.process_queued_item(item)

    def on_queue_selected(self):
        """Queue all selected looks for the selected assets"""

        assets = self.asset_outliner.get_selected_items()
        assert assets, "No assets selected"
        looks = self.look_outliner.get_selected_items()
        items = self.queue.create_items(looks, assets)

        self.queue.add_items(items)

    def on_process_queued(self):
        """Process all queued items"""
        self.queue.process_items()

    def on_process_selected_queued(self):
        """Apply currently selected looks to currently selected items"""

        items = self.queue.get_selected_items()
        for item in items:
            commands.process_queued_item(item)


def show(root=None, debug=False, parent=None):
    """Display Loader GUI

    Arguments:
        debug (bool, optional): Run loader in debug-mode,
            defaults to False

    """

    try:
        module.window.close()
        del module.window
    except (RuntimeError, AttributeError):
        pass

    with tools_lib.application():
        window = App(parent)
        window.setStyleSheet(style.load_stylesheet())
        window.show()

        module.window = window
