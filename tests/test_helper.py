"""Small helper classes for testing."""

from benchbuild import Project, source


class EmptyProject(Project):
    NAME = "test_empty"

    DOMAIN = "debug"
    GROUP = "debug"
    SOURCE = [source.nosource()]

    def build(self):
        pass

    def configure(self):
        pass

    def download(self, version=None):
        pass

    def compile(self):
        pass

    def run_tests(self) -> None:
        pass
