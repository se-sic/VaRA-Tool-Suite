import logging
import typing as tp
from collections import defaultdict

from varats.base.configuration import PatchConfiguration
from varats.project.project_util import ProjectBinaryWrapper
from varats.project.varats_project import VProject
from varats.report.tef_report import TEFReport, TraceEvent, TraceEventType
from varats.utils.config import get_config

LOG = logging.getLogger(__name__)


def get_feature_tags(project):
    config = get_config(project, PatchConfiguration)
    if not config:
        return []

    result = {opt.value for opt in config.options()}

    return result


def get_tags_RQ1(project):
    result = get_feature_tags(project)

    to_remove = [
        "SynthCTCRTP", "SynthCTPolicies", "SynthCTTraitBased",
        "SynthCTTemplateSpecialization"
    ]

    for s in to_remove:
        if s in result:
            result.remove(s)

    return result


def select_project_binaries(project: VProject) -> tp.List[ProjectBinaryWrapper]:
    """Uniformly select the binaries that should be analyzed."""
    if project.name == "DunePerfRegression":
        f_tags = get_feature_tags(project)

        grid_binary_map = {
            "YaspGrid": "poisson_yasp_q2_3d",
            "UGGrid": "poisson_ug_pk_2d",
            "ALUGrid": "poisson_alugrid"
        }

        for grid in grid_binary_map:
            if grid in f_tags:
                return [
                    binary for binary in project.binaries
                    if binary.name == grid_binary_map[grid]
                ]

    return [project.binaries[0]]


def get_interactions_from_fr_string(interactions: str, sep: str = ",") -> str:
    """Convert the feature strings in a TEFReport from FR(x,y) to x*y, similar
    to the format used by SPLConqueror."""
    interactions = (
        interactions.replace("FR", "").replace("(", "").replace(")", "")
    )
    interactions_list = interactions.split(sep)

    # Features cannot interact with itself, so remove duplicates
    interactions_list = list(set(interactions_list))

    # Ignore interactions with base, but do not remove base if it's the only
    # feature
    if "Base" in interactions_list and len(interactions_list) > 1:
        interactions_list.remove("Base")

    interactions_str = "*".join(interactions_list)

    return interactions_str


def get_matching_event(
    open_events: tp.List[TraceEvent], closing_event: TraceEvent
):
    for event in open_events:
        if (
            event.uuid == closing_event.uuid and
            event.pid == closing_event.pid and event.tid == closing_event.tid
        ):
            open_events.remove(event)
            return event

    LOG.debug(f"Could not find matching start for Event {repr(closing_event)}.")

    return None


def get_feature_regions_from_tef_report(
    tef_report: TEFReport,
) -> tp.Dict[str, int]:
    """Extract feature regions occurrences from a TEFReport."""
    open_events: tp.List[TraceEvent] = []

    feature_regions: tp.Dict[str, int] = defaultdict(int)

    found_missing_open_event = False
    for trace_event in tef_report.trace_events:
        if trace_event.category == "Feature":
            if trace_event.event_type == TraceEventType.DURATION_EVENT_BEGIN:
                # open_events.append(trace_event)
                # insert event at the top of the list
                open_events.insert(0, trace_event)

                interactions = [event.name for event in open_events]
                interaction_string = get_interactions_from_fr_string(
                    ",".join(interactions)
                )

                feature_regions[interaction_string] += 1
            elif trace_event.event_type == TraceEventType.DURATION_EVENT_END:
                opening_event = get_matching_event(open_events, trace_event)
                if not opening_event:
                    found_missing_open_event = True
                    continue

    if open_events:
        LOG.error("Not all events have been correctly closed.")
        LOG.debug(f"Events = {open_events}.")

    if found_missing_open_event:
        LOG.error("Not all events have been correctly opened.")

    return feature_regions
