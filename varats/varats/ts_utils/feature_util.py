"""Utilities for handling feature annotations in source code files."""

import logging
import re
import textwrap
import typing as tp
from pathlib import Path
from xml.etree import ElementTree

import click
import pygit2
from pygit2 import Blob, Commit, Patch

from varats.utils.git_util import UNCOMMITTED_COMMIT_HASH, FullCommitHash

LOG = logging.getLogger(__name__)


OutTy = tp.TypeVar('OutTy')


def _xml_extract(
    xml_element: ElementTree.Element,
    xml_path: str,
    convert: tp.Callable[[str], OutTy] = lambda x: x,
) -> OutTy | None:
    if (
        found := xml_element.find(xml_path)
    ) is not None and found.text is not None:
        return convert(found.text)
    return None


class Location:
    """A location in a source code file."""

    LOCATION_FORMAT = re.compile(
        r"(?P<file>[\w./]+)\s"
        r"(?P<start_line>\d+):(?P<start_col>\d+)"
        r"(\s(?P<end_line>\d+):(?P<end_col>\d+))?"
        r"(\s(?P<member_offset>[\w:]+))?"
    )

    def __init__(
        self,
        file: str,
        start_line: int,
        start_col: int,
        end_line: int,
        end_col: int | None,
        member_offset: str | None = None,
    ) -> None:
        """Creates a feature location."""
        self.file = file
        self.start_line = start_line
        self.start_col = start_col
        self.end_line = end_line
        self.end_col = end_col
        self.member_offset = member_offset

    @staticmethod
    def change_start_line(
        old_location: "Location",
        new_start_line: int,
    ) -> "Location":
        """Move the location the start of the location to a line."""
        return Location(
            old_location.file,
            new_start_line,
            old_location.start_col,
            old_location.end_line + (new_start_line - old_location.start_line),
            old_location.end_col,
            old_location.member_offset,
        )

    @staticmethod
    def move_location(old_location: "Location", line_offset: int) -> "Location":
        """Move the location by a line offset."""
        return Location.change_start_line(
            old_location, line_offset + old_location.start_line
        )

    @staticmethod
    def parse_string(
        raw_location: str, old_location: tp.Optional["Location"] = None
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
                f"'<file> <start_line>:<start_col> <end_line>:<end_col> "
                f"<member_offset>'"
            )

        return Location(
            match["file"],
            int(match["start_line"]),
            int(match["start_col"]),
            int(match["end_line"])
            if match["end_line"]
            else int(match["start_line"]),
            int(match["end_col"]) if match["end_col"] else None,
            match["member_offset"],
        )

    def to_xml(self, parent: ElementTree.Element) -> None:
        """Convert the location to SPLConqueror feature model format."""
        ElementTree.SubElement(parent, "path").text = str(self.file)
        start = ElementTree.SubElement(parent, "start")
        ElementTree.SubElement(start, "line").text = str(self.start_line)
        ElementTree.SubElement(start, "column").text = str(self.start_col)
        end = ElementTree.SubElement(parent, "end")
        ElementTree.SubElement(end, "line").text = str(self.end_line)
        ElementTree.SubElement(end, "column").text = str(self.end_col)
        if self.member_offset:
            ElementTree.SubElement(
                parent, "memberOffset"
            ).text = self.member_offset

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
        if self.member_offset:
            xml += f"<memberOffset>{self.member_offset}</memberOffset>\n"
        return xml

    @staticmethod
    def from_xml(source_range: ElementTree.Element) -> "Location | None":
        """Creates a location object from XML."""
        file = _xml_extract(source_range, "./path")
        start_line = _xml_extract(source_range, "./start/line", int)
        start_col = _xml_extract(source_range, "./start/column", int)
        end_line = _xml_extract(source_range, "./end/line", int)
        end_col = _xml_extract(source_range, "./end/column", int)
        member_offset = _xml_extract(source_range, "./memberOffset")

        if file is None or start_line is None or start_col is None:
            return None

        if end_line is None:
            end_line = start_line

        return Location(
            file, start_line, start_col, end_line, end_col, member_offset
        )

    def __str__(self) -> str:
        """String representation of the location."""
        member_offset_str = ""
        if self.member_offset:
            member_offset_str = " " + self.member_offset

        return (
            f"{self.file} "
            f"{self.start_line}:{self.start_col} "
            f"{self.end_line}:{self.end_col}"
            f"{member_offset_str}"
        )

    def __repr__(self) -> str:
        """String representation of the location."""
        return self.__str__()


