"""Driver module for `vara-gen-bbconfig`."""

import logging
import os
import sys
import typing as tp

import click

from varats.tools.bb_config import create_new_bb_config
from varats.ts_utils.cli_util import cli_yn_choice
from varats.utils.settings import save_config, vara_cfg, save_bb_config

LOG = logging.getLogger(__name__)


@click.command()
@click.option(
    "--bb-root",
    type=click.Path(),
    help="Set an alternative BenchBuild root folder."
)
@click.option("--test-projects", is_flag=True, help="Include test projects")
def main(bb_root: tp.Optional[str] = None, test_projects: bool = False) -> None:
    """
    Main function for the benchbuild config creator.

    `vara-gen-bbconfig`
    """
    if vara_cfg()["config_file"].value is None:
        if cli_yn_choice("Error! No VaRA config found. Should we create one?"):
            save_config()
        else:
            sys.exit()

    if bb_root is not None:
        if os.path.isabs(str(bb_root)):
            bb_root_path = str(bb_root)
        else:
            bb_root_path = os.path.dirname(str(vara_cfg()["config_file"])) + \
                           "/" + str(bb_root)

        LOG.info(f"Setting BB path to: {bb_root_path}")
        vara_cfg()["benchbuild_root"] = bb_root_path
        save_config()

    if vara_cfg()["benchbuild_root"].value is None:
        vara_cfg()["benchbuild_root"] = os.path.dirname(str(
            vara_cfg()["config_file"])) \
                                        + "/benchbuild"
        LOG.info(f"Setting BB path to: {vara_cfg()['benchbuild_root']}")
        save_config()

    bb_cfg = create_new_bb_config(vara_cfg(), test_projects)
    save_bb_config(bb_cfg)


if __name__ == '__main__':
    main()
