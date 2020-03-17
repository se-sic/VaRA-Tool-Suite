"""
TODO: module docs
"""
import typing as tp
import abc
import logging
from pathlib import Path

from varats.vara_manager import (BuildType, download_repo, add_remote,
                                 checkout_branch, fetch_remote)

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

    def clone(self, cb_base_dir: Path) -> None:
        """
        Clone the sub project into the specified folder relative to
        ``cb_base_dir``.

        Args:
            cb_base_dir: base directory for the ``CodeBase``
        """
        LOG.info(f"Cloning {self.name} into {cb_base_dir}")
        # TODO: add check if folder exists and throw exception
        download_repo(cb_base_dir / self.path.parent, self.url, self.path.name,
                      self.remote, print)

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
        self.__base_dir = cb_base_dir  # TODO: maybe remove and only depend on init param
        for sub_project in self.__sub_projects:
            sub_project.clone(self.base_dir)


"""
    Project -> VaRA, SPLConquerer, ...

    ResearchTool | Project
        - CodeBase -> sub projects // layout of repos
            * sub projects iterator ?
        ? repo interactions
            * status accessors

    BuildType

    ? StateManager

    ? good generalizations over different projects
        * show status
        * allow repo interactions
"""


class ResearchTool():
    """
    ResearchTool is an abstract base class for specifying research tools that
    are setup by VaRA-TS and usable through the tool suites experiments and
    tools.
    """

    def __init__(self, supported_build_types: tp.List[BuildType],
                 code_base: CodeBase) -> None:
        self.__supported_build_types = supported_build_types
        self.__code_base = code_base

    @property
    def code_base(self) -> CodeBase:
        return self.__code_base

    def is_build_type_supported(self, build_type: BuildType) -> bool:
        return build_type in self.__supported_build_types

    @abc.abstractmethod
    def setup(self, source_folder: Path, **kwargs) -> None:
        """
        TODO:
        - setup instructions
            * download
            * checkout different versions
            * folder layout
        """

    @abc.abstractmethod
    def upgrade(self) -> None:
        """
        Upgrade the research tool to a newer version.
        """

    @abc.abstractmethod
    def build(self, build_type: BuildType) -> None:
        """
        TODO:
        - build instructions
            * build_type
        """

    @abc.abstractmethod
    def install(self, install_location: Path) -> None:
        """
        Install the research tool into the given install_location.

        Args:
            install_location: a valid path to an existing folder
        """
