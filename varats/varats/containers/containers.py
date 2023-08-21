"""Container related functionality."""

import logging
import typing as tp
from collections import defaultdict
from copy import deepcopy
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory

from benchbuild.environments import bootstrap
from benchbuild.environments.adapters.common import buildah_version
from benchbuild.environments.domain.commands import (
    CreateImage,
    fs_compliant_name,
    ExportImage,
    DeleteImage,
    RunProjectContainer,
)
from benchbuild.environments.domain.declarative import (
    add_benchbuild_layers,
    ContainerImage,
)
from benchbuild.utils.settings import to_yaml, get_number_of_jobs
from plumbum import local

from varats.tools.research_tools.research_tool import (
    Distro,
    ContainerInstallable,
)
from varats.tools.research_tools.vara_manager import BuildType
from varats.tools.tool_util import get_research_tool
from varats.utils.settings import bb_cfg, vara_cfg, save_bb_config

LOG = logging.getLogger(__name__)


class ImageBase(Enum):
    """Container image bases that can be used by projects."""
    DEBIAN_10 = Distro.DEBIAN

    def __init__(self, distro: Distro):
        self.__distro = distro

    @property
    def distro(self) -> Distro:
        """Distro of the base image."""
        return self.__distro


class ImageStage(Enum):
    """The stages that make up a base image."""
    STAGE_00_BASE = 00
    STAGE_10_VARATS = 10
    STAGE_20_TOOL = 20
    STAGE_30_CONFIG = 30
    STAGE_31_CONFIG_DEV = 31


class StageBuilder():
    """
    Context manager for creating a base image stage.

    The image is built automatically when exiting the context manager.
    """

    varats_root = Path("/varats_root/")
    """VaRA-TS root inside the container."""

    varats_source_mount_target = Path("/varats")
    """VaRA-TS root inside the container."""

    bb_root = Path("/app/")
    """BenchBuild root inside the container."""

    def __init__(self, base: ImageBase, stage: ImageStage, image_name: str):
        self.__base = base
        self.__stage = stage
        self.__layers = ContainerImage()
        self.__image_name = image_name
        # pylint: disable=consider-using-with
        self.__tmp_dir = TemporaryDirectory()

    def __enter__(self) -> 'StageBuilder':
        return self

    def __exit__(
        self, exc_type: tp.Any, exc_val: tp.Any, exc_tb: tp.Any
    ) -> None:
        bootstrap.bus()(CreateImage(self.image_name, self.layers))

        if self.__tmp_dir:
            self.__tmp_dir.cleanup()

    @property
    def base(self) -> ImageBase:
        """
        Base image this image is based on.

        Returns:
            the base image
        """
        return self.__base

    @property
    def stage(self) -> ImageStage:
        """
        Stage of the base image that should be built/updated.

        Only the given stage and subsequent stages shall be considered.

        Returns:
            the image stage
        """
        return self.__stage

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
    def tmpdir(self) -> Path:
        """
        Temporary directory that can be used during image creation.

        Returns:
            the path to the temporary directory
        """
        return Path(self.__tmp_dir.name)


def _create_stage_00_base_layers(stage_builder: StageBuilder) -> None:
    _BASE_IMAGES[stage_builder.base](stage_builder)
    _setup_venv(stage_builder)

    if (research_tool := _get_installable_research_tool()):
        research_tool.container_install_dependencies(stage_builder)


def _create_stage_10_varats_layers(stage_builder: StageBuilder) -> None:
    stage_builder.layers.run('pip3', 'install', '--upgrade', 'pip')
    _add_varats_layers(stage_builder)
    if bb_cfg()['container']['from_source']:
        add_benchbuild_layers(stage_builder.layers)


def _create_stage_20_tool_layers(stage_builder: StageBuilder) -> None:
    if (research_tool := _get_installable_research_tool()):
        research_tool.container_install_tool(stage_builder)


def _create_stage_30_config_layers(stage_builder: StageBuilder) -> None:
    env: tp.Dict[str, tp.List[str]] = {}
    if (research_tool := _get_installable_research_tool()):
        env = research_tool.container_tool_env(stage_builder)

    _add_vara_config(stage_builder)
    _add_benchbuild_config(stage_builder, env)
    stage_builder.layers.workingdir(str(stage_builder.bb_root))


def _create_stage_31_config_dev_layers(stage_builder: StageBuilder) -> None:
    stage_builder.layers.workingdir(str(stage_builder.varats_root))
    stage_builder.layers.entrypoint("vara-buildsetup")


def _create_layers_helper(
    create_layers: tp.Callable[[StageBuilder], tp.Any]
) -> tp.Callable[[StageBuilder], None]:

    def wrapped(stage_builder: StageBuilder) -> None:
        create_layers(stage_builder)

    return wrapped


