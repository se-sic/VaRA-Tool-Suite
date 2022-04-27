"""This modules provides the base classes for research tools that allow
developers to setup and configure their own research tool by inheriting and
implementing the base classes ``ResearchTool`` and ``CodeBase``."""
import abc
import typing as tp
from enum import Enum
from pathlib import Path

import distro as distribution
from benchbuild.utils.cmd import apt, pacman

from varats.tools.research_tools.vara_manager import BuildType
from varats.utils.filesystem_util import FolderAlreadyPresentError
from varats.utils.git_commands import (
    get_branches,
    fetch_remote,
    get_tags,
    init_all_submodules,
    update_all_submodules,
    pull_current_branch,
    push_current_branch,
    checkout_branch_or_commit,
    checkout_new_branch,
    download_repo,
    add_remote,
    show_status,
)
from varats.utils.git_util import (
    get_current_branch,
    has_branch,
    has_remote_branch,
    branch_has_upstream,
)
from varats.utils.logger_util import log_without_linesep

if tp.TYPE_CHECKING:
    from varats.containers import containers  # pylint: disable=W0611


class Distro(Enum):
    """Linux distributions supported by the tool suite."""
    value: str

    DEBIAN = "debian"
    ARCH = "arch"
    FEDORA = "fedora"

    @staticmethod
    def get_current_distro() -> tp.Optional['Distro']:
        """Returns the current Linux distribution or None."""
        if distribution.id() == "debian":
            return Distro.DEBIAN
        if distribution.id() == "arch":
            return Distro.ARCH
        if distribution.id() == "fedora":
            return Distro.FEDORA
        return None

    def __str__(self) -> str:
        return str(self.value)


_install_commands = {
    Distro.DEBIAN: "apt install -y",
    Distro.ARCH: "pacman -S --noconfirm",
    Distro.FEDORA: "dnf install"
}

_checker_commands = {Distro.DEBIAN: apt["list"], Distro.ARCH: pacman["-Qi"]}

_expected_check_output = {Distro.DEBIAN: "installed", Distro.ARCH: "Installed"}


class Dependencies:
    """Models the dependencies for a research tool."""

    def __init__(self, dependencies: tp.Dict[Distro, tp.List[str]]):
        self.__dependencies = dependencies

    @property
    def distros(self) -> tp.List[Distro]:
        return list(self.__dependencies.keys())

    def has_dependencies_for_distro(self, distro: Distro) -> bool:
        """
        Check whether the deendency object has any entries for the given distro.

        Args:
            distro: the distro to check

        Returns:
            whether there are any dependencies for the given distro

        Test:
        >>> deps = Dependencies({Distro.DEBIAN: ["foo", "bar"]})
        >>> deps.has_dependencies_for_distro(Distro.DEBIAN)
        True
        >>> deps.has_dependencies_for_distro(Distro.ARCH)
        False
        >>> deps = Dependencies({Distro.DEBIAN: []})
        >>> deps.has_dependencies_for_distro(Distro.DEBIAN)
        False
        """
        return bool(self.__dependencies.get(distro, None))

    def has_all_dependencies_for_distro(self, distro: Distro) -> bool:
        """
        Given a distro, return if all specified dependencies are installed.
        Args:
            distro: the distro tu use

        Returns:
            True if all dependencies are installed and False otherwise
        """
        return len(self.get_missing_dependencies_for_distro(distro)) == 0

    def get_missing_dependencies_for_distro(self,
                                            distro: Distro) -> tp.List[str]:
        """
        Given a distro, return all not installed dependencies.
        Args:
            distro: the distro to use

        Returns:
            a list containing all not installed dependencies
        """
        not_installed: tp.List[str] = []

        if distro not in _checker_commands or \
                distro not in _expected_check_output:
            raise NotImplementedError(
                "Check/Expected commands are currently " +
                f"not implemented for {distro}"
            )

        base_command = _checker_commands[distro]
        for package in self.__dependencies[distro]:
            output = base_command(package)
            output_list = output.split()
            if _expected_check_output[distro] not in output_list:
                not_installed.append(package)
        return not_installed

    def get_install_command(self, distro: Distro) -> str:
        """
        Given a distro, return a command how the dependencies can be installed.
        Args:
            distro: the distro to use

        Returns:
            the command how the dependencies can be installed

        Test:
        >>> deps = Dependencies({Distro.DEBIAN: ["foo", "bar"], \
            Distro.ARCH: ["baz"]})
        >>> deps.get_install_command(Distro.DEBIAN)
        'apt install -y foo bar'
        >>> deps.get_install_command(Distro.ARCH)
        'pacman -S --noconfirm baz'
        """
        return f"{_install_commands[distro]} " \
               f"{' '.join(self.__dependencies[distro])}"


