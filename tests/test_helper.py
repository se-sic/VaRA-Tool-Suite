"""Small helper classes for testing."""

from benchbuild.project import Project


class EmptyProject(Project):
    NAME = "test_empty"
    DOMAIN = "debug"
    GROUP = "debug"
    SRC_FILE = "none"

    def build(self):
        pass

    def configure(self):
        pass

    def download(self, version=None):
        pass

    def compile(self):
        pass
