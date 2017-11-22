import logging

from avalon.vendor.Qt import QtWidgets, QtCore

from . import commands, models, views, proxy


class App(QtWidgets.QWidget):

    def __init__(self, parent=None):
        QtWidgets.QWidget.__init__(self, parent=parent)

        self._noderole = QtCore.Qt.UserRole + 1

        self.log = logging.getLogger(__name__)

        self.setWindowTitle("Look Manager 1.0")
        self.resize(900, 500)

        self.apply_button = None
        self.refresh_button = None
        self.random_button = None
        self.list_view = None

        self.setup_ui()

        self.setup_connections()

        self.refresh()

    def refresh(self):
        """Refresh the content"""

        # Get all containers and information
        items = commands.get_selected_assets()
        self.container_model.clear()
        if items:
            # Add all found containers to the models for display
            self.container_model.add_items(items)

    def setup_ui(self):
        """Build the UI"""

        main_layout = QtWidgets.QHBoxLayout()
        splitter = QtWidgets.QSplitter()

        # Container overview
        container_widget = QtWidgets.QWidget()
        container_title = self._create_label("Assets")
        container_layout = QtWidgets.QVBoxLayout()

        container_model = models.ContainerModel()
        container_view = views.View()
        container_view.setModel(container_model)
        container_view.setContextMenuPolicy(QtCore.Qt.NoContextMenu)

        from_selection_btn = QtWidgets.QPushButton("Get Looks From Selection")
        from_all_asset_btn = QtWidgets.QPushButton("Get Looks From All Assets")

        container_layout.addWidget(container_title)
        container_layout.addWidget(from_selection_btn)
        container_layout.addWidget(from_all_asset_btn)
        container_layout.addWidget(container_view)

        # Add container view
        container_widget.setLayout(container_layout)
        splitter.addWidget(container_widget)

        # look manager layout
        look_views_widget = QtWidgets.QWidget()
        look_views_layout = QtWidgets.QVBoxLayout()

        # Looks from database
        documents_title = self._create_label("Available looks")
        documents_title.setAlignment(QtCore.Qt.AlignCenter)
        document_model = models.FlatModel()
        document_view = views.View()
        document_view.setModel(document_model)
        document_view.setMinimumHeight(230)

        look_views_layout.addWidget(documents_title)
        look_views_layout.addWidget(document_view)

        # Turn off queue at start, show this widget
        queue_off_message = QtWidgets.QLabel(
            "Queue is empty, add items to the queue to active it")
        queue_off_message.setAlignment(QtCore.Qt.AlignCenter)
        queue_off_message.setStyleSheet("font-size: 12px;")

        # Queue view
        queue_title = self._create_label("Queue")
        queue_title.setAlignment(QtCore.Qt.AlignCenter)
        queue_model = models.LookQueueModel()
        queue_view = views.View()
        queue_view.setModel(queue_model)

        queue_widgets = QtWidgets.QStackedWidget()
        queue_widgets.addWidget(queue_off_message)
        queue_widgets.addWidget(queue_view)

        look_views_layout.addWidget(queue_title)
        look_views_layout.addWidget(queue_widgets)

        # Method buttons
        method_buttons_layout = QtWidgets.QHBoxLayout()
        assign_to_selected_btn = QtWidgets.QPushButton("Assign to Selected")
        assign_to_all_btn = QtWidgets.QPushButton("Assign to All")
        remove_unused_btn = QtWidgets.QPushButton("Remove Unused Looks")
        method_buttons_layout.addWidget(assign_to_selected_btn)
        method_buttons_layout.addWidget(assign_to_all_btn)
        method_buttons_layout.addWidget(remove_unused_btn)

        look_views_layout.addLayout(method_buttons_layout)
        look_views_widget.setLayout(look_views_layout)
        splitter.addWidget(look_views_widget)

        main_layout.addWidget(splitter)

        container_view.setColumnWidth(0, 200)  # subset
        document_view.setColumnWidth(0, 200)
        queue_view.setColumnWidth(0, 200)

        self.from_selection_btn = from_selection_btn
        self.from_all_asset_btn = from_all_asset_btn

        self.assign_to_selected_btn = assign_to_selected_btn
        self.assign_to_all_btn = assign_to_all_btn
        self.remove_unused_btn = remove_unused_btn

        self.container_model = container_model
        self.container_view = container_view

        self.document_model = document_model
        self.document_view = document_view

        self.queue_widgets = queue_widgets

        self.queue_model = queue_model
        self.queue_view = queue_view

        self.setLayout(main_layout)

    def setup_connections(self):
        """Connect interactive widgets with actions"""

        container_selection_model = self.container_view.selectionModel()
        container_selection_model.selectionChanged.connect(
            self._on_container_selection_changed)

        # Buttons
        self.from_selection_btn.clicked.connect(self.refresh)
        self.from_all_asset_btn.clicked.connect(self._get_all_assets)
        self.assign_to_all_btn.clicked.connect(self._apply_from_queue)
        self.assign_to_selected_btn.clicked.connect(self._apply_from_selection)
        self.remove_unused_btn.clicked.connect(commands.remove_unused_looks)

        # Set menu triggers
        self.document_view.customContextMenuRequested.connect(
            self.build_document_menu)

        self.queue_view.customContextMenuRequested.connect(
            self.build_queue_menu)

    def build_document_menu(self, pos):
        """Build RMB menu for document view"""

        active = self.document_view.currentIndex()  # index under mouse
        active = active.sibling(active.row(), 0)  # get first column
        globalpos = self.document_view.viewport().mapToGlobal(pos)

        if not active.isValid():
            return

        menu = QtWidgets.QMenu(self.document_view)

        # Direct assignment
        apply_action = QtWidgets.QAction(menu, text="Assign Directly")
        apply_action.triggered.connect(self._apply_from_selection)

        queue_action = QtWidgets.QAction(menu, text="Queue Assignment")
        queue_action.triggered.connect(self._add_queue_items)

        menu.addAction(apply_action)
        menu.addAction(queue_action)

        menu.exec_(globalpos)

    def build_queue_menu(self, pos):

        active = self.queue_view.currentIndex()  # index under mouse
        active = active.sibling(active.row(), 0)  # get first column
        globalpos = self.queue_view.viewport().mapToGlobal(pos)

        menu = QtWidgets.QMenu(self.document_view)

        if active.isValid():
            apply_action = QtWidgets.QAction(menu, text="Apply looks")
            apply_action.triggered.connect(self._apply_from_queue)

            remove_action = QtWidgets.QAction(menu, text="Removed Queue")
            remove_action.triggered.connect(self._remove_selected_queued)

            menu.addAction(apply_action)
            menu.addAction(remove_action)
            menu.addSeparator()

        clear_action = QtWidgets.QAction(menu, text="Clear Queue")
        clear_action.triggered.connect(self._clear_queue)

        menu.addAction(clear_action)

        menu.exec_(globalpos)

    def _create_label(self, text):
        """Lazy function to create a label"""

        title = QtWidgets.QLabel(text)
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("font-weight: bold; font-size: 12px")

        return title

    def _on_container_selection_changed(self):

        all_documents = []

        indices = self.container_view.get_indices()
        for idx in indices:
            data = idx.data(self._noderole)
            if data is None:
                continue

            _id = data.get("_id", None)
            if not _id:
                continue

            all_documents.extend(data.get("looks", []))

        self.document_model.clear()
        self.document_model.add_items(all_documents)

    def _get_all_assets(self):

        items = commands.get_all_assets()
        self.container_model.clear()
        self.container_view.setVisible(False)
        self.container_model.add_items(items)
        self.container_view.setVisible(True)

    def _create_queue_items(self):
        """Create a queue item based on the selection"""

        documents = [document.data(self._noderole) for document in
                     self.document_view.get_indices()]
        assert len(documents) > 0, "Please select a look"
        containers = [container.data(self._noderole) for container in
                      self.container_view.get_indices()]

        items = []
        for data in containers:

            asset_name = data["asset"]["name"]
            for doc in documents:
                version = doc["version"].get(asset_name, None)
                if version is None:
                    continue
                items.append({"asset": data["objectName"],
                              "subset": doc["subset"],
                              "version": version["name"],
                              "document": version})

        return items

    def _add_queue_items(self):

        if self.queue_widgets.currentIndex() != 1:
            self.queue_widgets.setCurrentIndex(1)

        items = self._create_queue_items()

        validated = []
        for item in items:
            valid = self._validate_queue_entry(item)
            if valid:
                validated.append(item)

        self.queue_model.add_items(validated)

    def _validate_queue_entry(self, entry):
        """If an entry already exists return false"""

        parent = QtCore.QModelIndex()
        for row in range(self.queue_model.rowCount(parent)):
            idx = self.queue_model.index(row, 0, parent)
            data = idx.data(self._noderole)
            if entry == data:
                self.log.info("Already in queue")
                return False

        return True

    def _get_queued_items(self):
        """Get all queued items in form of dictionaries
        Returns:
            list
        """

        items = []

        parent = QtCore.QModelIndex()
        for row in range(self.queue_model.rowCount(parent)):
            idx = self.queue_model.index(row, 0, parent)
            data = idx.data(self._noderole)
            items.append(data)

        return items

    def _remove_selected_queued(self):
        """Remove selected item(s) from the queue"""

        model_index = QtCore.QModelIndex()

        active = self.queue_view.currentIndex()
        active_row = active.row()

        items = []
        for row in range(self.queue_model.rowCount(model_index)):
            idx = self.queue_model.index(row, 0, model_index)
            index_data = idx.data(self._noderole)
            items.append(index_data)

        items.pop(active_row)

        self.queue_model.clear()
        if not items:
            self.queue_widgets.setCurrentIndex(0)
            return

        self.queue_model.add_items(items)

    def _clear_queue(self):
        self.queue_widgets.setCurrentIndex(0)
        self.queue_model.clear()

    def _apply_from_selection(self):
        items = self._create_queue_items()
        for item in items:
            commands.process_queued_item(item)

    def _apply_from_queue(self):
        """Apply the look based on the queued looks"""

        # Get queued items
        items = self._get_queued_items()
        if not items:
            self.log.error("No look selected")
            return
        for item in items:
            commands.process_queued_item(item)


def main():
    global application
    application = App()
    application.show()


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = App()
    w.show()
    app.exec_()
