"""Driver module for `vara-gen-bbconfig`."""

import argparse
import logging
import os
import sys

from varats.settings import (
    generate_benchbuild_config,
    save_config,
    get_vara_config,
)
from varats.utils.cli_util import cli_yn_choice

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
    cfg = get_vara_config()

    if cfg["config_file"].value is None:
        if cli_yn_choice("Error! No VaRA config found. Should we create one?"):
            save_config()
        else:
            sys.exit()

    if args.bb_root is not None:
        if os.path.isabs(str(args.bb_root)):
            bb_root_path = str(args.bb_root)
        else:
            bb_root_path = os.path.dirname(str(cfg["config_file"])) + \
                           "/" + str(args.bb_root)

        LOG.info(f"Setting BB path to: {bb_root_path}")
        cfg["benchbuild_root"] = bb_root_path
        save_config()

    if cfg["benchbuild_root"].value is None:
        cfg["benchbuild_root"] = os.path.dirname(str(cfg["config_file"])) \
                                   + "/benchbuild"
        LOG.info(f"Setting BB path to: {cfg['benchbuild_root']}")
        save_config()

    generate_benchbuild_config(
        cfg,
        str(cfg["benchbuild_root"]) + "/.benchbuild.yml"
    )


if __name__ == '__main__':
    main()
