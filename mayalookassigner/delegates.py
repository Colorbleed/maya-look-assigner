from avalon import io
from avalon.vendor.Qt import QtWidgets, QtCore


class VersionDelegate(QtWidgets.QStyledItemDelegate):
    """A delegate that display version integer formatted as version string."""

    def __init__(self, parent=None):
        super(VersionDelegate, self).__init__(parent)
        self._noderole = QtCore.Qt.UserRole + 1

    def _format_version(self, value):
        """Formats integer to displayable version name"""
        return "v{0:03d}".format(value)

    def displayText(self, value, locale):
        assert isinstance(value, int), "Version is not `int`"
        return self._format_version(value)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QComboBox(parent)
        return editor

    def setEditorData(self, editor, index):

        editor.clear()

        # Current value of the index
        value = index.data(QtCore.Qt.DisplayRole)
        assert isinstance(value, int), "Version is not `int`"

        # Add all available versions to the editor
        node = index.data(self._noderole)
        parent_id = node['version_document']['parent']
        versions = io.find({"type": "version", "parent": parent_id},
                           sort=[("name", 1)])
        index = 0
        for i, version in enumerate(versions):
            label = self._format_version(version['name'])
            editor.addItem(label, userData=version)

            if version['name'] == value:
                index = i

        editor.setCurrentIndex(index)

    def setModelData(self, editor, model, index):
        """Apply the integer version back in the model"""
        version = editor.itemData(editor.currentIndex())
        model.setData(index, version['name'])