# yapf: disable
_BASE_IMAGES: tp.Dict[ImageBase, tp.Callable[[StageBuilder], None]] = {
    ImageBase.DEBIAN_10:
        _create_layers_helper(lambda ctx: ctx.layers
            .from_("docker.io/library/debian:10")
            .run('apt', 'update')
            .run('apt', 'install', '-y', 'wget', 'gnupg', 'lsb-release',
                 'software-properties-common', 'musl-dev', 'git', 'gcc',
                 'libgit2-dev', 'libffi-dev', 'libyaml-dev', 'graphviz-dev')
            # install python 3.10
            .run('apt', 'install', '-y', 'build-essential', 'gdb', 'lcov',
                 'pkg-config', 'libbz2-dev', 'libffi-dev', 'libgdbm-dev',
                 'libgdbm-compat-dev', 'liblzma-dev', 'libncurses5-dev',
                 'libreadline6-dev', 'libsqlite3-dev', 'libssl-dev',
                 'lzma', 'lzma-dev', 'tk-dev', 'uuid-dev', 'zlib1g-dev')
            .run('wget',
                 'https://www.python.org/ftp/python/3.10.9/Python-3.10.9.tgz')
            .run('tar', '-xf', 'Python-3.10.9.tgz')
            .workingdir('Python-3.10.9')
            .run('./configure', '--enable-optimizations', 'CFLAGS=-fPIC')
            .run('make', '-j', str(get_number_of_jobs(bb_cfg())))
            .run('make', 'install')
            .workingdir('/')
            # install llvm 13
            .run('wget', 'https://apt.llvm.org/llvm.sh')
            .run('chmod', '+x', './llvm.sh')
            .run('./llvm.sh', '14', 'all')
            .run('ln', '-s', '/usr/bin/clang-14', '/usr/bin/clang')
            .run('ln', '-s', '/usr/bin/clang++-14', '/usr/bin/clang++')
            .run('ln', '-s', '/usr/bin/lld-14', '/usr/bin/lld'))
}

_STAGE_LAYERS: tp.Dict[ImageStage,
                       tp.Callable[[StageBuilder], None]] = {
    ImageStage.STAGE_00_BASE:       _create_stage_00_base_layers,
    ImageStage.STAGE_10_VARATS:     _create_stage_10_varats_layers,
    ImageStage.STAGE_20_TOOL:       _create_stage_20_tool_layers,
    ImageStage.STAGE_30_CONFIG:     _create_stage_30_config_layers,
    ImageStage.STAGE_31_CONFIG_DEV: _create_stage_31_config_dev_layers
}

_BASE_IMAGE_STAGES: tp.List[ImageStage] = [
    ImageStage.STAGE_00_BASE,
    ImageStage.STAGE_10_VARATS,
    ImageStage.STAGE_20_TOOL,
    ImageStage.STAGE_30_CONFIG
]
_DEV_IMAGE_STAGES: tp.List[ImageStage] = [
    ImageStage.STAGE_00_BASE,
    ImageStage.STAGE_10_VARATS,
    ImageStage.STAGE_31_CONFIG_DEV,
]
# yapf: enable


def _create_container_image(
    base: ImageBase, stage: ImageStage, stages: tp.List[ImageStage],
    image_name: tp.Callable[[ImageStage], str], force_rebuild: bool
) -> str:
    """
    Build/update a base image for the given image base and the current research
    tool.

    Only rebuild the given stage and subsequent stages.

    Args:
        base:  the image base
        stage: the image stage to create/update
        stages: a list of stages the complete image stack consists of
        image_name: a function that returns the image's name for a given stage
    Returns:
        the name of the final container image
    """
    # delete stages that will be (re-)created
    if force_rebuild or stage != stages[0]:
        _delete_container_image(base, stage, stages, image_name)

    name = ""
    for current_stage in stages:
        if current_stage.value >= stage.value:
            name = image_name(current_stage)
            LOG.debug(
                f"Working on image {name} "
                f"(base={base.name}, stage={current_stage})."
            )
            with StageBuilder(base, current_stage, name) as stage_builder:
                # build on previous stage if not the first
                if current_stage != stages[0]:
                    stage_builder.layers.from_(
                        image_name(stages[stages.index(current_stage) - 1])
                    )
                _STAGE_LAYERS[current_stage](stage_builder)
    return name


def _get_installable_research_tool() -> tp.Optional[ContainerInstallable]:
    if (configured_research_tool := vara_cfg()["container"]["research_tool"]):
        research_tool = get_research_tool(str(configured_research_tool))
        if isinstance(research_tool, ContainerInstallable):
            return research_tool
    return None


