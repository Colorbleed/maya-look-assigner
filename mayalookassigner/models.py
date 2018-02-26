from collections import defaultdict
from avalon.vendor.Qt import QtCore
from avalon.tools.cbsceneinventory import model


class AssetModel(model.TreeModel):

    COLUMNS = ["asset_name"]

    def add_items(self, items):
        """
        Add items to model with needed data
        Args:
            items(list): collection of item data

        Returns:
            None
        """

        self.beginResetModel()

        for item in items:
            item_node = model.Node()
            item_node.update(item)
            self.add_child(item_node)

        self.endResetModel()

    def data(self, index, role):

        if not index.isValid():
            return

        if role == model.TreeModel.NodeRole:
            node = index.internalPointer()
            return node

        if role == QtCore.Qt.DisplayRole:
            node = index.internalPointer()
            return node.get(self.COLUMNS[0], None)

        return super(AssetModel, self).data(index, role)


class LookModel(model.TreeModel):

    COLUMNS = ["subset", "match", "version_name"]

    def add_items(self, items):
        """
        Add items to model with needed data
        Args:
            items(list): collection of item data

        Returns:
            None
        """

        self.beginResetModel()

        subsets = defaultdict(list)
        for item in items:
            subsets[item["subset"]].append(item)

        for subset, assets in sorted(subsets.iteritems()):
            version = assets[0]["version"]

            item_node = model.Node()

            item_node["asset_name"] = assets[0]["asset_name"]
            item_node["subset"] = subset
            item_node["version"] = version
            item_node["version_name"] = version["name"]
            item_node["match"] = len(assets)

            self.add_child(item_node)

        self.endResetModel()


class QueueModel(AssetModel):
    COLUMNS = ["asset_name", "subset", "version_name"]

    def data(self, index, role):

        if not index.isValid():
            return

        if role == model.TreeModel.NodeRole:
            node = index.internalPointer()
            return node

        return super(AssetModel, self).data(index, role)
