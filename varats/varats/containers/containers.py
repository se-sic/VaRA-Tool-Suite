"""Container related functionality."""

import logging
import typing as tp
from copy import deepcopy
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory

from benchbuild.environments.domain.commands import (
    Command,
    CreateImage,
    fs_compliant_name,
    ExportImage,
)
from benchbuild.environments.domain.declarative import (
    add_benchbuild_layers,
    ContainerImage,
)
from benchbuild.environments.service_layer import messagebus, unit_of_work
from benchbuild.utils.cmd import buildah
from plumbum import local
from plumbum.commands import ConcreteCommand

from varats.tools.research_tools.research_tool import Distro
from varats.tools.tool_util import get_research_tool
from varats.utils.settings import bb_cfg, vara_cfg

LOG = logging.getLogger(__name__)


def prepare_buildah() -> ConcreteCommand:
    return buildah["--root",
                   bb_cfg()["container"]["root"].value, "--runroot",
                   bb_cfg()["container"]["runroot"].value]


class ImageBase(Enum):
    """Container image bases that can be used by projects."""
    DEBIAN_10 = ("localhost/debian:10_varats", Distro.DEBIAN)

    def __init__(self, name: str, distro: Distro):
        self.__name = name
        self.__distro = distro

    @property
    def image_name(self) -> str:
        image_name = self.__name
        configured_research_tool = vara_cfg()["container"]["research_tool"]
        if configured_research_tool:
            research_tool = get_research_tool(str(configured_research_tool))
            image_name += f"_{research_tool.name.lower()}"
        return image_name

    @property
    def distro(self) -> Distro:
        return self.__distro


_BASE_IMAGES: tp.Dict[ImageBase, tp.Callable[[], ContainerImage]] = {
    ImageBase.DEBIAN_10:
        lambda: ContainerImage().from_("docker.io/library/debian:10").
        run('apt', 'update').run(
            'apt', 'install', '-y', 'python3', 'python3-dev', 'python3-pip',
            'musl-dev', 'git', 'gcc', 'libgit2-dev', 'libffi-dev',
            'libyaml-dev', 'clang'
        )
}


class BaseImageCreationContext():
    """
    Context for base image creation.

    This class stores context information when creating a base image.
    """

    def __init__(self, base: ImageBase, tmpdir: Path):
        self.__layers = _BASE_IMAGES[base]()
        self.__distro = base.distro
        self.__image_name = base.image_name
        self.__tmpdir = tmpdir

    @property
    def layers(self) -> ContainerImage:
        """
        Layers of the container that is being created using this context.

        Users of this context can use this object to add new layers.

        Returns:
            the container layers
        """
        return self.__layers

    @property
    def image_name(self) -> str:
        """
        Name of the image that is being created.

        Returns:
            the name of the image that is being created
        """
        return self.__image_name

    @property
    def distro(self) -> Distro:
        """
        Distro the image that is being created is based on.

        Returns:
            the distro of the image that is being created
        """
        return self.__distro

    @property
    def varats_root(self) -> Path:
        """
        VaRA-TS root inside the container.

        Returns:
            the VaRA-TS root inside the container
        """
        return Path("/varats_root/")

    @property
    def bb_root(self) -> Path:
        """
        BenchBuild root inside the container.

        Returns:
            the BenchBuild root inside the container
        """
        return Path("/app/")

    @property
    def tmpdir(self) -> Path:
        """
        Temporary directory that can be used during image creation.

        Returns:
            the path to the temporary directory
        """
        return self.__tmpdir


def _add_varats_layers(image_context: BaseImageCreationContext) -> None:
    crun = bb_cfg()['container']['runtime'].value
    src_dir = Path(vara_cfg()['container']['varats_source'].value)
    tgt_dir = Path('/varats')

    def from_source(image: ContainerImage) -> None:
        LOG.debug('installing benchbuild from source.')
        LOG.debug(f'src_dir: {src_dir} tgt_dir: {tgt_dir}')

        image.run('mkdir', f'{tgt_dir}', runtime=crun)
        image.run('pip3', 'install', 'setuptools', runtime=crun)
        image.run(
            'pip3',
            'install',
            '--ignore-installed',
            str(tgt_dir / 'varats-core'),
            str(tgt_dir / 'varats'),
            mount=f'type=bind,src={src_dir},target={tgt_dir}',
            runtime=crun
        )

    def from_pip(image: ContainerImage) -> None:
        LOG.debug("installing varats from pip release.")
        image.run('pip3', 'install', 'varats-core', 'varats', runtime=crun)

    if bool(vara_cfg()['container']['from_source']):
        from_source(image_context.layers)
    else:
        from_pip(image_context.layers)


