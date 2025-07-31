import logging
import re
import textwrap
import typing as tp
from functools import reduce
from pathlib import Path
from xml.etree import ElementTree as ET

import click
import pygit2
from pygit2 import Commit, Blob
from virtualenv.discovery.cached_py_info import LogCmd

from varats.utils.git_util import FullCommitHash

LOG = logging.getLogger(__name__)


class Location:
    """A location in a source code file."""

    LOCATION_FORMAT = re.compile(
        r"(?P<file>[\w./]+)\s"
        r"(?P<start_line>\d+):(?P<start_col>\d+)\s?"
        r"((?P<end_line>\d+):(?P<end_col>\d+))?"
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
    def change_start_line(
        old_location: "Location",
        new_start_line: int,
    ):
        """Move the location the start of the location to a line."""
        return Location(
            old_location.file, new_start_line, old_location.start_col,
            old_location.end_line + (new_start_line - old_location.start_line),
            old_location.end_col
        )

    @staticmethod
    def move_location(old_location: "Location", line_offset: int) -> "Location":
        """Move the location by a line offset."""
        return Location.change_start_line(
            old_location, line_offset + old_location.start_line
        )

    @staticmethod
    def parse_string(
        raw_location: str,
        old_location: tp.Optional["Location"] = None
    ) -> "Location":
        """Create a location from a string."""
        if old_location and raw_location.isnumeric():
            new_line = int(raw_location)
            return Location.change_start_line(old_location, new_line)

        match = Location.LOCATION_FORMAT.match(raw_location)
        if match is None:
            raise click.UsageError(
                f"Could not parse location: {raw_location}.\n"
                f"Location format is "
                f"'<file> <start_line>:<start_col> <end_line>:<end_col>'"
            )

        return Location(
            match.group("file"), int(match.group("start_line")),
            int(match.group("start_col")),
            int(match.group("end_line"))
            if match.group("end_line") else int(match.group("start_line")),
            int(match.group("end_col")) if match.group("end_col") else None
        )

    def to_xml(self, parent) -> str:
        """Convert the location to SPLConqueror feature model format."""
        ET.SubElement(parent, "path").text = str(self.file)
        start = ET.SubElement(parent, "start")
        ET.SubElement(start, "line").text = str(self.start_line)
        ET.SubElement(start, "column").text = str(self.start_col)
        end = ET.SubElement(parent, "end")
        ET.SubElement(end, "line").text = str(self.end_line)
        ET.SubElement(end, "column").text = str(self.end_col)

    def to_xml_direct(self) -> str:
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

    def to_xml(self, parent) -> str:
        """Convert the annotation to SPLConqueror feature model format."""
        source_range = ET.SubElement(parent, "sourceRange")
        revision_range = ET.SubElement(source_range, "revisionRange")
        introduced_revision = ET.SubElement(revision_range, "introduced")
        introduced_revision.text = str(self.introduced)
        if self.removed is not None:
            removed_revision = ET.SubElement(revision_range, "removed")
            removed_revision.text = str(self.removed)
        self.location.to_xml(source_range)

    def to_xml_direct(self) -> str:
        """Convert the annotation to SPLConqueror feature model format."""
        xml = "<sourceRange>\n"
        xml += "  <revisionRange>\n"
        xml += f"    <introduced>{self.introduced.hash}</introduced>\n"
        if self.removed is not None:
            xml += f"    <removed>{self.removed.hash}</removed>\n"
        xml += "  </revisionRange>\n"
        xml += textwrap.indent(self.location.to_xml_direct(), "  ")
        xml += "</sourceRange>"

        return xml


def __get_and_check_location(
    raw_location: str,
    commit: Commit,
    old_location: tp.Optional["Location"] = None
) -> tp.Tuple[Location, str]:
    location = Location.parse_string(raw_location, old_location)
    LOG.debug(location)
    if commit.tree.__contains__(location.file):
        location_content = __get_location_content(commit, location)
    else:
        raise click.UsageError(
            f"The provided file does not exist in the repository."
        )
    if not location_content:
        raise click.UsageError(
            f"The provided location does not exist or is empty."
        )

    return location, location_content


def __get_location_content(commit: Commit,
                           location: Location) -> tp.Optional[str]:
    lines: tp.List[bytes] = tp.cast(Blob, commit.tree[location.file
                                                     ]).data.splitlines()
    if len(lines) < location.start_line:
        LOG.debug(
            "Location start_line is larger than number of lines in file, returning None."
        )
        return None
    # Handling of multiline locations
    if location.start_line != location.end_line:
        content = reduce(
            lambda x, y: x + "\n" + y.decode("utf-8"),
            lines[location.start_line:location.end_line - 1],
            lines[location.start_line - 1].decode("utf-8")[location.start_col -
                                                           1:]
        )
        content += "\n" + lines[location.end_line -
                                1].decode("utf-8")[:location.end_col]
        LOG.debug(
            "Location spans multiple lines, returning content from "
            f"{location.start_line} to {location.end_line}."
        )
        return content
    # Handling of single line locations
    line: str = lines[location.start_line - 1].decode("utf-8")
    LOG.debug(
        "Location spans a single line, returning content from "
        f"{line}"
    )
    if not location.end_col:
        LOG.debug("No end_col specified, assuming single word selection.")
        # If no end_col is specified, we assume just one word is selected
        if len(line) < location.start_col:
            LOG.debug(
                "Location start_col is larger than line length, returning None."
            )
            return None
        word = line[location.start_col - 1:]
        location.end_col = word.split()[0].__len__() + location.start_col - 2
        LOG.debug(f"End column set to {location.end_col}.")
    # Todo Why is this end_col and not start_col?
    if len(line) <= location.end_col:
        LOG.debug(
            f"Location end_col is larger than line length {len(line)}, returning None."
        )
        return None

    return line[(location.start_col - 1):location.end_col]


def __find_potential_new_locations(
    repo: pygit2.Repository, commit, annotation: FeatureAnnotation,
    old_target: str
) -> tp.List[tp.Tuple[Location, str]]:
    potential_new_locations: tp.List[tp.Tuple[Location, str]] = []
    for parent in commit.parents:
        diff = repo.diff(parent, commit)
        for patch in diff:
            if patch.delta.old_file.path == annotation.location.file:
                offset_counter = 0
                stop_offset = False
                for hunk in patch.hunks:
                    for line in hunk.lines:
                        if line.old_lineno > annotation.location.end_line:
                            stop_offset = True
                        if line.new_lineno >= 0:
                            if line.old_lineno < 0:
                                if not stop_offset:
                                    offset_counter += 1
                            if annotation.location.end_line == annotation.location.start_line:
                                content = line.content[
                                    annotation.location.start_col -
                                    1:annotation.location.end_col]
                            else:
                                content = line.content[annotation.location.
                                                       start_col - 1:]
                            if old_target == content:
                                potential_new_locations.append((
                                    Location.change_start_line(
                                        annotation.location, line.new_lineno
                                    ), content
                                ))
                        else:
                            if not stop_offset:
                                offset_counter -= 1

                potential_new_location = Location.move_location(
                    annotation.location, offset_counter
                )
                potential_new_content = __get_location_content(
                    commit, potential_new_location
                )
                if potential_new_content == old_target:
                    potential_new_locations.append(
                        (potential_new_location, potential_new_content)
                    )
    return potential_new_locations


def update_feature_model(
    path: Path, annotations: dict[str, dict[int, list[FeatureAnnotation]]]
):
    tree = ET.parse(str(path))
    root = tree.getroot()
    for feature in root.iter("configurationOption"):
        if annotations.__contains__(feature.find("name").text):
            annotation_dict = annotations.pop(feature.find("name").text)
            locations = feature.find("locations")
            for annotation_id, annotation_list in annotation_dict.items():
                for annotation in annotation_list:
                    annotation.to_xml(locations)
    tree.write(str(path))
    click.echo("Feature model updated.")
    if annotations:
        click.echo(
            "The following features were not found in the feature model: "
            f"{', '.join(annotations.keys())}"
        )


def load_initial_annotations(
    file: tp.TextIO,
    revision: pygit2.Commit,
) -> tuple[dict[str, dict[int, list[FeatureAnnotation]]], dict[str, dict[
    int, FeatureAnnotation]], dict[str, dict[int, str]]]:
    """Load initial annotations from a file."""
    current_feature: tp.Optional[str] = None
    tracked_features: dict[str, dict[int, list[FeatureAnnotation]]] = {}
    last_annotations: dict[str, dict[int, FeatureAnnotation]] = {}
    last_annotation_targets: dict[str, dict[int, str]] = {}
    commit_hash = FullCommitHash.from_pygit_commit(revision)
    for line in file.readlines():
        LOG.debug(f"Processing line: {line.strip()}")
        line = line.strip()
        if line == "":
            continue
        if line.endswith(":"):
            current_feature = line[:-1]
            if current_feature not in tracked_features:
                tracked_features[current_feature] = {}
                last_annotations[current_feature] = {}
                last_annotation_targets[current_feature] = {}
            continue
        if current_feature is None:
            raise click.UsageError(
                "Annotations file is not formatted correctly. "
                "It must start with a feature directive."
            )
        annotation_id = len(tracked_features[current_feature])
        location, target = __get_and_check_location(line, revision)
        tracked_features[current_feature][annotation_id] = []
        last_annotations[current_feature][annotation_id] = FeatureAnnotation(
            current_feature, location, commit_hash
        )
        last_annotation_targets[current_feature][annotation_id] = target
    return tracked_features, last_annotations, last_annotation_targets
