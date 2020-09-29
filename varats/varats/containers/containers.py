import typing as tp
from enum import Enum

from benchbuild.environments.domain import declarative, commands
from benchbuild.environments.service_layer import messagebus, unit_of_work


class ImageBase(Enum):
    DEBIAN_10 = "debian:10"


__BASE_IMAGES: tp.Dict[ImageBase, declarative.ContainerImage] = {
    ImageBase.DEBIAN_10:
        declarative.ContainerImage().from_("debian:10").run('apt',
                                                            'update').run(
                                                                'apt',
                                                                'install', '-y',
                                                                'python3',
                                                                'python3-dev',
                                                                'python3-pip',
                                                                'musl-dev',
                                                                'git', 'gcc',
                                                                'libgit2-dev',
                                                                'libffi-dev'
                                                            )
}


def add_varats_layers(
    layers: declarative.ContainerImage
) -> declarative.ContainerImage:
    # crun = str(CFG['container']['runtime'])
    # src_dir = str(CFG['container']['source'])
    # tgt_dir = '/benchbuild'

    # def from_source(image: ContainerImage) -> None:
    #     LOG.debug('installing benchbuild from source.')
    #     LOG.debug('src_dir: %s tgt_dir: %s', src_dir, tgt_dir)
    #
    #     # The image requires git, pip and a working python3.7 or better.
    #     image.run('mkdir', f'{tgt_dir}', runtime=crun)
    #     image.run('pip3', 'install', 'setuptools', runtime=crun)
    #     image.run(
    #         'pip3',
    #         'install',
    #         '--ignore-installed',
    #         tgt_dir,
    #         mount=f'type=bind,src={src_dir},target={tgt_dir}',
    #         runtime=crun
    #     )

    def from_pip(
        image: declarative.ContainerImage
    ) -> declarative.ContainerImage:
        # LOG.debug('installing benchbuild from pip release.')
        return image.run('pip3', 'install', 'varats-core', 'varats')

    # if bool(CFG['container']['from_source']):
    #     from_source(layers)
    # else:
    #     from_pip(layers)
    return from_pip(layers).run('vara-gen-bb-config')


# TODO: create tool that builds all base images
def create_base_image(base: ImageBase) -> None:
    image = __BASE_IMAGES[base]
    declarative.add_benchbuild_layers(image)
    add_varats_layers(image)
    # TODO: add active research tool layers and adjust image name
    cmd: commands.Command = commands.CreateImage(base.value, image)
    uow = unit_of_work.BuildahUnitOfWork()
    messagebus.handle(cmd, uow)


def get_base_image(base: ImageBase) -> declarative.ContainerImage:
    create_base_image(base)
    # TODO: select base image via active research tool
    return declarative.ContainerImage().from_(base.value)