class FeatureAnnotation:
    """A versioned feature source annotation."""

    def __init__(
        self,
        feature_name: str,
        location: Location,
        introduced: FullCommitHash,
        removed: FullCommitHash | None = None,
    ) -> None:
        """Creates a feature annotation."""
        self.feature_name = feature_name
        self.location = location
        self.introduced = introduced
        self.removed = removed

    def to_xml(self, parent: ElementTree.Element) -> None:
        """Convert the annotation to SPLConqueror feature model format."""
        source_range = ElementTree.SubElement(parent, "sourceRange")
        revision_range = ElementTree.SubElement(source_range, "revisionRange")
        introduced_revision = ElementTree.SubElement(
            revision_range, "introduced"
        )
        introduced_revision.text = str(self.introduced)
        if self.removed is not None:
            removed_revision = ElementTree.SubElement(revision_range, "removed")
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

    def __str__(self) -> str:
        """String representation of the annotation."""
        commit_range = f"{self.introduced.short_hash}"
        if self.removed is not None:
            commit_range += f"..{self.removed.short_hash}"

        return f"{self.feature_name}@[{range}] {self.location}"

    def __repr__(self) -> str:
        """String representation of the annotation."""
        return self.__str__()

    @staticmethod
    def from_xml(
        feature_name: str, source_range: ElementTree.Element
    ) -> "FeatureAnnotation | None":
        """Parses a feature annotation from XML."""
        location = Location.from_xml(source_range)
        if location is None:
            return None

        introduced = (
            _xml_extract(
                source_range, "./revisionRange/introduced", FullCommitHash
            )
            or UNCOMMITTED_COMMIT_HASH
        )
        removed = _xml_extract(
            source_range, "./revisionRange/removed", FullCommitHash
        )

        return FeatureAnnotation(feature_name, location, introduced, removed)


def __get_and_check_location(
    raw_location: str,
    commit: Commit,
    old_location: tp.Optional["Location"] = None,
) -> tuple[Location, str]:
    location = Location.parse_string(raw_location, old_location)
    if location.file in commit.tree:
        location_content = __get_location_content(commit, location)
    else:
        raise click.UsageError(
            "The provided file does not exist in the repository."
        )
    if not location_content:
        raise click.UsageError(
            "The provided location does not exist or is empty."
        )

    return location, location_content


def __get_location_content(commit: Commit, location: Location) -> str | None:
    lines: list[bytes] = tp.cast(
        "Blob", commit.tree[location.file]
    ).data.splitlines()
    if len(lines) < location.end_line:
        LOG.debug(
            "Location end_line is larger than number of lines in file,"
            " returning None."
        )
        return None

    # Handling of multiline locations
    if location.start_line != location.end_line:
        relevant_lines = [
            line.decode("utf-8")
            for line in lines[location.start_line - 1 : location.end_line - 1]
        ]
        relevant_lines[0] = relevant_lines[0][location.start_col - 1 :]
        relevant_lines[-1] = relevant_lines[-1][: location.end_col]
        LOG.debug(
            "Location spans multiple lines, returning content from "
            f"{location.start_line} to {location.end_line}."
        )
        return "\n".join(relevant_lines)

    # Handling of single line locations
    line: str = lines[location.start_line - 1].decode("utf-8")
    LOG.debug(f"Location spans a single line, returning content from {line}")

    if location.end_col is None:
        LOG.debug("No end_col specified, assuming single word selection.")
        # If no end_col is specified, we assume just one word is selected
        if len(line) < location.start_col:
            LOG.debug(
                "Location start_col is larger than line length, returning None."
            )
            return None
        word = line[location.start_col - 1 :]
        location.end_col = len(word.split()[0]) + location.start_col - 2
        LOG.debug(f"End column set to {location.end_col}.")

    if len(line) <= location.end_col:
        LOG.debug(
            f"Location end_col is larger than line length {len(line)},"
            f" returning None."
        )
        return None

    return line[location.start_col - 1 : location.end_col]


