
if False:
    get_icons = get_resources = None

from calibre.gui2.actions import InterfaceAction
from calibre_plugins.CBC_Creator.main import CBCConverter


class CBCCreatorInterface(InterfaceAction):

    name = "CBC Creator"
    action_spec = (
        "Convert to CBC",
        None,
        "Convert the selected Books to CBC format",
        "Ctrl+Shift+C",
    )

    def genesis(self):
        icon = get_icons("images/CBC_File.png")
        self.qaction.setIcon(icon)
        self.qaction.triggered.connect(self.create)

    def create(self):
        d = CBCConverter(self.gui)
        d.convert_books()