class SubProject():
    """Encapsulates a sub project, e.g., a library or tool, defining how it can
    be downloaded and integrated inside a ``CodeBase``."""

    def __init__(
        self,
        parent_code_base: 'CodeBase',
        name: str,
        URL: str,
        remote: str,
        sub_path: str,
        is_submodule: bool = False
    ):
        self.__name = name
        self.__parent_code_base = parent_code_base
        self.__url = URL
        self.__remote = remote
        self.__sub_path = Path(sub_path)
        self.__is_submodule = is_submodule

    @property
    def name(self) -> str:
        """Name of the sub project."""
        return self.__name

    @property
    def url(self) -> str:
        """Repository URL."""
        return self.__url

    @property
    def remote(self) -> str:
        """Git remote, for interacting with upstream repositories."""
        return self.__remote

    @property
    def path(self) -> Path:
        """
        Path to the sub project folder within a ``CodeBase``.

        For example:
            ``CodeBase.base_dir / self.path``

            Specifies the absolute path to the sub project folder.
        """
        return self.__sub_path

    @property
    def is_submodule(self) -> bool:
        """
        Determine if this project is a submodule and shouldn't be cloned and
        pulled automatically when a `CodeBase` is initialized or updated.

        Returns:
            True, if it should be automatically cloned
        """
        return self.__is_submodule

    def init_and_update_submodules(self) -> None:
        """
        Initialize and update all submodules of this sub project.

        Args:
            cb_base_dir: base directory for the ``CodeBase``
        """
        init_all_submodules(self.__parent_code_base.base_dir / self.path)
        update_all_submodules(self.__parent_code_base.base_dir / self.path)

    def clone(self) -> None:
        """Clone the sub project into the specified folder relative to the base
        dir of the ``CodeBase``."""
        print(f"Cloning {self.name} into {self.__parent_code_base.base_dir}")
        if (self.__parent_code_base.base_dir / self.path).exists():
            raise FolderAlreadyPresentError(
                self.__parent_code_base.base_dir / self.path
            )
        download_repo(
            self.__parent_code_base.base_dir / self.path.parent, self.url,
            self.path.name, self.remote, log_without_linesep(print)
        )

    def has_branch(
        self,
        branch_name: str,
        remote_to_check: tp.Optional[str] = None
    ) -> bool:
        """
        Check if the sub project has a branch with the specified ``branch
        name``.

        Args:
            branch_name: name of the branch
            remote_to_check: name of the remote to check, if None, only a local
                             check will be performed

        Returns:
            True, if the branch exists
        """
        absl_repo_path = self.__parent_code_base.base_dir / self.path
        if remote_to_check is None:
            return has_branch(absl_repo_path, branch_name)

        return has_remote_branch(absl_repo_path, branch_name, remote_to_check)

    def get_branches(self,
                     extra_args: tp.Optional[tp.List[str]
                                            ] = None) -> tp.List[str]:
        """
        Get branch names from this sub project.

        Args:
            extra_args: extra arguments passed to `git branch`

        Returns:
            list of branch names
        """
        return get_branches(
            self.__parent_code_base.base_dir / self.path, extra_args
        ).split()

    def add_remote(self, remote: str, url: str) -> None:
        """
        Add a new remote to the sub project.

        Args:
            remote: name of the new remote
            url: to the remote
        """
        add_remote(self.__parent_code_base.base_dir / self.path, remote, url)
        fetch_remote(remote, self.__parent_code_base.base_dir / self.path)

    def checkout_branch(self, branch_name: str) -> None:
        """
        Checkout out branch in sub project.

        Args:
            branch_name: name of the branch, should exists in the repo
        """
        checkout_branch_or_commit(
            self.__parent_code_base.base_dir / self.path, branch_name
        )

    def checkout_new_branch(
        self, branch_name: str, remote_branch: tp.Optional[str] = None
    ) -> None:
        """
        Create and checkout out a new branch in the sub project.

        Args:
            branch_name: name of the new branch, should not exists in the repo
        """
        checkout_new_branch(
            self.__parent_code_base.base_dir / self.path, branch_name,
            remote_branch
        )

    def fetch(
        self,
        remote: tp.Optional[str] = None,
        extra_args: tp.Optional[tp.List[str]] = None
    ) -> None:
        """Fetch updates from the remote."""
        fetch_remote(
            remote, self.__parent_code_base.base_dir / self.path, extra_args
        )

    def pull(self) -> None:
        """Pull updates from the remote of the current branch into the sub
        project."""
        pull_current_branch(self.__parent_code_base.base_dir / self.path)

    def push(self) -> None:
        """Push updates from the current branch to the remote branch."""
        absl_repo_path = self.__parent_code_base.base_dir / self.path
        branch_name = get_current_branch(absl_repo_path)
        if branch_has_upstream(absl_repo_path, branch_name):
            push_current_branch(absl_repo_path)
        else:
            push_current_branch(absl_repo_path, "origin", branch_name)

    def show_status(self) -> None:
        """Show the current status of the sub project."""
        show_status(self.__parent_code_base.base_dir / self.path)

    def __str__(self) -> str:
        return f"{self.name} [{self.url}:{self.remote}] {self.path}"

    def get_tags(self,
                 extra_args: tp.Optional[tp.List[str]] = None) -> tp.List[str]:
        """Get the list of available git tags."""
        tag_list = get_tags(
            self.__parent_code_base.base_dir / self.path, extra_args
        )
        return tag_list