def _unset_varats_source_mount(image_context: StageBuilder) -> None:
    mounts = bb_cfg()["container"]["mounts"].value
    mounts[:] = [
        mount for mount in mounts
        if mount[1] != str(image_context.varats_source_mount_target)
    ]
    save_bb_config()


def _set_varats_source_mount(image_context: StageBuilder, mnt_src: str) -> None:
    bb_cfg()["container"]["mounts"].value[:] += [[
        mnt_src, str(image_context.varats_source_mount_target)
    ]]
    save_bb_config()


def _setup_venv(image_context: StageBuilder) -> None:
    venv_path = "/venv"
    image_context.layers.run("pip3", "install", "virtualenv")
    image_context.layers.run("virtualenv", venv_path)
    image_context.layers.env(VIRTUAL_ENV=venv_path)
    image_context.layers.env(PATH=f"{venv_path}/bin:$PATH")


def _add_varats_layers(image_context: StageBuilder) -> None:
    crun = bb_cfg()['container']['runtime'].value

    def from_source(
        image: ContainerImage, editable_install: bool = False
    ) -> None:
        LOG.debug('installing varats from source.')

        src_dir = Path(vara_cfg()['container']['varats_source'].value)
        tgt_dir = image_context.varats_source_mount_target

        image.run('mkdir', f'{tgt_dir}', runtime=crun)
        image.run('pip3', 'install', 'setuptools', runtime=crun)

        pip_args = ['pip3', 'install']
        if editable_install:
            pip_args.append("-e")
            _set_varats_source_mount(image_context, str(src_dir))
        mount = f'type=bind,src={src_dir},target={tgt_dir}'
        if buildah_version() >= (1, 24, 0):
            mount += ',rw'
        image.run(
            *pip_args, str(tgt_dir / 'varats-core'), mount=mount, runtime=crun
        )
        image.run(*pip_args, str(tgt_dir / 'varats'), mount=mount, runtime=crun)

    def from_pip(image: ContainerImage) -> None:
        LOG.debug("installing varats from pip release.")
        image.run(
            'pip3',
            'install',
            '--ignore-installed',
            'varats-core',
            'varats',
            runtime=crun
        )

    _unset_varats_source_mount(image_context)
    if bool(vara_cfg()['container']['dev_mode']):
        from_source(image_context.layers, editable_install=True)
    elif bool(vara_cfg()['container']['from_source']):
        from_source(image_context.layers)
    else:
        from_pip(image_context.layers)


def _add_vara_config(image_context: StageBuilder) -> None:
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


def _add_benchbuild_config(
    image_context: StageBuilder, env: tp.Dict[str, tp.List[str]]
) -> None:
    bb_env: tp.Dict[str, tp.List[str]] = defaultdict(list)
    for key, value in env.items():
        bb_env[key].extend(value)

    # copy libraries to image if LD_LIBRARY_PATH is set
    if "LD_LIBRARY_PATH" in bb_cfg()["env"].value.keys():
        image_context.layers.copy_(
            bb_cfg()["env"].value["LD_LIBRARY_PATH"],
            str(image_context.varats_root / "libs")
        )
        bb_env["LD_LIBRARY_PATH"].extend([
            str(image_context.varats_root / "libs")
        ])

    # set BB config via env vars
    image_context.layers.env(
        BB_VARATS_OUTFILE=str(image_context.varats_root / "results"),
        BB_VARATS_RESULT=str(image_context.varats_root / "BC_files"),
        BB_JOBS=str(bb_cfg()["jobs"]),
        BB_ENV=to_yaml(dict(bb_env))
    )


def create_dev_image(base: ImageBase, build_type: BuildType) -> str:
    """
    Build a dev image for the given image base and research tool.

    A dev image is used to build the research tool in the container environment.

    Args:
        base: the image base
        build_type: the build type for the research tool
    """

    def image_name(stage: ImageStage) -> str:
        return get_dev_image_name(base, stage, build_type)

    return _create_container_image(
        base, _DEV_IMAGE_STAGES[0], _DEV_IMAGE_STAGES, image_name, False
    )


def create_base_image(
    base: ImageBase, first_stage: ImageStage, force_rebuild: bool
) -> None:
    """
    Builds the given base image for the current research tool.

    Args:
        base: the base image to build
        first_stage: the first image stage in the stack that shall be built
        force_rebuild: whether to rebuild existing images
    """

    def image_name(stage: ImageStage) -> str:
        return get_image_name(base, stage, True)

    _create_container_image(
        base, first_stage, _BASE_IMAGE_STAGES, image_name, force_rebuild
    )


