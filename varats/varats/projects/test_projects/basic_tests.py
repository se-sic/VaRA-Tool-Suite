"""Small test project to run basic vara tests."""
import benchbuild as bb
from plumbum import local


class BasicTests(bb.Project):  # type: ignore
    """
    Basic tests:

    Different small test files
    """

    NAME = 'basic-tests'
    DOMAIN = 'testing'
    GROUP = 'test_projects'

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/se-passau/vara-perf-tests.git",
            local="basic-tests",
            limit=1,
            refspec="origin/HEAD"
        )
    ]

    test_files = [
        "if.cpp", "loop.cpp", "switch.cpp", "exitOutsideRegion.cpp",
        "overlappingRegions.cpp", "returnInRegion.cpp"
    ]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        source = local.path(self.source_of_primary)

        clang = bb.compiler.cxx(self)
        with local.cwd(source + "/basic-tests"):
            for test_file in self.test_files:
                bb.watch(clang)(test_file, "-o", test_file.replace('.cpp', ''))
