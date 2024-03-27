"""Project file for the feature performance case study collection."""
import typing as tp

import benchbuild as bb
from benchbuild.utils.cmd import make, git
from benchbuild.utils.settings import get_number_of_jobs
from plumbum import local

from varats.containers.containers import get_base_image, ImageBase
from varats.paper.paper_config import project_filter_generator
from varats.project.project_domain import ProjectDomains
from varats.project.project_util import (
    ProjectBinaryWrapper,
    BinaryType,
    get_local_project_git_path,
    verify_binaries,
)
from varats.project.varats_project import VProject
from varats.utils.git_util import RevisionBinaryMap, ShortCommitHash
from varats.utils.settings import bb_cfg


class WC(VProject):
    """Test project for feature performance case studies."""

    NAME = 'wc'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/coreutils/coreutils.git",
            local="wc",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("wc")
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt',
        'install',
        '-y',
        'autoconf',
        'autopoint',
        'wget',
        'gettext',
        'texinfo',
        'rsync',
        'automake',
        'autotools-dev',
        'pkg-config',
        'gperf',
        'bison',
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(WC.NAME))

        binary_map.specify_binary("src/wc", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        wc_source = local.path(self.source_of(self.primary_source))
        cc_compiler = bb.compiler.cc(self)

        with local.cwd(wc_source):
            git("submodule", "init")
            git("submodule", "update")
            with local.env(CC=str(cc_compiler), FORCE_UNSAFE_CONFIGURE=1):
                bb.watch(local["./bootstrap"])()
                bb.watch(local["./configure"])("--disable-gcc-warnings")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
            verify_binaries(self)


class LS(VProject):
    """Test project for feature performance case studies."""

    NAME = 'ls'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/coreutils/coreutils.git",
            local="ls",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("ls")
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt',
        'install',
        '-y',
        'autoconf',
        'autopoint',
        'wget',
        'gettext',
        'texinfo',
        'rsync',
        'automake',
        'autotools-dev',
        'pkg-config',
        'gperf',
        'bison',
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(LS.NAME))

        binary_map.specify_binary("src/ls", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        wc_source = local.path(self.source_of(self.primary_source))
        cc_compiler = bb.compiler.cc(self)

        with local.cwd(wc_source):
            git("submodule", "init")
            git("submodule", "update")
            with local.env(CC=str(cc_compiler), FORCE_UNSAFE_CONFIGURE=1):
                bb.watch(local["./bootstrap"])()
                bb.watch(local["./configure"])("--disable-gcc-warnings")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
            verify_binaries(self)


class CAT(VProject):
    """Test project for feature performance case studies."""

    NAME = 'cat'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/coreutils/coreutils.git",
            local="cat",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("cat")
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt',
        'install',
        '-y',
        'autoconf',
        'autopoint',
        'wget',
        'gettext',
        'texinfo',
        'rsync',
        'automake',
        'autotools-dev',
        'pkg-config',
        'gperf',
        'bison',
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(CAT.NAME))

        binary_map.specify_binary("src/cat", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        wc_source = local.path(self.source_of(self.primary_source))
        cc_compiler = bb.compiler.cc(self)

        with local.cwd(wc_source):
            git("submodule", "init")
            git("submodule", "update")
            with local.env(CC=str(cc_compiler), FORCE_UNSAFE_CONFIGURE=1):
                bb.watch(local["./bootstrap"])()
                bb.watch(local["./configure"])("--disable-gcc-warnings")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
            verify_binaries(self)


class CP(VProject):
    """Test project for feature performance case studies."""

    NAME = 'cp'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/coreutils/coreutils.git",
            local="cp",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("cp")
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt',
        'install',
        '-y',
        'autoconf',
        'autopoint',
        'wget',
        'gettext',
        'texinfo',
        'rsync',
        'automake',
        'autotools-dev',
        'pkg-config',
        'gperf',
        'bison',
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(CP.NAME))

        binary_map.specify_binary("src/cp", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        wc_source = local.path(self.source_of(self.primary_source))
        cc_compiler = bb.compiler.cc(self)

        with local.cwd(wc_source):
            git("submodule", "init")
            git("submodule", "update")
            with local.env(CC=str(cc_compiler), FORCE_UNSAFE_CONFIGURE=1):
                bb.watch(local["./bootstrap"])()
                bb.watch(local["./configure"])("--disable-gcc-warnings")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
            verify_binaries(self)


class WHOAMI(VProject):
    """Test project for feature performance case studies."""

    NAME = 'whoami'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/coreutils/coreutils.git",
            local="whoami",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("whoami")
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt',
        'install',
        '-y',
        'autoconf',
        'autopoint',
        'wget',
        'gettext',
        'texinfo',
        'rsync',
        'automake',
        'autotools-dev',
        'pkg-config',
        'gperf',
        'bison',
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(WHOAMI.NAME))

        binary_map.specify_binary("src/whoami", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        wc_source = local.path(self.source_of(self.primary_source))
        cc_compiler = bb.compiler.cc(self)

        with local.cwd(wc_source):
            git("submodule", "init")
            git("submodule", "update")
            with local.env(CC=str(cc_compiler), FORCE_UNSAFE_CONFIGURE=1):
                bb.watch(local["./bootstrap"])()
                bb.watch(local["./configure"])("--disable-gcc-warnings")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
            verify_binaries(self)


class DD(VProject):
    """Test project for feature performance case studies."""

    NAME = 'dd'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/coreutils/coreutils.git",
            local="dd",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("dd")
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt',
        'install',
        '-y',
        'autoconf',
        'autopoint',
        'wget',
        'gettext',
        'texinfo',
        'rsync',
        'automake',
        'autotools-dev',
        'pkg-config',
        'gperf',
        'bison',
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(DD.NAME))

        binary_map.specify_binary("src/dd", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        wc_source = local.path(self.source_of(self.primary_source))
        cc_compiler = bb.compiler.cc(self)

        with local.cwd(wc_source):
            git("submodule", "init")
            git("submodule", "update")
            with local.env(CC=str(cc_compiler), FORCE_UNSAFE_CONFIGURE=1):
                bb.watch(local["./bootstrap"])()
                bb.watch(local["./configure"])("--disable-gcc-warnings")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
            verify_binaries(self)


class FOLD(VProject):
    """Test project for feature performance case studies."""

    NAME = 'fold'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/coreutils/coreutils.git",
            local="fold",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("fold")
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt',
        'install',
        '-y',
        'autoconf',
        'autopoint',
        'wget',
        'gettext',
        'texinfo',
        'rsync',
        'automake',
        'autotools-dev',
        'pkg-config',
        'gperf',
        'bison',
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(FOLD.NAME))

        binary_map.specify_binary("src/fold", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        wc_source = local.path(self.source_of(self.primary_source))
        cc_compiler = bb.compiler.cc(self)

        with local.cwd(wc_source):
            git("submodule", "init")
            git("submodule", "update")
            with local.env(CC=str(cc_compiler), FORCE_UNSAFE_CONFIGURE=1):
                bb.watch(local["./bootstrap"])()
                bb.watch(local["./configure"])("--disable-gcc-warnings")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
            verify_binaries(self)


class JOIN(VProject):
    """Test project for feature performance case studies."""

    NAME = 'join'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/coreutils/coreutils.git",
            local="join",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("join")
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt',
        'install',
        '-y',
        'autoconf',
        'autopoint',
        'wget',
        'gettext',
        'texinfo',
        'rsync',
        'automake',
        'autotools-dev',
        'pkg-config',
        'gperf',
        'bison',
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(JOIN.NAME))

        binary_map.specify_binary("src/join", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        wc_source = local.path(self.source_of(self.primary_source))
        cc_compiler = bb.compiler.cc(self)

        with local.cwd(wc_source):
            git("submodule", "init")
            git("submodule", "update")
            with local.env(CC=str(cc_compiler), FORCE_UNSAFE_CONFIGURE=1):
                bb.watch(local["./bootstrap"])()
                bb.watch(local["./configure"])("--disable-gcc-warnings")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
            verify_binaries(self)


class KILL(VProject):
    """Test project for feature performance case studies."""

    NAME = 'kill'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/coreutils/coreutils.git",
            local="kill",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("kill")
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt',
        'install',
        '-y',
        'autoconf',
        'autopoint',
        'wget',
        'gettext',
        'texinfo',
        'rsync',
        'automake',
        'autotools-dev',
        'pkg-config',
        'gperf',
        'bison',
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(KILL.NAME))

        binary_map.specify_binary("src/kill", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        wc_source = local.path(self.source_of(self.primary_source))
        cc_compiler = bb.compiler.cc(self)

        with local.cwd(wc_source):
            git("submodule", "init")
            git("submodule", "update")
            with local.env(CC=str(cc_compiler), FORCE_UNSAFE_CONFIGURE=1):
                bb.watch(local["./bootstrap"])()
                bb.watch(local["./configure"])("--disable-gcc-warnings")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
            verify_binaries(self)


class UNIQ(VProject):
    """Test project for feature performance case studies."""

    NAME = 'uniq'
    GROUP = 'c_projects'
    DOMAIN = ProjectDomains.UNIX_TOOLS

    SOURCE = [
        bb.source.Git(
            remote="https://github.com/coreutils/coreutils.git",
            local="uniq",
            refspec="origin/HEAD",
            limit=None,
            shallow=False,
            version_filter=project_filter_generator("uniq")
        )
    ]

    CONTAINER = get_base_image(ImageBase.DEBIAN_10).run(
        'apt',
        'install',
        '-y',
        'autoconf',
        'autopoint',
        'wget',
        'gettext',
        'texinfo',
        'rsync',
        'automake',
        'autotools-dev',
        'pkg-config',
        'gperf',
        'bison',
    )

    @staticmethod
    def binaries_for_revision(
        revision: ShortCommitHash  # pylint: disable=W0613
    ) -> tp.List[ProjectBinaryWrapper]:
        binary_map = RevisionBinaryMap(get_local_project_git_path(UNIQ.NAME))

        binary_map.specify_binary("src/uniq", BinaryType.EXECUTABLE)

        return binary_map[revision]

    def run_tests(self) -> None:
        pass

    def compile(self) -> None:
        """Compile the project."""
        wc_source = local.path(self.source_of(self.primary_source))
        cc_compiler = bb.compiler.cc(self)

        with local.cwd(wc_source):
            git("submodule", "init")
            git("submodule", "update")
            with local.env(CC=str(cc_compiler), FORCE_UNSAFE_CONFIGURE=1):
                bb.watch(local["./bootstrap"])()
                bb.watch(local["./configure"])("--disable-gcc-warnings")

            bb.watch(make)("-j", get_number_of_jobs(bb_cfg()))
            verify_binaries(self)
