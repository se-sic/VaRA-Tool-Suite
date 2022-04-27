"""Module for the research tool VaRA that describes the VaRA code base layout
and how to configure and setup VaRA."""
import logging
import math
import os
import re
import shutil
import typing as tp
from pathlib import Path

from benchbuild.utils.cmd import ln, mkdir
from plumbum import local
from PyQt5.QtCore import QProcess

from varats.tools.research_tools.cmake_util import set_cmake_var
from varats.tools.research_tools.research_tool import (
    CodeBase,
    ResearchTool,
    SubProject,
    Dependencies,
    Distro,
)
from varats.tools.research_tools.vara_manager import (
    BuildType,
    ProcessManager,
    run_process_with_output,
)
from varats.utils.exceptions import ProcessTerminatedError
from varats.utils.logger_util import log_without_linesep
from varats.utils.settings import save_config, vara_cfg

if tp.TYPE_CHECKING:
    from varats.containers import containers  # pylint: disable=W0611

LOG = logging.getLogger(__name__)


def set_vara_cmake_variables(
    install_prefix: str,
    post_out: tp.Callable[[str], None] = lambda x: None
) -> None:
    """Set all wanted/needed cmake flags."""
    set_cmake_var("CMAKE_INSTALL_PREFIX", install_prefix, post_out)
    set_cmake_var("CMAKE_CXX_STANDARD", str(17), post_out)


class VaRACodeBase(CodeBase):
    """Layout of the VaRA code base: setting up vara-llvm-project fork, VaRA,
    and optionally phasar for static analysis."""

    def __init__(self, base_dir: Path) -> None:
        sub_projects = [
            SubProject(
                self, "vara-llvm-project",
                "https://github.com/llvm/llvm-project.git", "upstream",
                "vara-llvm-project"
            ),
            SubProject(
                self, "VaRA", "git@github.com:se-sic/VaRA.git", "origin",
                "vara-llvm-project/vara"
            ),
            SubProject(
                self,
                "phasar",
                "https://github.com/secure-software-engineering/phasar.git",
                "origin",
                "vara-llvm-project/phasar",
                is_submodule=True
            )
        ]
        super().__init__(base_dir, sub_projects)

    def setup_vara_remotes(self) -> None:
        """Sets up VaRA specific upstream remotes for projects that were
        forked."""
        self.get_sub_project("vara-llvm-project").add_remote(
            "origin", "git@github.com:se-sic/vara-llvm-project.git"
        )

    def setup_build_link(self) -> None:
        """Setup build-config folder link for VaRA's default build setup
        scripts."""
        llvm_project_dir = self.base_dir / self.get_sub_project(
            "vara-llvm-project"
        ).path
        mkdir(llvm_project_dir / "build/")
        with local.cwd(llvm_project_dir / "build/"):
            ln("-s", "../vara/utils/vara/builds/", "build_cfg")

    def checkout_vara_version(
        self, version: int, use_dev_branches: bool
    ) -> None:
        """
        Checkout out a specific version of VaRA.

        Args:
            version: major version number, e.g., 100 or 110
            use_dev_branches: true, if one wants the current development version
        """
        dev_suffix = "-dev" if use_dev_branches else ""
        print(f"Checking out VaRA version {str(version) + dev_suffix}")

        self.get_sub_project("vara-llvm-project"
                            ).checkout_branch(f"vara-{version}{dev_suffix}")

        # TODO (sattlerf): make different checkout for older versions
        self.get_sub_project("VaRA").checkout_branch(f"vara{dev_suffix}")

    def setup_submodules(self) -> None:
        """Set up the git submodules of all sub projects."""
        self.get_sub_project("vara-llvm-project").init_and_update_submodules()
        self.get_sub_project("phasar").init_and_update_submodules()

    def pull(self) -> None:
        """Pull and update all ``SubProject`` s."""
        self.map_sub_projects(lambda prj: prj.pull(), exclude_submodules=True)
        self.setup_submodules()

    def fetch(
        self,
        sub_prj_name: str,
        remote: tp.Optional[str] = None,
        extra_args: tp.Optional[tp.List[str]] = None
    ) -> None:
        """Fetch the `SubProject` corresponding to the passed subproject
        name."""
        sub_prj: SubProject = self.get_sub_project(sub_prj_name)
        sub_prj.fetch(remote, extra_args)

    def get_tags(
        self,
        sub_prj_name: str,
        extra_args: tp.Optional[tp.List[str]] = None
    ) -> tp.List[str]:
        """Get a list of available git tags of the `SubProject` corresponding to
        the passed subproject name."""
        sub_prj: SubProject = self.get_sub_project(sub_prj_name)
        tag_list = sub_prj.get_tags(extra_args)
        return tag_list