def _add_vara_config(image_context: BaseImageCreationContext) -> None:
    config = deepcopy(vara_cfg())
    config_file = str(image_context.tmpdir / ".varats.yaml")

    config["config_file"] = str(image_context.varats_root / ".varats.yaml")
    config["result_dir"] = str(image_context.varats_root / "results/")
    config["paper_config"]["folder"] = str(
        image_context.varats_root / "paper_configs/"
    )
    config["benchbuild_root"] = str(image_context.bb_root)

    config.store(local.path(config_file))
    image_context.layers.copy_([config_file], config["config_file"].value)
    image_context.layers.env(VARATS_CONFIG_FILE=config["config_file"].value)


def _add_benchbuild_config(image_context: BaseImageCreationContext) -> None:
    image_context.layers.env(
        BB_VARATS_OUTFILE=str(image_context.varats_root / "results"),
        BB_VARATS_RESULT=str(image_context.varats_root / "BC_files"),
        BB_JOBS=str(bb_cfg()["jobs"]),
    )


def create_base_image(base: ImageBase) -> None:
    """
    Build a base image for the given image base and the current research tool.

    Args:
        base: the image base
    """
    with TemporaryDirectory() as tmpdir:
        image_context = BaseImageCreationContext(base, Path(tmpdir))

        # we need an up-to-date pip version to get the prebuilt pygit2 package
        # with an up-to-date libgit2
        image_context.layers.run('pip3', 'install', '--upgrade', 'pip')
        _add_varats_layers(image_context)
        # override bb with custom version if bb install from source is active
        if bb_cfg()['container']['from_source']:
            add_benchbuild_layers(image_context.layers)

        # add research tool if configured
        configured_research_tool = vara_cfg()["container"]["research_tool"]
        if configured_research_tool:
            research_tool = get_research_tool(str(configured_research_tool))
            research_tool.add_container_layers(image_context)

        _add_vara_config(image_context)
        _add_benchbuild_config(image_context)

        image_context.layers.workingdir(str(image_context.bb_root))
        cmd: Command = CreateImage(base.image_name, image_context.layers)
        uow = unit_of_work.ContainerImagesUOW()
        messagebus.handle(cmd, uow)


def create_base_images() -> None:
    """Builds all base images for the current research tool."""
    for base in ImageBase:
        LOG.info(f"Building base image {base.image_name}.")
        create_base_image(base)


def get_base_image(base: ImageBase) -> ContainerImage:
    """
    Get the requested base image for the current research tool.

    Args:
        base: the base image to retrieve

    Returns:
        the requested base image
    """
    return ContainerImage().from_(base.image_name)


def delete_base_image(base: ImageBase) -> None:
    """
    Delete the base image for the given image base and the current research
    tool.

    Args:
        base: the image base
    """
    prepare_buildah()("rmi", "--force", base.image_name)


def delete_base_images() -> None:
    """Deletes all base images for the current research tool."""
    for base in ImageBase:
        LOG.info(f"Deleting base image {base.image_name}.")
        delete_base_image(base)


def export_base_image(base: ImageBase) -> None:
    """Export the base image to the filesystem."""
    uow = unit_of_work.ContainerImagesUOW()
    export_name = fs_compliant_name(base.image_name)
    export_path = local.path(
        bb_cfg()["container"]["export"].value
    ) / export_name + ".tar"
    export_cmd = ExportImage(base.image_name, str(export_path))
    messagebus.handle(export_cmd, uow)


def export_base_images() -> None:
    """Exports all base images for the current research tool."""
    for base in ImageBase:
        LOG.info(f"Exporting base image {base.image_name}.")
        export_base_image(base)
