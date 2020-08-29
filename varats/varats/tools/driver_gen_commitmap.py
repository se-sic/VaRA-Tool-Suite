"""Driver module for `vara-gen-commitmap`."""

import argparse
from pathlib import Path

from varats.tools.commit_map import get_commit_map, store_commit_map
from varats.utils.cli_util import initialize_cli_tool
from varats.utils.settings import vara_cfg


def main() -> None:
    """Create a commit map for a repository."""
    initialize_cli_tool()
    parser = argparse.ArgumentParser("vara-gen-commitmap")
    parser.add_argument("project_name", help="Name of the project")
    parser.add_argument("--path", help="Path to git repository", default=None)
    parser.add_argument(
        "--end", help="End of the commit range (inclusive)", default="HEAD"
    )
    parser.add_argument(
        "--start", help="Start of the commit range (exclusive)", default=None
    )
    parser.add_argument("-o", "--output", help="Output filename")

    args = parser.parse_args()

    if args.path is None:
        path = None
    elif args.path.endswith(".git"):
        path = Path(args.path[:-4])
    else:
        path = Path(args.path)

    if path is not None and not path.exists():
        raise argparse.ArgumentTypeError("Repository path does not exist")

    cmap = get_commit_map(args.project_name, path, args.end, args.start)

    if args.output is None:
        if path is not None:
            default_name = path.name.replace("-HEAD", "")
        else:
            default_name = args.project_name

        output_name = "{result_folder}/{project_name}/{file_name}.cmap" \
            .format(
            result_folder=vara_cfg()["result_dir"],
            project_name=default_name,
            file_name=default_name)
    else:
        if args.output.endswith(".cmap"):
            output_name = args.output
        else:
            output_name = args.output + ".cmap"
    store_commit_map(cmap, output_name)


if __name__ == '__main__':
    main()
