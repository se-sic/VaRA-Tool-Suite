"""Driver module for `vara-gen-bbconfig`."""

import argparse
import logging
import os
import sys

from varats.utils.bb_config import generate_benchbuild_config
from varats.utils.cli_util import cli_yn_choice
from varats.utils.settings import save_config, vara_cfg

LOG = logging.getLogger(__name__)


def main() -> None:
    """
    Main function for the benchbuild config creator.

    `vara-gen-bbconfig`
    """
    parser = argparse.ArgumentParser("vara-gen-bbconfig")
    parser.add_argument(
        "--bb-root", help="Set an alternative BenchBuild root folder."
    )

    args = parser.parse_args()
    if vara_cfg()["config_file"].value is None:
        if cli_yn_choice("Error! No VaRA config found. Should we create one?"):
            save_config()
        else:
            sys.exit()

    if args.bb_root is not None:
        if os.path.isabs(str(args.bb_root)):
            bb_root_path = str(args.bb_root)
        else:
            bb_root_path = os.path.dirname(str(vara_cfg()["config_file"])) + \
                           "/" + str(args.bb_root)

        LOG.info(f"Setting BB path to: {bb_root_path}")
        vara_cfg()["benchbuild_root"] = bb_root_path
        save_config()

    if vara_cfg()["benchbuild_root"].value is None:
        vara_cfg()["benchbuild_root"] = os.path.dirname(str(
            vara_cfg()["config_file"])) \
                                        + "/benchbuild"
        LOG.info(f"Setting BB path to: {vara_cfg()['benchbuild_root']}")
        save_config()

    generate_benchbuild_config(
        vara_cfg(),
        str(vara_cfg()["benchbuild_root"]) + "/.benchbuild.yml"
    )


if __name__ == '__main__':
    main()
