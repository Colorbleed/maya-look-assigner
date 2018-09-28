import sys
import logging

from avalon import style
from avalon.tools import lib
from avalon.vendor.Qt import QtWidgets, QtCore

from maya import cmds
import maya.api.OpenMaya as om

from . import widgets
from . import commands

module = sys.modules[__name__]
module.window = None


class App(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self.log = logging.getLogger(__name__)

        # Store callback references
        self._callbacks = []

        filename = commands.get_workfile()

        self.setObjectName("lookManager")
        self.setWindowTitle("Look Manager 1.3.0 - [{}]".format(filename))
        self.setWindowFlags(QtCore.Qt.Window)
        self.setParent(parent)

        self.resize(750, 500)

        self.setup_ui()

        self.setup_connections()

        # Force refresh check on initialization
        self._on_renderlayer_switch()

    def setup_ui(self):
        """Build the UI"""

        main_layout = QtWidgets.QVBoxLayout(self)
        main_splitter = QtWidgets.QSplitter()
        main_splitter.setStyleSheet("QSplitter{ border: 0px; }")

        # Assets overview
        asset_outliner = widgets.AssetOutliner()

        # Look manager part
        look_manager_widget = QtWidgets.QWidget()
        look_manager_layout = QtWidgets.QVBoxLayout()

        look_splitter = QtWidgets.QSplitter()
        look_splitter.setOrientation(QtCore.Qt.Vertical)

        look_outliner = widgets.LookOutliner()  # Database look overview
        queue_widget = widgets.QueueWidget()  # Queue list overview
        queue_widget.stack.setCurrentIndex(0)

        look_splitter.addWidget(look_outliner)
        look_splitter.addWidget(queue_widget)

        default_buttons = QtWidgets.QHBoxLayout()
        load_queue_btn = QtWidgets.QPushButton("Load Queue from File")
        remove_unused_btn = QtWidgets.QPushButton("Remove Unused Looks")
        default_buttons.addWidget(load_queue_btn)
        default_buttons.addWidget(remove_unused_btn)

        look_manager_layout.addWidget(look_splitter)
        look_manager_layout.addLayout(default_buttons)
        look_manager_widget.setLayout(look_manager_layout)

        look_splitter.setSizes([550, 0])

        status = QtWidgets.QStatusBar()
        status.setSizeGripEnabled(False)
        warn_layer = QtWidgets.QLabel("Current Layer is not "
                                      "defaultRenderLayer")
        warn_layer.setStyleSheet("color: #DD5555; font-weight: bold;")

        footer = QtWidgets.QHBoxLayout()
        footer.addWidget(status)
        footer.addWidget(warn_layer)

        # Build up widgets
        main_splitter.addWidget(asset_outliner)
        main_splitter.addWidget(look_manager_widget)
        main_splitter.setSizes([350, 200])
        main_layout.addWidget(main_splitter)
        main_layout.addLayout(footer)

        # Set column width
        asset_outliner.view.setColumnWidth(0, 200)
        look_outliner.view.setColumnWidth(0, 150)

        # Open widgets
        self.asset_outliner = asset_outliner
        self.look_outliner = look_outliner
        self.queue = queue_widget
        self.look_splitter = look_splitter
        self.status = status
        self.warn_layer = warn_layer

        # Open Buttons
        self.remove_unused = remove_unused_btn
        self.load_queue = load_queue_btn

    def setup_connections(self):
        """Connect interactive widgets with actions"""

        self.asset_outliner.selection_changed.connect(
            self.on_asset_selection_changed)

        self.asset_outliner.refreshed.connect(
            lambda: self.echo("Loaded assets.."))

        self.look_outliner.menu_queue_action.connect(self.on_queue_selected)
        self.look_outliner.menu_apply_action.connect(self.on_process_selected)
        self.queue.on_emptied.connect(self._on_queue_emptied)

        self.remove_unused.clicked.connect(commands.remove_unused_looks)
        self.load_queue.clicked.connect(self.queue.load_queue)

        # Maya renderlayer switch callback
        callback = om.MEventMessage.addEventCallback(
            "renderLayerManagerChange",
            self._on_renderlayer_switch
        )
        self._callbacks.append(callback)

    def closeEvent(self, event):

        # Delete callbacks
        for callback in self._callbacks:
            om.MMessage.removeCallback(callback)

        return super(App, self).closeEvent(event)

    def _on_renderlayer_switch(self, *args):

        layer = cmds.editRenderLayerGlobals(query=True,
                                            currentRenderLayer=True)
        if layer != "defaultRenderLayer":
            self.warn_layer.show()
        else:
            self.warn_layer.hide()

    def echo(self, message):
        self.log.info(message)
        self.status.showMessage(message, 1000)

    def refresh(self):
        """Refresh the content"""

        # Get all containers and information
        self.asset_outliner.clear()
        found_items = self.asset_outliner.get_all_assets()
        if not found_items:
            self.look_outliner.clear()

    def on_asset_selection_changed(self):
        """Get selected items from asset loader and fill look outliner"""

        items = self.asset_outliner.get_selected_items()
        self.look_outliner.clear()
        self.look_outliner.add_items(items)

    def on_process_selected(self):
        """Process all selected looks for the selected assets"""

        assets = self.asset_outliner.get_selected_items()
        assert assets, "No assets selected"
        looks = self.look_outliner.get_selected_items()
        items = self.queue.create_items(looks, assets)

        self.echo("Assigning selected..")
        for item in items:
            commands.process_queued_item(item)

    def on_queue_selected(self):
        """Queue all selected looks for the selected assets"""

        assets = self.asset_outliner.get_selected_items()
        assert assets, "No assets selected"
        looks = self.look_outliner.get_selected_items()
        items = self.queue.create_items(looks, assets)

        self.queue.add_items(items)
        self.look_splitter.setSizes([250, 250])

    def on_process_queued(self):
        """Process all queued items"""
        self.queue.process_items()

    def on_process_selected_queued(self):
        """Apply currently selected looks to currently selected items"""

        items = self.queue.get_selected_items()
        for item in items:
            commands.process_queued_item(item)

    def _on_queue_emptied(self):
        self.look_splitter.setSizes([500, 0])


def show():
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

    # Get Maya main window
    top_level_widgets = QtWidgets.QApplication.topLevelWidgets()
    mainwindow = next(widget for widget in top_level_widgets
                      if widget.objectName() == "MayaWindow")

    with lib.application():
        window = App(parent=mainwindow)
        window.setStyleSheet(style.load_stylesheet())
        window.show()

        module.window = window
