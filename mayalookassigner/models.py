from collections import defaultdict
from avalon.vendor.Qt import QtCore
from avalon.tools.cbsceneinventory import model, proxy


class ContainerModel(model.TreeModel):

    COLUMNS = ["objectName"]

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
            print item["asset"]
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

        return super(ContainerModel, self).data(index, role)


class FlatModel(model.TreeModel):

    COLUMNS = ["subset", "match"]

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
            item_node = model.Node()
            count = len(assets)
            item_node["version"] = {asset["asset"]: asset["version"]
                                    for asset in assets}

            item_node["subset"] = subset
            item_node["match"] = count
            item_node["assets"] = [asset["asset"] for asset in assets]

            self.add_child(item_node)

        self.endResetModel()


class LookQueueModel(ContainerModel):
    COLUMNS = ["asset", "subset", "version", "new"]
    # TODO: implement version widget?

    def data(self, index, role):

        if not index.isValid():
            return

        if role == model.TreeModel.NodeRole:
            node = index.internalPointer()
            return node

        return super(ContainerModel, self).data(index, role)
