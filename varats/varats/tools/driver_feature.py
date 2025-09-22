"""Driver module for `vara-feature`"""
import logging
import typing as tp
from functools import partial
from pathlib import Path

import click
from pygit2 import Walker, Commit, Repository
from pygit2.enums import SortMode

from varats.project.project_util import get_local_project_repo
from varats.tools.tool_util import configuration_lookup_error_handler
from varats.ts_utils.cli_util import initialize_cli_tool
from varats.ts_utils.click_param_types import create_project_choice
from varats.ts_utils.feature_util import (
    Location,
    __get_and_check_location,
    FeatureAnnotation,
    __get_location_content,
    __find_potential_new_locations,
    update_feature_model,
    load_initial_annotations,
)
from varats.utils.git_util import CommitHash

LOG = logging.getLogger(__name__)


def __prompt_location(
    feature_name: str,
    commit: Commit,
    old_location: tp.Optional[Location] = None,
    prompt: tp.Optional[str] = None,
    default: tp.Optional[str] = None
) -> tp.Tuple[Location, str]:
    commit_hash = CommitHash.from_pygit_commit(commit)
    if prompt is None:
        prompt = (
            f"Enter location for feature {feature_name} @"
            f" {commit_hash.short_hash}"
        )

    parse_location = partial(
        __get_and_check_location, commit=commit, old_location=old_location
    )

    return tp.cast(
        tp.Tuple[Location, str],
        click.prompt(prompt, default=default, value_proc=parse_location)
    )


def get_pygit_commit(project: str, revision=None):
    """Get a pygit commit for a project7."""
    repo = get_local_project_repo(project).pygit_repo
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
    return first_commit


@click.group()
@configuration_lookup_error_handler
def main() -> None:
    """Tool for working with feature models."""
    initialize_cli_tool()


@main.command("annotate")
@click.option("--project", "-p", type=create_project_choice(), required=True)
@click.option("--revision", "-r", type=str, required=False)
@click.option(
    "--infile", "-i", type=click.File("r"), default=None, required=False
)
@click.option(
    "--outfile",
    "-o",
    type=click.File("w"),
    default=click.open_file('-', mode="w"),
    required=False
)
def __annotate(
    project: str, revision: tp.Optional[str], infile: tp.Optional[tp.TextIO],
    outfile: tp.TextIO
) -> None:
    initialize_cli_tool()
    repo = get_local_project_repo(project).pygit_repo
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

    tracked_features: dict[str, dict[int, list[FeatureAnnotation]]]
    last_annotations: dict[str, dict[int, FeatureAnnotation]]
    last_annotation_targets: dict[str, dict[int, str]]

    if infile is not None:
        LOG.debug(f"Reading existing annotations from {infile.name}")
        tracked_features, last_annotations, last_annotation_targets =\
            load_initial_annotations(
            infile, first_commit
        )
        LOG.debug(
            f"Loaded {len(tracked_features)} tracked features from "
            f"{infile.name}."
        )
    else:
        tracked_features = {}
        last_annotations = {}
        last_annotation_targets = {}

    LOG.debug(f"Current revision: {first_commit.id}")

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

    tracked_features = track_annotations(
        last_annotation_targets, last_annotations, repo, tracked_features,
        walker
    )
    write_annotations(outfile, tracked_features)


def track_annotations(
    last_annotation_targets: dict[str, dict[int, str]],
    last_annotations: dict[str, dict[int, FeatureAnnotation]], repo: Repository,
    tracked_features: dict[str, dict[int,
                                     list[FeatureAnnotation]]], walker: Walker
) -> dict[str, dict[int, list[FeatureAnnotation]]]:
    """Track the given annotations through the given walker and write the
    results to the given output file."""
    for commit in walker:
        commit_hash = CommitHash.from_pygit_commit(commit)
        LOG.debug(f"Current revision: {commit_hash.hash}",)
        for feature, annotations in last_annotations.items():
            for annotation_id, annotation in annotations.items():
                old_target = last_annotation_targets[feature][annotation_id]
                current_target = __get_location_content(
                    commit, annotation.location
                )

                if current_target != old_target:
                    LOG.debug(
                        f"{feature} @ ({annotation_id}, {annotation.location}):"
                        f" {current_target} != {old_target}"
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
                        f"[{feature} @ {commit_hash.short_hash}] "
                        f"Annotation changed for '{old_target}'."
                    )
                    click.echo(f"Old location: {annotation.location}")
                    potential_new_locations = __find_potential_new_locations(
                        repo, commit, annotation, old_target
                    )
                    # Determine potential new location
                    if potential_new_locations:
                        potential_new_locations.sort(
                            key=lambda x: x[0].start_line - annotation.location.
                            start_line
                        )
                        best_candidate = potential_new_locations[0]
                    new_location, new_target = __prompt_location(
                        feature,
                        commit,
                        annotation.location,
                        "New location: ",
                        default=f"{best_candidate[0]}:{best_candidate[1]}"
                        if potential_new_locations else None
                    )

                    last_annotations[feature][annotation_id] = \
                        FeatureAnnotation(feature, new_location, commit_hash)
                    last_annotation_targets[feature][annotation_id] = new_target

                    if new_target != old_target:
                        click.echo(
                            f"Symbol changed. Tracking as '{new_target}'."
                        )
            click.echo()

    # store remaining annotations
    for feature, annotations in last_annotations.items():
        for annotation_id, annotation in annotations.items():
            tracked_features[feature][annotation_id].append(annotation)

    return tracked_features


def write_annotations(
    outfile: tp.TextIO,
    tracked_features: dict[str, dict[int, list[FeatureAnnotation]]]
) -> None:
    """Write the given annotations to the given output file."""
    if not Path(str(outfile.name)).exists():
        for feature, annotations in tracked_features.items():
            outfile.write(f"Annotations for feature {feature}:\n")
            for _, locations in annotations.items():
                for location in locations:
                    outfile.write(location.to_xml_direct())
                    outfile.write("\n")
                outfile.write("\n")
            outfile.write("\n")
    else:
        update_feature_model(Path(outfile.name), tracked_features)
    click.echo(f"Final annotations written to {outfile.name}.")


if __name__ == '__main__':
    main()
