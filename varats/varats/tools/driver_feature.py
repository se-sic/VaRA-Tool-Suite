"""Driver module for `vara-feature`"""
import logging
import re
import textwrap
import typing as tp
from functools import partial

import click
from pygit2 import Walker, Commit, Blob
from pygit2.enums import SortMode

from varats.project.project_util import get_local_project_git
from varats.tools.tool_util import configuration_lookup_error_handler
from varats.ts_utils.cli_util import initialize_cli_tool
from varats.ts_utils.click_param_types import create_project_choice
from varats.utils.git_util import FullCommitHash

LOG = logging.getLogger(__name__)


class Location:
    LOCATION_FORMAT = re.compile(
        r"(?P<file>[\w.]+)\s"
        r"(?P<start_line>\d+):(?P<start_col>\d+)\s"
        r"(?P<end_line>\d+):(?P<end_col>\d+)"
    )

    def __init__(
        self, file: str, start_line: int, start_col: int, end_line: int,
        end_col: int
    ) -> None:
        self.file = file
        self.start_line = start_line
        self.start_col = start_col
        self.end_line = end_line
        self.end_col = end_col

    @staticmethod
    def parse_string(
        s: str,
        old_location: tp.Optional["Location"] = None
    ) -> tp.Optional["Location"]:
        if old_location is not None and s.isnumeric():
            new_line = int(s)
            return Location(
                old_location.file, new_line, old_location.start_col, new_line,
                old_location.end_col
            )

        match = Location.LOCATION_FORMAT.match(s)
        if match is None:
            raise click.UsageError(
                f"Could not parse location: {s}.\nLocation format is "
                f"'<file> <start_line>:<start_col> <end_line>:<end_col>'"
            )

        return Location(
            match.group("file"), int(match.group("start_line")),
            int(match.group("start_col")), int(match.group("end_line")),
            int(match.group("end_col"))
        )

    def to_xml(self) -> str:
        xml = f"<path>{self.file}</path>\n"
        xml += f"<start><line>{self.start_line}</line><column>{self.start_col}</column></start>\n"
        xml += f"<end><line>{self.end_line}</line><column>{self.end_col}</column></end>\n"
        return xml

    def __str__(self) -> str:
        return f"{self.file} {self.start_line}:{self.start_col} {self.end_line}:{self.end_col}"


class FeatureAnnotation:

    def __init__(
        self,
        feature_name: str,
        location: Location,
        introduced: FullCommitHash,
        removed: tp.Optional[FullCommitHash] = None
    ) -> None:
        self.feature_name = feature_name
        self.location = location
        self.introduced = introduced
        self.removed = removed

    def to_xml(self) -> str:
        xml = "<sourceRange>\n"
        xml += "  <revisionRange>\n"
        xml += f"    <introduced>{self.introduced.hash}</introduced>\n"
        if self.removed is not None:
            xml += f"    <removed>{self.removed.hash}</removed>\n"
        xml += "  </revisionRange>\n"
        xml += textwrap.indent(self.location.to_xml(), "  ")
        xml += "</sourceRange>"

        return xml


def prompt_location(
    feature_name: str,
    commit_hash: FullCommitHash,
    old_location: tp.Optional[Location] = None
) -> tp.Optional[Location]:
    parse_location: tp.Callable[[str], tp.Optional[Location]]
    if old_location is not None:
        parse_location = partial(
            Location.parse_string, old_location=old_location
        )
    else:
        parse_location = Location.parse_string

    return click.prompt(
        f"Enter location for feature {feature_name} @ {commit_hash.short_hash}",
        value_proc=parse_location
    )


def get_location_content(commit: Commit,
                         location: Location) -> tp.Optional[str]:
    assert location.start_line == location.end_line, \
        "Multiline locations are not supported yet."
    lines = tp.cast(Blob, commit.tree[location.file]).data.splitlines()

    if len(lines) < location.start_line:
        return None

    line = lines[location.start_line - 1].decode("utf-8")

    if len(line) <= location.end_col:
        return None

    return line[(location.start_col - 1):location.end_col]


@click.group()
@configuration_lookup_error_handler
def main() -> None:
    """Tool for working with feature models."""
    initialize_cli_tool()


@main.command("annotate")
@click.option("--project", "-p", type=create_project_choice(), required=True)
@click.option("--revision", "-r", type=str, required=False)
@click.option(
    "--outfile",
    "-o",
    type=click.File("w"),
    default=click.open_file('-', mode="w"),
    required=False
)
def __annotate(
    project: str, revision: tp.Optional[str], outfile: tp.IO
) -> None:
    initialize_cli_tool()

    repo = get_local_project_git(project)
    walker: Walker

    walker = repo.walk(
        repo.head.target, SortMode.TOPOLOGICAL | SortMode.REVERSE
    )
    walker.simplify_first_parent()

    first_commit = next(walker)
    if revision is not None:
        commit = repo.get(revision)
        while first_commit != commit:
            first_commit = next(walker)

    tracked_features: dict[str, list[FeatureAnnotation]] = {}
    last_annotations: dict[str, FeatureAnnotation] = {}
    last_annotation_targets: dict[str, str] = {}

    click.echo(f"Current revision: {first_commit.oid}")
    while click.confirm("Annotate another feature?"):
        feature_name = click.prompt("Enter feature name to annotate", type=str)
        commit_hash = FullCommitHash(str(first_commit.id))
        location = prompt_location(feature_name, commit_hash)
        last_annotations[feature_name] = FeatureAnnotation(
            feature_name, location, commit_hash
        )
        last_annotation_targets[feature_name] = get_location_content(
            first_commit, location
        )
        tracked_features[feature_name] = []
        LOG.debug(
            f"Tracking {feature_name} @ {location}: {last_annotation_targets[feature_name]}"
        )

    for commit in walker:
        commit_hash = FullCommitHash(str(commit.id))
        click.echo(f"Current revision: {commit_hash.hash}")

        for feature, annotation in last_annotations.items():
            current_target = get_location_content(commit, annotation.location)
            if current_target != last_annotation_targets[feature]:
                LOG.debug(
                    f"{feature}: {current_target} != {last_annotation_targets[feature]}"
                )
                # set removed field for annotation and store it
                tracked_features[feature].append(
                    FeatureAnnotation(
                        annotation.feature_name, annotation.location,
                        annotation.introduced, commit_hash
                    )
                )

                # track new feature location
                click.echo(f"Location of feature {feature} has changed.")
                new_location = prompt_location(
                    feature, commit_hash, annotation.location
                )
                last_annotations[feature] = FeatureAnnotation(
                    feature, new_location, commit_hash
                )
                last_annotation_targets[feature] = get_location_content(
                    commit, new_location
                )
                LOG.debug(
                    f"Tracking {feature} @ {new_location}: {last_annotation_targets[feature]}"
                )

    # store remaining annotations
    for feature, annotation in last_annotations.items():
        tracked_features[feature].append(annotation)

    click.echo(f"Final annotations written to {outfile.name}.")
    for feature, annotations in tracked_features.items():
        outfile.write(f"Annotations for feature {feature}:\n")
        for annotation in annotations:
            outfile.write(annotation.to_xml())
            outfile.write("\n")
        outfile.write("\n\n")


if __name__ == '__main__':
    main()