class CodeBase():
    """
    A ``CodeBase`` depicts the layout of a project, specifying where the a
    research tool lives and how different sub projects should be cloned.

    In addition, it allows access to the sub projects, e.g., for checkout or
    other repository manipulations.
    """

    def __init__(self, base_dir: Path, sub_projects: tp.List[SubProject]):
        self.__sub_projects = sub_projects
        self.__base_dir = base_dir

    @property
    def base_dir(self) -> Path:
        return self.__base_dir

    def get_sub_project(self, name: str) -> SubProject:
        """
        Lookup a sub project of this ``CodeBase``

        Args:
            name: of the sub project
        """
        for sub_project in self.__sub_projects:
            if sub_project.name == name:
                return sub_project
        raise LookupError

    def clone(self, cb_base_dir: Path) -> None:
        """
        Clones the full code base into the specified folder ``cb_base_dir``,
        which marks the base folder of the code base structure.

        Args:
            cb_base_dir: new base dir of the code base
        """
        self.__base_dir = cb_base_dir
        for sub_project in self.__sub_projects:
            if not sub_project.is_submodule:
                sub_project.clone()

    def map_sub_projects(
        self,
        func: tp.Callable[[SubProject], None],
        exclude_submodules: bool = False
    ) -> None:
        """
        Execute a callable ``func`` on all sub projects of the code base.

        Args:
            func: function to execute on the sub projects
            exclude_submodules: if True sub projects that
                                are managed using git submodules will be
                                excluded
        """
        for sub_project in self.__sub_projects:
            if exclude_submodules and sub_project.is_submodule:
                continue
            func(sub_project)


SpecificCodeBase = tp.TypeVar("SpecificCodeBase", bound=CodeBase)


