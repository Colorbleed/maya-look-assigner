from avalon import api, io

from avalon.vendor.Qt import QtWidgets, QtCore


DEFAULT_COLOR = "#fb9c15"


class View(QtWidgets.QTreeView):
    data_changed = QtCore.Signal()

    def __init__(self, parent=None):
        super(View, self).__init__(parent=parent)

        # view settings
        self.setIndentation(6)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.setSelectionMode(self.ExtendedSelection)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

    def get_indices(self):
        """Get the selected rows"""
        selection_model = self.selectionModel()
        return selection_model.selectedRows()

    def extend_to_children(self, indices):
        """Extend the indices to the children indices.

        Top-level indices are extended to its children indices. Sub-items
        are kept as is.

        :param indices: The indices to extend.
        :type indices: list

        :return: The children indices
        :rtype: list
        """

        subitems = set()
        for i in indices:
            valid_parent = i.parent().isValid()
            if valid_parent and i not in subitems:
                subitems.add(i)
            else:
                # is top level node
                model = i.model()
                rows = model.rowCount(parent=i)
                for row in range(rows):
                    child = model.index(row, 0, parent=i)
                    subitems.add(child)

        return list(subitems)

    def show_version_dialog(self, items):
        """Create a dialog with the available versions for the selected file

        :param items: list of items to run the "set_version" for
        :type items: list

        :returns: None
        """

        active = items[-1]

        # Get available versions for active representation
        representation_id = io.ObjectId(active["representation"])
        representation = io.find_one({"_id": representation_id})
        version = io.find_one({"_id": representation["parent"]})

        versions = io.find({"parent": version["parent"]},
                           sort=[("name", 1)])
        versions = list(versions)

        current_version = active["version"]

        # Get index among the listed versions
        index = len(versions) - 1
        for i, version in enumerate(versions):
            if version["name"] == current_version:
                index = i
                break

        versions_by_label = dict()
        labels = []
        for version in versions:
            label = "v{0:03d}".format(version["name"])
            labels.append(label)
            versions_by_label[label] = version

        label, state = QtWidgets.QInputDialog.getItem(self,
                                                      "Set version..",
                                                      "Set version number "
                                                      "to",
                                                      labels,
                                                      current=index,
                                                      editable=False)
        if not state:
            return

        if label:
            version = versions_by_label[label]["name"]
            for item in items:
                api.update(item, version)
            # refresh model when done
            self.data_changed.emit()

    def _queue_look_assignment(self):
        # get the selected asset(s)
        # get the selected look(s)

        active = self.currentIndex()  # index under mouse
        active = active.sibling(active.row(), 0)  # get first column

        print(active)