def __process_patch(
    location: Location, commit: Commit, old_target: str, patch: Patch
) -> list[tuple[Location, str]]:
    """Process a patch and return potential new locations for a feature."""
    potential_new_locations: list[tuple[Location, str]] = []
    offset_counter = 0
    for hunk in patch.hunks:
        for line in hunk.lines:
            if line.new_lineno >= 0:  # Added or modified line
                if line.old_lineno < 0 and line.old_lineno < location.end_line:
                    # Added line if we are before the location, increase offset
                    offset_counter += 1

                if location.end_line == location.start_line:
                    content = line.content[
                        location.start_col - 1 : location.end_col
                    ]
                else:
                    content = line.content[location.start_col - 1 :]
                if old_target == content:
                    potential_new_locations.append(
                        (
                            Location.change_start_line(
                                location, line.new_lineno
                            ),
                            content,
                        )
                    )

            else:
                # Deleted line if we are before the location, decrease offset
                if line.old_lineno < location.end_line:
                    offset_counter -= 1
    # Check location based on the offset calculated from the diff.
    # The line may not be in the diff as it was not changed,
    # but moved because of the diff.
    potential_new_location = Location.move_location(location, offset_counter)
    potential_new_content = __get_location_content(
        commit, potential_new_location
    )
    if potential_new_content == old_target:
        potential_new_locations.append(
            (potential_new_location, potential_new_content)
        )
    return potential_new_locations


def __find_potential_new_locations(
    repo: pygit2.Repository,
    commit: Commit,
    current_location: Location,
    old_target: str,
) -> list[tuple[Location, str]]:
    """Find potential new locations for a feature annotation."""
    potential_new_locations: list[tuple[Location, str]] = []
    for parent in commit.parents:
        diff = repo.diff(parent, commit)
        for patch in diff:
            if (
                patch is not None
                and patch.delta.old_file.path == current_location.file
            ):
                potential_new_locations.extend(
                    __process_patch(current_location, commit, old_target, patch)
                )
    return potential_new_locations


def update_feature_model(
    path: Path, annotations: dict[str, dict[int, list[FeatureAnnotation]]]
) -> None:
    """Update the feature model at the given path based on the annotations."""
    tree = ElementTree.parse(str(path))
    root = tree.getroot()
    for feature in root.iter("configurationOption"):
        xml_feature = feature.find("name")
        if xml_feature and xml_feature.text in annotations:
            annotation_dict = annotations.pop(xml_feature.text)
            locations = feature.find("locations")
            if locations:
                for _, annotation_list in annotation_dict.items():
                    for annotation in annotation_list:
                        annotation.to_xml(locations)
    tree.write(str(path))
    click.echo("Feature model updated.")
    if annotations:
        click.echo(
            "The following features were not found in the feature model: "
            f"{', '.join(annotations.keys())}"
        )


def load_feature_model(
    fm_file: tp.TextIO,
) -> dict[str, list[FeatureAnnotation]]:
    """Load initial annotations from a feature model."""
    annotations: dict[str, list[FeatureAnnotation]] = {}

    tree = ElementTree.parse(fm_file)
    root = tree.getroot()
    for feature in root.iter("configurationOption"):
        if (xml_feature := feature.find("./name")) is not None:
            feature_name = xml_feature.text
            if feature_name is None:
                LOG.warning(f"Feature has no name: {xml_feature.text}")
                continue

            feature_annotations: list[FeatureAnnotation] = []
            if (locations := feature.find("./locations")) is not None:
                for source_range in locations.iter("sourceRange"):
                    if (
                        annotation := FeatureAnnotation.from_xml(
                            feature_name, source_range
                        )
                    ) is not None:
                        feature_annotations.append(annotation)
            annotations[feature_name] = feature_annotations

    return annotations
