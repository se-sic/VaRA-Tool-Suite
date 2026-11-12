"""Driver module for `vara-feature`."""

import logging
import typing as tp
from functools import partial
from pathlib import Path

import click
from pygit2 import Commit, Walker
from pygit2.enums import SortMode

from varats.project.project_util import get_local_project_repo
from varats.tools.tool_util import configuration_lookup_error_handler
from varats.ts_utils.cli_util import initialize_cli_tool
from varats.ts_utils.click_param_types import create_project_choice
from varats.ts_utils.feature_util import (
    FeatureAnnotation,
    Location,
    find_potential_new_locations,
    get_and_check_location,
    get_location_content,
    load_feature_model,
    update_feature_model,
)
from varats.utils.git_util import CommitHash, RepositoryHandle

LOG = logging.getLogger(__name__)


def __prompt_location(
    feature_name: str,
    commit: Commit,
    old_location: Location | None = None,
    prompt: str | None = None,
    default: str | None = None,
) -> tuple[Location, str]:
    commit_hash = CommitHash.from_pygit_commit(commit)
    if prompt is None:
        prompt = (
            f"Enter location for feature {feature_name} @"
            f" {commit_hash.short_hash}"
        )

    parse_location = partial(
        get_and_check_location, commit=commit, old_location=old_location
    )

    return click.prompt(prompt, default=default, value_proc=parse_location)


@click.group()
@configuration_lookup_error_handler
def main() -> None:
    """Tool for working with feature models."""
    initialize_cli_tool()


@main.command("annotate")
@click.option("--project", "-p", type=create_project_choice(), required=True)
@click.option("--revision", "-r", type=str, required=False)
@click.option(
    "--infile",
    "-i",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    required=False,
    help="Feature model to add the new annotations to.",
)
@click.option(
    "--outfile",
    "-o",
    type=click.File("w"),
    default=click.open_file('-', mode="w", lazy=True),
    required=False,
)
def __annotate(
    project: str,
    revision: str | None,
    infile: Path | None,
    outfile: tp.TextIO,
) -> None:
    initialize_cli_tool()
    repo = get_local_project_repo(project)
    walker: Walker

    walker = repo.pygit_repo.walk(
        repo.pygit_repo.head.target, SortMode.TOPOLOGICAL | SortMode.REVERSE
    )
    walker.simplify_first_parent()

    first_commit = next(walker)
    if revision is not None:
        commit = repo.pygit_commit(revision)
        while first_commit != commit:
            first_commit = next(walker)

    tracked_features: dict[str, dict[int, list[FeatureAnnotation]]] = {}
    last_annotations: dict[str, dict[int, FeatureAnnotation]] = {}
    last_annotation_targets: dict[str, dict[int, str]] = {}

    feature_type = click.STRING
    if infile is not None:
        feature_type = click.Choice(list(load_feature_model(infile)))

    LOG.debug(f"Current revision: {first_commit.id}")

    while click.confirm("Annotate another feature?"):
        feature_name = click.prompt(
            "Enter feature name to annotate", type=feature_type
        )
        commit_hash = CommitHash.from_pygit_commit(first_commit)
        tracked_features.setdefault(feature_name, {})
        last_annotations.setdefault(feature_name, {})
        last_annotation_targets.setdefault(feature_name, {})

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
        last_annotation_targets,
        last_annotations,
        repo,
        tracked_features,
        walker,
    )
    write_annotations(outfile, tracked_features, infile)


def track_annotations(
    last_annotation_targets: dict[str, dict[int, str]],
    last_annotations: dict[str, dict[int, FeatureAnnotation]],
    repo: RepositoryHandle,
    tracked_features: dict[str, dict[int, list[FeatureAnnotation]]],
    walker: Walker,
) -> dict[str, dict[int, list[FeatureAnnotation]]]:
    """
    Track the given annotations through the history of the given walker.

    The user is prompted for new locations whenever an annotation's target
    changes.
    """
    for commit in walker:
        commit_hash = CommitHash.from_pygit_commit(commit)
        LOG.debug(
            f"Current revision: {commit_hash.hash}",
        )
        for feature, annotations in last_annotations.items():
            for annotation_id, annotation in annotations.items():
                old_target = last_annotation_targets[feature][annotation_id]
                current_target = get_location_content(
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
                            annotation.feature_name,
                            annotation.location,
                            annotation.introduced,
                            commit_hash,
                        )
                    )

                    # track new feature location
                    click.echo(
                        f"\n[{feature} @ {commit_hash.short_hash}] "
                        f"Annotation changed for '{old_target}'."
                    )
                    click.echo(f"Old location: {annotation.location}")
                    potential_new_locations = find_potential_new_locations(
                        repo.pygit_repo, commit, annotation.location, old_target
                    )
                    # Determine potential new location
                    best_candidate: tuple[Location, str] | None = None
                    if potential_new_locations:
                        potential_new_locations.sort(
                            key=lambda x: (
                                x[0].start_line - annotation.location.start_line
                            )
                        )
                        best_candidate = potential_new_locations[0]
                    new_location, new_target = __prompt_location(
                        feature,
                        commit,
                        annotation.location,
                        "New location: ",
                        default=f"{best_candidate[0]}:{best_candidate[1]}"
                        if best_candidate
                        else None,
                    )

                    last_annotations[feature][annotation_id] = (
                        FeatureAnnotation(feature, new_location, commit_hash)
                    )
                    last_annotation_targets[feature][annotation_id] = new_target

                    if new_target != old_target:
                        click.echo(
                            f"Symbol changed. Tracking as '{new_target}'."
                        )

    # store remaining annotations
    for feature, annotations in last_annotations.items():
        for annotation_id, annotation in annotations.items():
            tracked_features[feature][annotation_id].append(annotation)

    return tracked_features


def write_annotations(
    outfile: tp.TextIO,
    tracked_features: dict[str, dict[int, list[FeatureAnnotation]]],
    feature_model: Path | None = None,
) -> None:
    """
    Write the given annotations to the given output file.

    If a feature model is given (or the output file already is one), the
    annotations are added to it and the merged model is written.
    """
    if feature_model is None and Path(str(outfile.name)).exists():
        feature_model = Path(outfile.name)

    if feature_model is None:
        for feature, annotations in tracked_features.items():
            outfile.write(f"Annotations for feature {feature}:\n")
            for _, locations in annotations.items():
                for location in locations:
                    outfile.write(location.to_xml_direct())
                    outfile.write("\n")
                outfile.write("\n")
            outfile.write("\n")
    else:
        update_feature_model(feature_model, tracked_features, outfile)
    click.echo(f"\nFinal annotations written to {outfile.name}.")


if __name__ == '__main__':
    main()
