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
from varats.utils.git_util import CommitHash, FullCommitHash

LOG = logging.getLogger(__name__)


class Location:
    """A location in a source code file."""

    LOCATION_FORMAT = re.compile(
        r"(?P<file>[\w./]+)\s"
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
        raw_location: str,
        old_location: tp.Optional["Location"] = None
    ) -> "Location":
        """Create a location from a string."""
        if old_location and raw_location.isnumeric():
            new_line = int(raw_location)
            return Location(
                old_location.file, new_line, old_location.start_col, new_line,
                old_location.end_col
            )

        match = Location.LOCATION_FORMAT.match(raw_location)
        if match is None:
            raise click.UsageError(
                f"Could not parse location: {raw_location}.\n"
                f"Location format is "
                f"'<file> <start_line>:<start_col> <end_line>:<end_col>'"
            )

        return Location(
            match.group("file"), int(match.group("start_line")),
            int(match.group("start_col")), int(match.group("end_line")),
            int(match.group("end_col"))
        )

    def to_xml(self) -> str:
        """Convert the location to SPLConqueror feature model format."""
        xml = f"<path>{self.file}</path>\n"
        xml += (
            f"<start><line>{self.start_line}</line>"
            f"<column>{self.start_col}</column></start>\n"
        )
        xml += (
            f"<end><line>{self.end_line}</line>"
            f"<column>{self.end_col}</column></end>\n"
        )
        return xml

    def __str__(self) -> str:
        return (
            f"{self.file} "
            f"{self.start_line}:{self.start_col} "
            f"{self.end_line}:{self.end_col}"
        )


class FeatureAnnotation:
    """A versioned feature source annotation."""

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
        """Convert the annotation to SPLConqueror feature model format."""
        xml = "<sourceRange>\n"
        xml += "  <revisionRange>\n"
        xml += f"    <introduced>{self.introduced.hash}</introduced>\n"
        if self.removed is not None:
            xml += f"    <removed>{self.removed.hash}</removed>\n"
        xml += "  </revisionRange>\n"
        xml += textwrap.indent(self.location.to_xml(), "  ")
        xml += "</sourceRange>"

        return xml


def __prompt_location(
    feature_name: str,
    commit: Commit,
    old_location: tp.Optional[Location] = None,
    old_content: tp.Optional[str] = None
) -> tp.Tuple[Location, str]:
    commit_hash = CommitHash.from_pygit_commit(commit)

    prompt = f"Enter location for feature {feature_name} @ {commit_hash.short_hash}"
    if old_content:
        prompt += f" ({old_content})"

    parse_location = partial(
        __get_and_check_location, commit=commit, old_location=old_location
    )

    return tp.cast(
        tp.Tuple[Location, str],
        click.prompt(prompt, value_proc=parse_location)
    )


def __get_and_check_location(
    raw_location: str,
    commit: Commit,
    old_location: tp.Optional["Location"] = None
) -> tp.Tuple[Location, str]:
    location = Location.parse_string(raw_location, old_location)
    location_content = __get_location_content(commit, location)

    if not location_content:
        raise click.UsageError(
            f"The provided location does not exist or is empty."
        )

    return location, location_content


def __get_location_content(commit: Commit,
                           location: Location) -> tp.Optional[str]:
    assert location.start_line == location.end_line, \
        "Multiline locations are not supported yet."
    lines: tp.List[bytes] = tp.cast(Blob, commit.tree[location.file
                                                     ]).data.splitlines()

    if len(lines) < location.start_line:
        return None

    line: str = lines[location.start_line - 1].decode("utf-8")

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
    project: str, revision: tp.Optional[str], outfile: tp.TextIO
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

    tracked_features: dict[str, dict[int, list[FeatureAnnotation]]] = {}
    last_annotations: dict[str, dict[int, FeatureAnnotation]] = {}
    last_annotation_targets: dict[str, dict[int, str]] = {}

    LOG.debug("Current revision: %s", first_commit.id)
    while click.confirm("Annotate another feature?"):
        feature_name = click.prompt("Enter feature name to annotate", type=str)
        commit_hash = CommitHash.from_pygit_commit(first_commit)
        tracked_features[feature_name] = {}
        last_annotations[feature_name] = {}
        last_annotation_targets[feature_name] = {}

        while click.confirm(
            f"Track another location for feature '{feature_name}'?"
        ):
            annotation_id = len(tracked_features[feature_name])
            location, target = __prompt_location(feature_name, first_commit)

            tracked_features[feature_name][annotation_id] = []
            last_annotations[feature_name][annotation_id] = FeatureAnnotation(
                feature_name, location, commit_hash
            )
            last_annotation_targets[feature_name][annotation_id] = target
            click.echo(f"Tracking '{target}' at location {location}")

        click.echo()

    for commit in walker:
        commit_hash = CommitHash.from_pygit_commit(commit)
        LOG.debug("Current revision: %s", commit_hash.hash)

        for feature, annotations in last_annotations.items():
            for annotation_id, annotation in annotations.items():
                old_target = last_annotation_targets[feature][annotation_id]
                current_target = __get_location_content(
                    commit, annotation.location
                )

                if current_target != old_target:
                    LOG.debug(
                        f"{feature} @ ({annotation_id}, {annotation.location}): "
                        f"{current_target} != {old_target}"
                    )
                    # set removed field for annotation and store it
                    tracked_features[feature][annotation_id].append(
                        FeatureAnnotation(
                            annotation.feature_name, annotation.location,
                            annotation.introduced, commit_hash
                        )
                    )

                    # track new feature location
                    click.echo(
                        f"({commit_hash.short_hash}) Annotation '{old_target}' "
                        f"of feature '{feature}' has changed."
                    )
                    click.echo(f"Old location was {annotation.location}")

                    new_location, new_target = __prompt_location(
                        feature, commit, annotation.location, old_target
                    )

                    last_annotations[feature][annotation_id] = \
                        FeatureAnnotation(feature, new_location, commit_hash)
                    last_annotation_targets[feature][annotation_id] = new_target
                    click.echo(
                        f"Tracking '{new_target}' at location {new_location}"
                    )
            click.echo()

    # store remaining annotations
    for feature, annotations in last_annotations.items():
        for annotation_id, annotation in annotations.items():
            tracked_features[feature][annotation_id].append(annotation)

    click.echo(f"Final annotations written to {outfile.name}.")
    for feature, annotations in tracked_features.items():
        outfile.write(f"Annotations for feature {feature}:\n")
        for annotation_id, locations in annotations.items():
            for location in locations:
                outfile.write(location.to_xml())
                outfile.write("\n")
        outfile.write("\n\n")


if __name__ == '__main__':
    main()