class VaRA(ResearchTool[VaRACodeBase]):
    """
    Research tool implementation for VaRA.

    Find the main repo online on github: https://github.com/se-sic/VaRA
    """

    __DEPENDENCIES = Dependencies({
        Distro.DEBIAN: [
            "libboost-all-dev", "libpapi-dev", "googletest", "libsqlite3-dev",
            "libxml2-dev", "libcurl4-openssl-dev", "cmake", "ninja-build"
        ],
        Distro.ARCH: [
            "boost-libs", "boost", "sqlite3", "libxml2", "cmake", "curl",
            "ninja"
        ],
        Distro.FEDORA: [
            "libsqlite3x-devel", "libcurl-devel", "boost-devel", "papi-devel",
            "llvm-googletest", "libxml2-devel", "clang"
        ]
    })

    def __init__(self, base_dir: Path) -> None:
        super().__init__("VaRA", [BuildType.DEV], VaRACodeBase(base_dir))
        vara_cfg()["vara"]["llvm_source_dir"] = str(base_dir)
        save_config()

    @classmethod
    def get_dependencies(cls) -> Dependencies:
        return cls.__DEPENDENCIES

    @staticmethod
    def source_location() -> Path:
        """Returns the source location of the research tool."""
        return Path(vara_cfg()["vara"]["llvm_source_dir"].value)

    @staticmethod
    def has_source_location() -> bool:
        """Checks if a source location of the research tool is configured."""
        return vara_cfg()["vara"]["llvm_source_dir"].value is not None

    @staticmethod
    def install_location() -> Path:
        """Returns the install location of the research tool."""
        return Path(vara_cfg()["vara"]["llvm_install_dir"].value)

    @staticmethod
    def has_install_location() -> bool:
        """Checks if a install location of the research tool is configured."""
        return vara_cfg()["vara"]["llvm_install_dir"].value is not None

    def setup(
        self, source_folder: tp.Optional[Path], install_prefix: Path,
        version: tp.Optional[int]
    ) -> None:
        """
        Setup the research tool VaRA with it's code base. This method sets up
        all relevant config variables, downloads repositories via the
        ``CodeBase``, checkouts the correct branches and prepares the research
        tool to be built.

        Args:
            source_folder: location to store the code base in
            install_prefix: Installation prefix path
            version: Version to setup
        """
        cfg = vara_cfg()
        if source_folder:
            cfg["vara"]["llvm_source_dir"] = str(source_folder)
        cfg["vara"]["llvm_install_dir"] = str(install_prefix)
        if version:
            version = int(version)
            cfg["vara"]["version"] = version
        else:
            version = int(cfg["vara"]["version"].value)
        save_config()

        print(f"Setting up VaRA in {self.source_location()}")

        use_dev_branches = cfg["vara"]["developer_version"].value

        self.code_base.clone(self.source_location())
        self.code_base.setup_vara_remotes()
        self.code_base.checkout_vara_version(version, use_dev_branches)
        self.code_base.setup_submodules()
        self.code_base.setup_build_link()

    def find_highest_sub_prj_version(self, sub_prj_name: str) -> int:
        """Returns the highest release version number for the specified
        ``SubProject`` name."""

        self.code_base.fetch(sub_prj_name)

        unfiltered_version_list: tp.List[str]
        highest_version = -1

        if sub_prj_name == "VaRA":
            unfiltered_version_list = self.code_base.get_tags("VaRA")
            version_pattern = re.compile(r"vara-([0-9]+\.[0-9])")

        elif sub_prj_name == "vara-llvm-project":
            unfiltered_version_list = self.code_base.get_sub_project(
                "vara-llvm-project"
            ).get_branches(["-r"])
            version_pattern = re.compile(r"vara-([0-9]+)-dev")
        else:
            LOG.warning(
                "The version retrieval of the specified subproject is not "
                "implemented yet."
            )
            raise NotImplementedError

        for unfiltered_version in unfiltered_version_list:
            match = version_pattern.search(unfiltered_version)
            if match:
                match_version = int(re.sub(r"\D", "", match.group()))
                if match_version > highest_version:
                    highest_version = match_version

        if highest_version == -1:
            warning_str = f"No version in {sub_prj_name} matched the release " \
                          f"pattern."
            LOG.warning(warning_str)
            raise LookupError

        return highest_version

    def is_up_to_date(self) -> bool:
        """Returns true if VaRA's major release version is up to date."""

        current_vara_version = int(vara_cfg()["vara"]["version"])

        highest_vara_tag_version = self.find_highest_sub_prj_version("VaRA")
        highest_vara_llvm_version = self.find_highest_sub_prj_version(
            "vara-llvm-project"
        )

        if (current_vara_version >=
            highest_vara_llvm_version) and current_vara_version >= (
                math.ceil(highest_vara_tag_version / 10) * 10
            ):
            return True

        return False

    def upgrade(self) -> None:
        """Upgrade the research tool to a newer version."""
        new_version = self.find_highest_sub_prj_version("vara-llvm-project")

        if new_version != (
            math.ceil(self.find_highest_sub_prj_version("VaRA") / 10) * 10
        ):
            raise AssertionError("vara-llvm-project and vara tool out of sync.")

        if str(vara_cfg()["vara"]["version"]) != str(new_version):
            self.code_base.checkout_vara_version(new_version, True)

            vara_cfg()["vara"]["version"] = new_version
            save_config()

        self.code_base.pull()

    def build(
        self, build_type: BuildType, install_location: Path,
        build_folder_suffix: tp.Optional[str]
    ) -> None:
        """
        Build/Compile VaRA in the specified ``build_type``. This method leaves
        VaRA in a finished state, i.e., being ready to be installed.

        Args:
            build_type: which type of build should be used, e.g., debug,
                        development or release
        """
        full_path = self.code_base.base_dir / "vara-llvm-project" / "build/"
        if not self.is_build_type_supported(build_type):
            LOG.critical(
                f"BuildType {build_type.name} is not supported by VaRA"
            )
            return

        build_folder_path = build_type.build_folder(build_folder_suffix)
        full_path /= build_folder_path
        build_args = [str(build_folder_path)] if build_folder_suffix else None

        # Setup configured build folder
        print(" - Setting up build folder.")
        if not os.path.exists(full_path):
            try:
                os.makedirs(full_path.parent, exist_ok=True)
                build_script = f"./build_cfg/build-{str(build_type)}.sh"

                with ProcessManager.create_process(
                    build_script, args=build_args, workdir=full_path.parent
                ) as proc:
                    proc.setProcessChannelMode(QProcess.MergedChannels)
                    proc.readyReadStandardOutput.connect(
                        lambda: run_process_with_output(
                            proc, log_without_linesep(print)
                        )
                    )
            except ProcessTerminatedError as error:
                shutil.rmtree(full_path)
                raise error
        print(" - Finished setup of build folder.")

        # Set install prefix in cmake
        with local.cwd(full_path):
            vara_cfg()["vara"]["llvm_install_dir"] = str(install_location)
            set_vara_cmake_variables(
                str(install_location), log_without_linesep(print)
            )
        print(" - Finished extra cmake config.")

        print(" - Now building...")
        # Compile llvm + VaRA
        with ProcessManager.create_process(
            "ninja", ["install"], workdir=full_path
        ) as proc:
            proc.setProcessChannelMode(QProcess.MergedChannels)
            proc.readyReadStandardOutput.connect(
                lambda:
                run_process_with_output(proc, log_without_linesep(print))
            )

    def install_exists(self, install_location: Path) -> bool:
        # pylint: disable=no-self-use
        """
        Check whether a VaRA installation exists at the given path.

        In contrast to :func:`verify_install()`, this does not try to execute
        any binaries. This is useful if the VaRA installation is intended for
        a different environment, e.g., in a container.

        Args:
            install_location: the installation directory to check

        Returns:
            True if the given directory contains a VaRA installation
        """
        status_ok = True
        status_ok &= (install_location / "bin/clang++").exists()
        status_ok &= (install_location / "bin/opt").exists()
        status_ok &= (install_location / "bin/phasar-llvm").exists()
        return status_ok

    def verify_install(self, install_location: Path) -> bool:
        """
        Verify if VaRA was correctly installed.

        Returns:
            True, if the tool was correctly installed
        """
        status_ok = self.install_exists(install_location)

        # Check that clang++ can display it's version
        clang = local[str(install_location / "bin/clang++")]
        ret, stdout, _ = clang.run("--version")

        vara_name = self.code_base.get_sub_project("vara-llvm-project").name
        status_ok &= ret == 0
        status_ok &= vara_name in stdout

        # Check that phasar-llvm can display it's version
        phasar_llvm = local[str(install_location / "bin/phasar-llvm")]
        ret, stdout, _ = phasar_llvm.run("--version")
        status_ok &= ret == 0

        phasar_name = self.code_base.get_sub_project("phasar").name.lower()
        status_ok &= phasar_name in stdout.lower()

        return status_ok

    def verify_build(
        self, build_type: BuildType, build_folder_suffix: tp.Optional[str]
    ) -> bool:
        """
        Verifies whether vara was built correctly for the given target.

        Args:
            build_type: which type of build should be used, e.g., debug,
                        development or release

        Returns:
            True iff all tests from check_vara pass
        """
        full_path = self.code_base.base_dir / "vara-llvm-project" / "build/"
        if not self.is_build_type_supported(build_type):
            LOG.critical(
                f"BuildType {build_type.name} is not supported by VaRA"
            )
            return False

        build_folder_path = build_type.build_folder(build_folder_suffix)
        full_path /= build_folder_path

        ninja = local["ninja"].with_cwd(full_path)
        ret, _, _ = ninja.run("check-vara")
        return bool(ret == 0)

    def container_install_tool(
        self, image_context: 'containers.BaseImageCreationContext'
    ) -> None:
        """
        Add layers for installing this research tool to the given container.

        Args:
            image_context: the base image creation context
        """
        img_name = image_context.base.name
        vara_install_dir = str(self.install_location()) + "_" + img_name
        if not self.install_exists(Path(vara_install_dir)):
            raise AssertionError(
                f"Could not find VaRA build for base container {img_name}.\n"
                f"Run 'vara-buildsetup build vara --container={img_name}' "
                f"to compile VaRA for this base image."
            )

        container_vara_dir = image_context.varats_root / (
            "tools/VaRA_" + img_name
        )
        image_context.layers.copy_([vara_install_dir], str(container_vara_dir))
        image_context.append_to_env("PATH", [str(container_vara_dir / 'bin')])