class ResearchTool(tp.Generic[SpecificCodeBase]):
    """ResearchTool is an abstract base class for specifying research tools that
    are set up by VaRA-TS and usable through the tool suites experiments and
    tools."""

    def __init__(
        self, tool_name: str, supported_build_types: tp.List[BuildType],
        code_base: SpecificCodeBase
    ) -> None:
        self.__name = tool_name
        self.__supported_build_types = supported_build_types
        self.__code_base = code_base

    @property
    def code_base(self) -> SpecificCodeBase:
        return self.__code_base

    @property
    def name(self) -> str:
        return self.__name

    def is_build_type_supported(self, build_type: BuildType) -> bool:
        return build_type in self.__supported_build_types

    @classmethod
    @abc.abstractmethod
    def get_dependencies(cls) -> Dependencies:
        """Returns the dependencies for this research tool."""

    @staticmethod
    @abc.abstractmethod
    def source_location() -> Path:
        """Returns the source location of the research tool."""

    @staticmethod
    @abc.abstractmethod
    def has_source_location() -> bool:
        """Checks if a source location of the research tool is configured."""

    @staticmethod
    @abc.abstractmethod
    def install_location() -> Path:
        """Returns the install location of the research tool."""

    @staticmethod
    @abc.abstractmethod
    def has_install_location() -> bool:
        """Checks if a install location of the research tool is configured."""

    @abc.abstractmethod
    def setup(
        self, source_folder: tp.Optional[Path], install_prefix: Path,
        version: tp.Optional[int]
    ) -> None:
        """
        Setup a research tool with it's code base. This method sets up all
        relevant config variables, downloads repositories via the ``CodeBase``,
        checks out the correct branches and prepares the research tool to be
        build.

        Args:
            source_folder: location to store the code base in
            install_prefix: Installation prefix path
            version: Version to setup
        """

    @abc.abstractmethod
    def find_highest_sub_prj_version(self, sub_prj_name: str) -> int:
        """Returns the highest release version number for the specified
        ``SubProject`` name."""

    @abc.abstractmethod
    def is_up_to_date(self) -> bool:
        """Returns true if VaRA's major release version is up to date."""

    @abc.abstractmethod
    def upgrade(self) -> None:
        """Upgrade the research tool to a newer version."""

    @abc.abstractmethod
    def build(
        self, build_type: BuildType, install_location: Path,
        build_folder_suffix: tp.Optional[str]
    ) -> None:
        """
        Build/Compile the research tool in the specified ``build_type`` and
        install it to the specified ``install_location``.

        Args:
            build_type: which type of build should be used, e.g., debug,
                        development or release
            install_location: location to install the research tool into
            build_folder_suffix: a suffix that is appended to the build folder
        """

    @abc.abstractmethod
    def verify_install(self, install_location: Path) -> bool:
        """
        Verify if the research tool was correctly installed.

        Returns:
            True, if the tool was correctly installed
        """

    @abc.abstractmethod
    def verify_build(
        self, build_type: BuildType, build_folder_suffix: tp.Optional[str]
    ) -> bool:
        """
        Verify if the research tool was built correctly for a given build_type.

        Args:
            build_type: which type of build should be used, e.g., debug,
                        development or release
            build_folder_suffix: a suffix that is appended to the build folder

        Returns:
            True, if the build was correct.
        """

    def container_install_dependencies(
        self, image_context: 'containers.BaseImageCreationContext'
    ) -> None:
        """
        Add layers for installing this research tool's dependencies to the given
        container.

        Args:
            image_context: the base image creation context
        """
        if self.get_dependencies().has_dependencies_for_distro(
            image_context.base.distro
        ):
            image_context.layers.run(
                *(
                    self.get_dependencies().
                    get_install_command(image_context.base.distro).split(" ")
                )
            )

    @abc.abstractmethod
    def container_install_tool(
        self, image_context: 'containers.BaseImageCreationContext'
    ) -> None:
        """
        Add layers for installing this research tool to the given container.

        Args:
            image_context: the base image creation context
        """
