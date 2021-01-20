"""Container related functionality."""

import logging
import typing as tp
from copy import deepcopy
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory

from benchbuild.environments.domain.commands import Command, CreateImage
from benchbuild.environments.domain.declarative import (
    add_benchbuild_layers,
    ContainerImage,
)
from benchbuild.environments.service_layer import messagebus, unit_of_work
from benchbuild.utils.cmd import buildah
from plumbum import local
from plumbum.commands import ConcreteCommand

from varats.tools.tool_util import get_research_tool
from varats.utils.settings import bb_cfg, vara_cfg

LOG = logging.getLogger(__name__)


def prepare_buildah() -> ConcreteCommand:
    return buildah["--root",
                   bb_cfg()["container"]["root"].value, "--runroot",
                   bb_cfg()["container"]["runroot"].value]


class ImageBase(Enum):
    """Container image bases that can be used by projects."""
    DEBIAN_10 = "localhost/debian:10_varats"


__BASE_IMAGES: tp.Dict[ImageBase, ContainerImage] = {
    ImageBase.DEBIAN_10:
        ContainerImage().from_("docker.io/library/debian:10"
                              ).run('apt', 'update').run(
                                  'apt', 'install', '-y', 'python3',
                                  'python3-dev', 'python3-pip', 'musl-dev',
                                  'git', 'gcc', 'libgit2-dev', 'libffi-dev',
                                  'libyaml-dev', 'clang'
                              )
}

CONTAINER_VARATS_ROOT: Path = Path("/varats_root/")
CONTAINER_BB_ROOT: Path = Path("/app/")


def _add_varats_layers(layers: ContainerImage) -> ContainerImage:
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
        from_source(layers)
    else:
        from_pip(layers)
    return layers


def _add_vara_config(layers: ContainerImage, tmp_dir: str) -> ContainerImage:
    config = deepcopy(vara_cfg())
    config_file = tmp_dir + "/.varats.yaml"

    config["config_file"] = str(CONTAINER_VARATS_ROOT / ".varats.yaml")
    config["result_dir"] = str(CONTAINER_VARATS_ROOT / "results/")
    config["paper_config"]["folder"] = str(
        CONTAINER_VARATS_ROOT / "paper_configs/"
    )
    config["benchbuild_root"] = str(CONTAINER_BB_ROOT)

    #TODO: hook for research tool (se-passau/VaRA#718)

    config.store(local.path(config_file))
    layers.copy_([config_file], config["config_file"].value)
    layers.env(VARATS_CONFIG_FILE=config["config_file"].value)

    return layers


def _add_benchbuild_config(layers: ContainerImage) -> ContainerImage:
    layers.env(
        BB_VARATS_OUTFILE=str(CONTAINER_VARATS_ROOT / "results"),
        BB_VARATS_RESULT=str(CONTAINER_VARATS_ROOT / "BC_files")
    )

    return layers


def create_base_image(base: ImageBase) -> None:
    """
    Build a base image for the given image base and the current research tool.

    Args:
        base: the image base
    """
    with TemporaryDirectory() as tmpdir:
        image = __BASE_IMAGES[base]
        image_name = base.value

        # we need an up-to-date pip version to get the prebuilt pygit2 package
        # with an up-to-date libgit2
        image.run('pip3', 'install', '--upgrade', 'pip')
        _add_varats_layers(image)
        # override bb with custom version if bb install from source is active
        if bb_cfg()['container']['from_source']:
            add_benchbuild_layers(image)

        # add research tool if configured
        configured_research_tool = vara_cfg()["container"]["research_tool"]
        if configured_research_tool:
            research_tool = get_research_tool(str(configured_research_tool))
            image_name += f"_{research_tool.name.lower()}"
            # TODO (se-passau/VaRA#718): enable when implemented
            # research_tool.add_container_layers(image)

        _add_vara_config(image, tmpdir)
        _add_benchbuild_config(image)

        image.workingdir(str(CONTAINER_BB_ROOT))
        cmd: Command = CreateImage(image_name, image)
        uow = unit_of_work.ContainerImagesUOW()
        messagebus.handle(cmd, uow)


def create_base_images() -> None:
    """Builds all base images for the current research tool."""
    for base in ImageBase:
        LOG.info(f"Building base container {base.value}.")
        create_base_image(base)


def get_base_image(base: ImageBase) -> ContainerImage:
    """
    Get the requested base image for the current research tool.

    Args:
        base: the base image to retrieve

    Returns:
        the requested base image
    """
    image_name = base.value
    configured_research_tool = vara_cfg()["container"]["research_tool"]
    if configured_research_tool:
        research_tool = get_research_tool(str(configured_research_tool))
        image_name += f"_{research_tool.name.lower()}"
    return ContainerImage().from_(image_name)


def delete_base_image(base: ImageBase) -> None:
    """
    Delete the base image for the given image base and the current research
    tool.

    Args:
        base: the image base
    """
    prepare_buildah()("rmi", "--force", base.value)


def delete_base_images() -> None:
    """Deletes all base images for the current research tool."""
    for base in ImageBase:
        LOG.info(f"deleting base container {base.value}.")
        delete_base_image(base)
