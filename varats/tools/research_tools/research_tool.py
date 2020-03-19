"""
This modules provides the base classes for research tools that allow developers
to setup and configure their own research tool by inheriting and implementing
the base classes ``ResearchTool`` and ``CodeBase``.
"""
import typing as tp
import abc
import logging
from pathlib import Path

from varats.vara_manager import (BuildType, download_repo, add_remote,
                                 checkout_branch, fetch_remote,
                                 init_all_submodules, update_all_submodules)
from varats.utils.cli_util import log_without_linsep
from varats.utils.filesystem_util import FolderAlreadyPresentError

LOG = logging.getLogger(__name__)


class SubProject():
    """
    Encapsulates a sub project, e.g., a library or tool, defining how it can be
    downloaded and integrated inside a ``CodeBase``.
    """

    def __init__(self, name: str, URL: str, remote: str, sub_path: str):
        self.__name = name
        self.__url = URL
        self.__remote = remote
        self.__sub_path = Path(sub_path)

    @property
    def name(self) -> str:
        """
        Name of the sub project
        """
        return self.__name

    @property
    def url(self) -> str:
        """
        Repository URL
        """
        return self.__url

    @property
    def remote(self) -> str:
        """
        Git remote, for interacting with upstream repositories.
        """
        return self.__remote

    @property
    def path(self) -> Path:
        """
        Path to the sub project folder within a ``CodeBase``.

        For example:
            ``CodeBase.base_dir / self.path``

            Specifies the full qualified path to the sub project folder.
        """
        return self.__sub_path

    def init_and_update_submodules(self, cb_base_dir: Path) -> None:
        """
        Initialize and update all submodules of this sub project.

        Args:
            cb_base_dir: base directory for the ``CodeBase``
        """
        init_all_submodules(cb_base_dir / self.path)
        update_all_submodules(cb_base_dir / self.path)

    def clone(self, cb_base_dir: Path) -> None:
        """
        Clone the sub project into the specified folder relative to
        ``cb_base_dir``.

        Args:
            cb_base_dir: base directory for the ``CodeBase``
        """
        LOG.info(f"Cloning {self.name} into {cb_base_dir}")
        if (cb_base_dir / self.path).exists():
            raise FolderAlreadyPresentError(cb_base_dir / self.path)
        download_repo(cb_base_dir / self.path.parent, self.url, self.path.name,
                      self.remote, log_without_linsep(LOG.info))

    def add_remote(self, cb_base_dir: Path, remote: str, url: str) -> None:
        """
        Add a new remote to the sub project

        Args:
            cb_base_dir: base directory for the ``CodeBase``
            remote: name of the new remote
            url: to the remote
        """
        add_remote(cb_base_dir / self.path, remote, url)
        fetch_remote(remote, cb_base_dir / self.path)

    def checkout_branch(self, cb_base_dir: Path, branch_name: str) -> None:
        """
        Checkout our branch in sub project.

        Args:
            cb_base_dir: base directory for the ``CodeBase``
            branch_name: name of the branch, should exists in the repo
        """
        checkout_branch(cb_base_dir / self.path, branch_name)

    def __str__(self) -> str:
        return "{name} [{url}:{remote}] {folder}".format(name=self.name,
                                                         url=self.url,
                                                         remote=self.remote,
                                                         folder=self.path)


class CodeBase():
    """
    A ``CodeBase`` depicts the layout of a project, specifying where the a
    research tool lives and how different sub projects should be cloned. In
    addition, it allows access to the sub projects, e.g., for checkout or other
    repository manipulations.
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
        which markes the base folder of the code base structure.

        Args:
            cb_base_dir: new base dir of the code base
        """
        self.__base_dir = cb_base_dir
        for sub_project in self.__sub_projects:
            sub_project.clone(self.base_dir)


"""
    TODO: remove later
    ResearchTool | Project
        ? repo interactions
            * status accessors

    ? good generalizations over different projects
        * show status
        * allow repo interactions
"""

SpecificCodeBase = tp.TypeVar("SpecificCodeBase", bound=CodeBase)


class ResearchTool(tp.Generic[SpecificCodeBase]):
    """
    ResearchTool is an abstract base class for specifying research tools that
    are setup by VaRA-TS and usable through the tool suites experiments and
    tools.
    """

    def __init__(self, tool_name: str,
                 supported_build_types: tp.List[BuildType],
                 code_base: SpecificCodeBase) -> None:
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

    @abc.abstractmethod
    def setup(self, source_folder: Path, **kwargs: tp.Any) -> None:
        """
        Setup a research tool with it's code base. This method sets up all
        relevant config variables, downloads repositories via the ``CodeBase``,
        checkouts the correct branches and prepares the research tool to be
        build.

        Args:
            source_folder: location to store the code base in
        """

    @abc.abstractmethod
    def upgrade(self) -> None:
        """
        Upgrade the research tool to a newer version.
        """

    @abc.abstractmethod
    def build(self, build_type: BuildType, install_location: Path) -> None:
        """
        Build/Compile the research tool in the specified ``build_type`` and
        install it to the specified ``install_location``.

        Args:
            build_type: which type of build should be used, e.g., debug,
                        development or release
            install_location: location to install the research tool into
        """
