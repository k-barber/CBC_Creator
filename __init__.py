from calibre.customize import InterfaceActionBase

class CBC_Creator(InterfaceActionBase):
    name                = 'CBC Creator'
    description         = 'Creates a CBC file from CBZ or CB7 files'
    supported_platforms = ['windows', 'osx', 'linux']
    author              = 'Kristopher Barber'
    version             = (1, 0, 0)
    minimum_calibre_version = (5, 0, 0)
    actual_plugin       = 'calibre_plugins.CBC_Creator.ui:CBCCreatorInterface'

    def is_customizable(self):
        return False
