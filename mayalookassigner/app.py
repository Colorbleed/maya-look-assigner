import sys
import time
import logging
from collections import defaultdict

from avalon import style, io
from avalon.tools import lib
from avalon.vendor.Qt import QtWidgets, QtCore

from maya import cmds
import maya.api.OpenMaya as om

from . import widgets
from . import commands

module = sys.modules[__name__]
module.window = None


def create_items(looks, asset_items):
    """Create a queue item based on the selection

    Args:
        looks (list): list of dicts with document information
        assets (list): list of dicts with document information

    Returns:
        list: collection of look and asset data in dictionaries

    """

    # Collect the looks we want to apply (by name)
    subsets = {look["subset"] for look in looks}

    # Collect the asset item entries per asset
    # and collect the namespaces we'd like to apply
    # todo: can we get the combined namespace filter an easier way?
    assets = dict()
    asset_namespaces = defaultdict(set)
    for item in asset_items:
        asset = item["asset"]["name"]
        asset_namespaces[asset].add(item.get("namespace"))

        if asset in assets:
            continue

        assets[asset] = item

    # Set the namespaces to assign per asset
    for asset in assets:
        namespaces = asset_namespaces[asset]
        if None in namespaces:
            # When None is present the all namespaces should be assigned.
            namespaces = None

        assets[asset]["namespaces"] = namespaces

    # Generate a queue item for every asset/look combination
    items = []
    for asset in assets.values():

        # Iterate the available looks for the asset
        for look in asset["looks"]:
            if look["name"] in subsets:

                # Get the latest version of this asset's look subset
                version = io.find_one({"type": "version",
                                       "parent": look["_id"]},
                                      sort=[("name", -1)])

                items.append({"asset": asset["asset"],
                              "subset": look,
                              "namespaces": asset["namespaces"],
                              "version": version})

    return items


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

        # Assets (left)
        asset_outliner = widgets.AssetOutliner()

        # Looks (right)
        looks_widget = QtWidgets.QWidget()
        looks_layout = QtWidgets.QVBoxLayout(looks_widget)

        look_outliner = widgets.LookOutliner()  # Database look overview

        assign_selected = QtWidgets.QCheckBox("Assign to selected only")
        assign_selected.setToolTip("Whether to assign only to selected nodes "
                                   "or to the full asset")
        remove_unused_btn = QtWidgets.QPushButton("Remove Unused Looks")

        looks_layout.addWidget(look_outliner)
        looks_layout.addWidget(assign_selected)
        looks_layout.addWidget(remove_unused_btn)

        # Footer
        status = QtWidgets.QStatusBar()
        status.setSizeGripEnabled(False)
        status.setFixedHeight(25)
        warn_layer = QtWidgets.QLabel("Current Layer is not "
                                      "defaultRenderLayer")
        warn_layer.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        warn_layer.setStyleSheet("color: #DD5555; font-weight: bold;")
        warn_layer.setFixedHeight(25)

        footer = QtWidgets.QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.addWidget(status)
        footer.addWidget(warn_layer)

        # Build up widgets
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_splitter = QtWidgets.QSplitter()
        main_splitter.setStyleSheet("QSplitter{ border: 0px; }")
        main_splitter.addWidget(asset_outliner)
        main_splitter.addWidget(looks_widget)
        main_splitter.setSizes([350, 200])
        main_layout.addWidget(main_splitter)
        main_layout.addLayout(footer)

        # Set column width
        asset_outliner.view.setColumnWidth(0, 200)
        look_outliner.view.setColumnWidth(0, 150)

        # Open widgets
        self.asset_outliner = asset_outliner
        self.look_outliner = look_outliner
        self.status = status
        self.warn_layer = warn_layer

        # Buttons
        self.remove_unused = remove_unused_btn
        self.assign_selected = assign_selected

    def setup_connections(self):
        """Connect interactive widgets with actions"""

        self.asset_outliner.selection_changed.connect(
            self.on_asset_selection_changed)

        self.asset_outliner.refreshed.connect(
            lambda: self.echo("Loaded assets.."))

        self.look_outliner.menu_apply_action.connect(self.on_process_selected)
        self.remove_unused.clicked.connect(commands.remove_unused_looks)

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
        """Callback that updates on Maya renderlayer switch"""

        layer = cmds.editRenderLayerGlobals(query=True,
                                            currentRenderLayer=True)
        if layer != "defaultRenderLayer":
            self.warn_layer.show()
        else:
            self.warn_layer.hide()

    def echo(self, message):
        self.status.showMessage(message, 1500)

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
        items = create_items(looks, assets)

        selected = self.assign_selected.isChecked()

        # Collect all nodes by hash (optimization)
        if not selected:
            nodes = cmds.ls(dag=True,  long=True)
        else:
            nodes = commands.get_selected_nodes()
        id_nodes = commands.create_asset_id_hash(nodes)

        start = time.time()
        for i, item in enumerate(items):

            nodes = id_nodes.get(str(item["asset"]["_id"]))

            # If namespaces are selected and *not* the top entry we should
            # filter to assign only to those namespaces.
            namespaces = item.get("namespaces")
            if namespaces:
                nodes = [node for node in nodes if
                         commands.get_namespace_from_node(node) in namespaces]

            asset_name = item["asset"]["name"]
            subset_name = item["subset"]["name"]
            self.echo("({}/{}) Assigning {} to {}\t".format(i+1,
                                                            len(items),
                                                            subset_name,
                                                            asset_name))

            commands.assign_item(item, nodes=nodes)
        end = time.time()

        self.echo("Finished assigning.. ({0:.3f}s)".format(end - start))


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
