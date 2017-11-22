from avalon.vendor.Qt import QtWidgets, QtCore, QtGui


class FamilyFilterProxyModel(QtCore.QSortFilterProxyModel):

    FilterExclude = 0
    FilterInclude = 1
    NodeRole = QtCore.Qt.UserRole + 1

    def __init__(self, method=None, filter=None, parent=None):
        super(FamilyFilterProxyModel, self).__init__(parent)
        self._method = method if method is None else self.FilterExclude
        self._filter = filter or []

    def setFilterMethod(self, value):
        self._method = value

    def setFilterValue(self, value):
        self._filter = value

    def filterAcceptsRow(self, row=0, parent=QtCore.QModelIndex()):

        model = self.sourceModel()
        index = model.index(row, 0, parent=parent)

        # Ensure index is valid
        if not index.isValid() or index is None:
            return True

        # Check if index is top node and if it has any children

        # Get the node data and validate
        node = model.data(index, self.NodeRole)
        family = node.get("family", None)
        if family is None:
            return True

        # We want to keep the families which are not in the list
        return self._filter_family(family)

    def _filter_family(self, family):

        if self._method == self.FilterExclude:
            return family not in self._filter
        elif self._method == self.FilterInclude:
            return family in self._filter
        else:
            raise ValueError("Invalid Filter mode, supported Filter methods "
                             "are: FilterExclude [0] and FilterInclude [1]")