def create_base_images(
    images: tp.Iterable[ImageBase] = ImageBase,
    stage: ImageStage = _BASE_IMAGE_STAGES[0],
    force_rebuild: bool = False
) -> None:
    """Builds all base images for the current research tool."""
    for base in images:
        LOG.info(f"Building base image {base}.")
        create_base_image(base, stage, force_rebuild)


def get_base_image(base: ImageBase) -> ContainerImage:
    """
    Get the requested base image for the current research tool.

    Args:
        base: the base image to retrieve

    Returns:
        the requested base image
    """
    image_name = get_image_name(base, _BASE_IMAGE_STAGES[-1], True)
    return ContainerImage().from_(image_name)


def get_image_name(
    base: ImageBase, stage: ImageStage, include_tool: bool
) -> str:
    """
    Get the name for a container image.

    Args:
        base: the container's image base
        stage: the container's stage
        include_tool: whether to include the research tool name or not

    Returns:
        the container's name
    """
    name = f"{base.name.lower()}:{stage.name.lower()}"
    configured_research_tool = vara_cfg()["container"]["research_tool"]
    if include_tool and configured_research_tool:
        name += f"_{str(configured_research_tool).lower()}"
    return name


def get_dev_image_name(
    base: ImageBase, stage: ImageStage, build_type: BuildType
) -> str:
    """
    Get the name for a dev-container image.

    Args:
        base: the container's image base
        stage: the container's stage
        build_type: the build type for the research tool

    Returns:
        the dev-container's name
    """
    return f"{get_image_name(base, stage, True)}_{build_type.name.lower()}"


def _delete_container_image(
    base: ImageBase, stage: ImageStage, stages: tp.List[ImageStage],
    image_name: tp.Callable[[ImageStage], str]
) -> None:
    """
    Delete a base image.

    Args:
        base: the image base
        stage: delete this stage and all subsequent stages
        stages: a list of stages the complete image stack consists of
        image_name: a function that returns the image's name for a given stage
    """
    publish = bootstrap.bus()
    for current_stage in stages:
        if current_stage.value >= stage.value:
            name = image_name(current_stage)
            LOG.debug(
                f"Deleting image {name} "
                f"(base={base.name}, stage={current_stage})"
            )
            publish(DeleteImage(name))


def delete_base_images(
    images: tp.Iterable[ImageBase] = ImageBase,
    first_stage: ImageStage = _BASE_IMAGE_STAGES[0]
) -> None:
    """
    Deletes the selected base images.

    Args:
        images: the base images to delete
        first_stage: the first stage in the stack that should be deleted
    """
    for base in images:

        def image_name(stage: ImageStage) -> str:
            return get_image_name(base, stage, True)  # pylint: disable=W0640

        LOG.info(f"Deleting base image {base}.")
        _delete_container_image(
            base, first_stage, _BASE_IMAGE_STAGES, image_name
        )


def delete_dev_images(
    build_type: BuildType,
    images: tp.Iterable[ImageBase] = ImageBase,
    first_stage: ImageStage = _DEV_IMAGE_STAGES[0]
) -> None:
    """
    Deletes the selected dev images.

    Args:
        build_type: the build type for the research tool
        images: the dev images to delete
        first_stage: the first stage in the stack that should be deleted
    """
    for base in images:

        def image_name(stage: ImageStage) -> str:
            # pylint: disable=W0640
            return get_dev_image_name(base, stage, build_type)

        LOG.info(f"Deleting dev image {base}.")
        _delete_container_image(
            base, first_stage, _DEV_IMAGE_STAGES, image_name
        )


def export_base_image(base: ImageBase) -> None:
    """Export the base image to the filesystem."""
    publish = bootstrap.bus()
    image_name = get_image_name(base, _BASE_IMAGE_STAGES[-1], True)
    export_name = fs_compliant_name(image_name)
    export_path = Path(
        local.path(bb_cfg()["container"]["export"].value) / export_name + ".tar"
    )
    if export_path.exists() and export_path.is_file():
        export_path.unlink()
    publish(ExportImage(image_name, str(export_path)))


def export_base_images(images: tp.Iterable[ImageBase] = ImageBase) -> None:
    """Exports the selected base images."""
    for base in images:
        LOG.info(f"Exporting base image {base}.")
        export_base_image(base)


def run_container(
    image_tag: str, container_name: str, build_dir: tp.Optional[str],
    args: tp.Sequence[str]
) -> None:
    """
    Run a podman container.

    Args:
        image_tag: tag of the image to use for the container
        container_name: name for the spawned container
        build_dir: benchbuild's build directory
        args: arguments that get passed to the container's entry point
    """
    publish = bootstrap.bus()
    publish(RunProjectContainer(image_tag, container_name, build_dir, args))
