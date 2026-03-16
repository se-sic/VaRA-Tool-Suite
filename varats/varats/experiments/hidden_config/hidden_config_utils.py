import typing as tp

import numpy as np

from varats.base.configuration import PatchVariationConfiguration
from varats.paper.case_study import CaseStudy
from varats.paper.paper_config import get_paper_config
from varats.project.patch_variation_source import get_current_variation_id
from varats.project.varats_project import VProject
from varats.utils.config import load_configuration_map_for_case_study

HIDDEN_CONFIG_REPS = 10
# Mapping of patches per project to possible variations
# for patch rendering.
PATCH_VARIATIONS = {
    "libzmq": {
        "hwm_template": ("hwm", [x for x in range(100, 2000, 100)]),
    },
    "brotli": {
        "command_block_cost": (
            "command_block_cost",
            [x / 10 for x in range(120, 150, 1) if x != 135]
        ),
        "literal_block_cost": (
            "literal_block_cost",
            [x / 10 for x in range(270, 300, 1) if x != 281]
        ),
        "distance_block_cost": (
            "distance_block_cost",
            [x / 10 for x in range(130, 160, 1) if x != 146]
        ),
        "min_entropy":
            ("min_entropy", [x / 100 for x in range(650, 950, 10) if x != 792]),
        "min_utf_ratio":
            ("min_utf_ratio", [x / 100 for x in range(50, 100, 5) if x != 75]),
        "sample_rate": (
            "sample_rate", [x for x in range(10, 20) if x != 13] +
            [13 * i for i in range(2, 6)]
        ),
        "one_symbol_histogram": (
            "one_symbol_histogram",
            [3, 6, 9, 10, 11, 13, 14, 15, 18] + [x * 12 for x in range(2, 6)]
        ),
        "two_symbol_histogram": (
            "two_symbol_histogram",
            [12, 14, 16, 18, 22, 24, 26, 28] + [x * 20 for x in range(2, 6)]
        ),
        "three_symbol_histogram": (
            "three_symbol_histogram",
            [20, 22, 24, 26, 30, 32, 34, 36] + [x * 28 for x in range(2, 6)]
        ),
        "four_symbol_histogram": (
            "four_symbol_histogram",
            [30, 33, 35, 36, 38, 39, 42, 44] + [x * 37 for x in range(2, 6)]
        ),
        "max_literal_histograms": (
            "max_literal_histograms",
            [25, 50, 75, 125, 150, 175, 200] + [x * 100 for x in range(3, 7)]
        ),
        "max_command_histograms": (
            "max_command_histograms", [10, 20, 30, 40, 60, 70, 80, 90, 100] +
            [x * 50 for x in range(3, 7)]
        ),
        "literal_stride_length": (
            "literal_stride_length",
            [30, 40, 50, 60, 80, 90, 100, 110] + [x * 70 for x in range(2, 6)]
        ),
        "command_stride_length": (
            "command_stride_length", [15, 20, 25, 30, 35, 45, 50, 55, 60, 65] +
            [x * 40 for x in range(2, 6)]
        ),
        "distance_stride_length": (
            "distance_stride_length", [15, 20, 25, 30, 35, 45, 50, 55, 60, 65] +
            [x * 40 for x in range(2, 6)]
        ),
        "symbols_per_literal_histogram": (
            "symbols_per_literal_histogram",
            [400, 425, 450, 475, 500, 525, 550, 575, 600, 625, 650] +
            [x * 544 for x in range(2, 6)]
        ),
        "symbols_per_command_histogram": (
            "symbols_per_command_histogram",
            [400, 425, 450, 475, 500, 525, 550, 575, 600, 625, 650] +
            [x * 530 for x in range(2, 6)]
        ),
        "symbols_per_distance_histogram": (
            "symbols_per_distance_histogram",
            [400, 425, 450, 475, 500, 525, 550, 575, 600, 625, 650] +
            [x * 544 for x in range(2, 6)]
        ),
        "min_length_block_splitting": (
            "min_length_block_splitting",
            [2**x for x in range(2, 13) if 2**x != 128]
        ),
        "iter_mul_refining": (
            "iter_mul_refining",
            [x for x in range(3, 11)] + [x * 10 for x in range(2, 6)]
        ),
    },
    "DunePerfRegression": {
        "hexa_gitter_refinement": (
            "resolution",
            [x for x in range(25, 100, 25)] + [x for x in range(100, 500, 50)]
        ),
        "alu_repartition": ("mem_factor", [x for x in range(3, 10, 1)]),
    },
    "FastDownward": {
        "extra_columns": ("extra_columns", [x for x in range(1, 10)]),
        "max_distance":
            ("max_distance", [2**x for x in range(1, 10) if 2**x != 32]),
        "memory_padding": (
            "memory_padding_mb",
            [25] + [x for x in range(50, 105, 5) if x != 75] + [150, 225, 300]
        ),
        "preconditions_to_test":
            ("preconditions_to_test", [x for x in range(2, 11) if x != 5]),
    },
    "libvpx": {
        "block_size_vp9_enc":
            ("block_size", [2**x for x in range(1, 7) if x != 4]),
        "cq_adjust_one_pass": ("cq_adjust", [0.05, 0.2, 0.4, 0.6, 0.8]),
        "cq_adjust_two_pass": ("cq_adjust", [0.05, 0.2, 0.4, 0.6, 0.8]),
        "kMaxMfBoost":
            ("kMaxMfBoost", [250, 500, 1000, 1500, 3000, 4000, 10000]),
        "min_filter_pick":
            ("min_filter_level", [1, 2, 3, 4] + [x for x in range(5, 20, 2)]),
        "min_filter_search":
            ("min_filter_level", [1, 2, 3, 4] + [x for x in range(5, 20, 2)]),
        "mv_threshold": ("mv_threshold", [25, 50, 150, 200, 400, 800, 1000]),
        "pred_stride": ("pred_stride", [4, 8, 16, 32, 128]),
        "pred_stride_rd": ("pred_stride", [4, 8, 16, 32, 128])
    },
    "7zip": {
        "min_block_size": (
            "min_block_size",
            [x for x in range(2, 11)] + [2**x for x in range(4, 11)]
        ),
        "num_threads_max": ("num_threads_max", [2**x for x in range(1, 10)]),
        "start_string_capacity":
            ("start_string_capacity", [2**x for x in range(1, 9) if 2**x != 4]),
    },
    "xz": {
        "enc_chunk_size":
            ("enc_chunk_size", [2**x for x in range(7, 18) if 2**x != 16384]),
        "dec_chunk_size":
            ("dec_chunk_size", [2**x for x in range(7, 18) if 2**x != 16384]),
    },
    "postgres": {
        "analyse_min_tracks": (
            "min_tracks", [
                5, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300, 400,
                500
            ]
        ),
        "blocklist_cnt": (
            "blocklist_cnt",
            [2, 4, 5, 6, 7, 8, 9, 10, 15, 20, 25, 30, 40, 50, 100]
        ),
        "bufpage_multi_delete":
            ("nitems", [3, 4, 5, 6, 7, 8, 9, 10, 14, 20, 30, 40, 50, 100]),
        "clause_threshold": (
            "clause_threshold",
            [10, 20, 30, 40, 50, 60, 70, 80, 90, 150, 200, 300, 400, 500]
        ),
        "colinfo_hash":
            ("min_cols", [2**x for x in range(1, 16) if 2**x != 32]),
        "like_hist_heuristic": (
            "num_entries", [
                10, 20, 30, 40, 50, 60, 70, 80, 90, 150, 200, 300, 400, 500,
                1000, 5000
            ]
        ),
        "max_buffered_tuples": (
            "max_tuples",
            [10, 50, 100, 200, 300, 400, 500, 2000, 3000, 4000, 5000, 10000]
        ),
        "max_empty_blocks": (
            "max_empty_blocks", [
                2, 3, 4, 5, 6, 7, 8, 9, 15, 20, 30, 40, 50, 100, 200, 300, 400,
                500
            ]
        ),
        "max_free_contexts": (
            "max_free_contexts", [
                10, 20, 30, 40, 50, 60, 70, 80, 90, 150, 200, 300, 400, 500,
                1000, 5000
            ]
        ),
        "max_inval_msg":
            ("max_inval_msg", [2**x for x in range(1, 16) if 2**x != 32]),
        "max_num_msg":
            ("max_num_messages", [2**x for x in range(1, 16) if 2**x != 4096]),
        "max_partition_buffers": (
            "max_partition_buffers", [2**x for x in range(1, 12) if 2**x != 32]
        ),
        "max_spins": (
            "max_spins",
            [20, 50, 100, 200, 300, 400, 500, 2000, 3000, 4000, 5000, 10000]
        ),
        "max_writeall_buffers": (
            "max_writeall_buffers", [2**x for x in range(1, 16) if 2**x != 16]
        ),
        "min_alloc": ("min_alloc", [2**x for x in range(1, 16) if 2**x != 32]),
        "min_size_soap": (
            "min_size_soap", [
                3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 20, 30, 40, 50, 100,
                500
            ]
        ),
        "min_spins": (
            "min_spins", [
                5, 15, 20, 25, 30, 40, 50, 60, 70, 80, 90, 150, 200, 300, 400,
                500, 600, 700, 800, 900
            ]
        ),
        "nt_rels_hash": ("nrels", [2**x for x in range(1, 16) if 2**x != 64]),
        "num_blocks": ("n_blocks", [2**x for x in range(1, 16) if 2**x != 8]),
        "num_seg_bins":
            ("num_seg_bins", [2**x for x in range(1, 16) if 2**x != 16]),
        "num_tries": (
            "num_tries", [
                10, 20, 30, 40, 60, 70, 80, 90, 100, 150, 200, 300, 400, 500,
                1000
            ]
        ),
        "page_read_penalty":
            ("read_penalty", [1.1, 1.25, 1.5, 1.75, 2.5, 3, 4, 5, 10]),
        "page_write_penalty":
            ("write_penalty", [1.1, 1.25, 1.5, 1.75, 2.5, 3, 4, 5, 10]),
        "ref_cnt_size":
            ("ref_cnt_size", [2**x for x in range(1, 16) if 2**x != 8]),
        "selec_factor":
            ("selec_factor", [0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9]),
        "stringinfo_min_length":
            ("min_space", [2**x for x in range(1, 16) if 2**x != 16]),
        "sync_scan_nelem": (
            "sync_scan_nelem",
            [5, 10, 15, 25, 30, 40, 50, 75, 100, 150, 200, 300, 400, 500]
        ),
        "xlog_distance_factor":
            ("factor", [1.05, 1.15, 1.25, 1.5, 2, 2.5, 3, 3.5, 4, 5, 10]),
        "xlog_insert_logs":
            ("xlog_insert_locks", [2**x for x in range(1, 16) if 2**x != 8]),
        "xlog_min_buffers":
            ("min_buffers", [2**x for x in range(1, 16) if 2**x != 8]),
    },
    "mariadb": {
        # "array_exp_factor":
        #     ("expansion_factor", [2**x for x in range(1, 16) if 2**x != 2]),
        # "array_min_capacity": (
        #     "array_min_capacity", [
        #         5, 10, 15, 25, 30, 40, 50, 60, 70, 80, 90, 150, 200, 300, 400,
        #         500
        #     ]
        # ),
        # "best_timer_cycles": (
        #     "overhead_cycles", [
        #         5, 10, 15, 25, 30, 40, 50, 60, 70, 80, 90, 150, 200, 300, 400,
        #         500
        #     ]
        # ),
        # "item_buf_size":
        #     ("buf_size", [2**x for x in range(1, 16) if 2**x != 64]),
        # "max_cols_fk": (
        #     "max_cols", [50, 100, 150, 200, 300, 400, 600, 700, 800, 900, 1000]
        # ),
        # "max_ha": ("max_ha", [2**x for x in range(1, 16) if 2**x != 64]),
        # "max_skips": (
        #     "max_skips", [
        #         2, 3, 4, 5, 6, 7, 8, 9, 15, 20, 30, 40, 50, 60, 70, 80, 90, 100,
        #         200
        #     ]
        # ),
        # "overhead_cycles": (
        #     "overhead_cycles", [
        #         5, 10, 15, 25, 30, 40, 50, 60, 70, 80, 90, 150, 200, 300, 400,
        #         500
        #     ]
        # ),
        # "sp_instr_buf_size":
        #     ("buf_size", [2**x for x in range(1, 16) if 2**x != 512]),
        # "sql_prepare_buf_size":
        #     ("buf_size", [2**x for x in range(1, 16) if 2**x != 256]),
        # "sql_select_buf_size":
        #     ("buf_size", [2**x for x in range(1, 16) if 2**x != 64]),
        # "sql_string_buf_size":
        #     ("buf_size", [2**x for x in range(1, 16) if 2**x != 256]),
        # "sql_table_buf_size": (
        #     "buf_size", [50, 100, 150, 200, 300, 400, 600, 700, 800, 900, 1000]
        # ),
        # "sql_view_buf_size":
        #     ("buf_size", [2**x for x in range(1, 16) if 2**x != 4096]),
        # "sql_view_buf_size_is":
        #     ("buf_size", [2**x for x in range(1, 16) if 2**x != 4096]),
        # "table_buf_size":
        #     ("buf_size", [2**x for x in range(1, 16) if 2**x != 1024]),
        # "unireg_buf_size":
        #     ("buf_size", [2**x for x in range(1, 16) if 2**x != 64]),
        "table_buf_size": ("buf_size", [256, 512]),
        "unireg_buf_size": ("buf_size", [32, 128]),
    }
}


def get_variation_config(
    project: VProject
) -> tp.Optional[PatchVariationConfiguration]:
    # Get patch variation config
    variation_id = get_current_variation_id(project)
    if variation_id is None:
        return None

    paper_config = get_paper_config()
    case_studies = paper_config.get_case_studies(cs_name=project.name)

    if len(case_studies) > 1:
        raise AssertionError(
            "Cannot handle multiple case studies of the same project."
        )

    case_study = case_studies[0]

    config_map = load_configuration_map_for_case_study(
        paper_config, case_study, PatchVariationConfiguration
    )

    variation = config_map.get_configuration(variation_id)

    return variation


def get_variations_as_dict(
    project: VProject
) -> tp.Dict[str, tp.Dict[str, tp.Any]]:
    return {
        o.name: dict(o.value) for o in get_variation_config(project).options()
    }


def get_all_variations_as_dict(
    case_study: CaseStudy
) -> tp.Dict[str, tp.Dict[str, tp.Any]]:
    paper_config = get_paper_config()

    config_map = load_configuration_map_for_case_study(
        paper_config, case_study, PatchVariationConfiguration
    )

    result = {}

    for cid in config_map.ids():
        variation = config_map.get_configuration(cid)
        if variation is None:
            continue

        for o in variation.options():
            patch_name = o.name
            if patch_name not in result:
                result[patch_name] = {}
            if len(o.value) > 1:
                print(
                    "Warning: Multiple arguments for patch variation, only the first one will be used."
                )

            for arg_name, arg_values in o.value.items():
                if arg_name not in result[patch_name]:
                    result[patch_name][arg_name] = set()
                result[patch_name] = (
                    arg_name, list(arg_values) + sample_variations(arg_values)
                )

    return result


def sample_variations(values: tp.List[tp.Any],
                      num_samples: int = 20) -> tp.List[tp.Any]:
    rng = np.random.default_rng(seed=42)

    if isinstance(values[0], int):
        random_values = rng.integers(
            min(values), max(values) + 1, size=num_samples
        )
    elif isinstance(values[0], float):
        # We want to sample floats with the same number of decimal places as the provided values
        decimal_places = max(len(str(value).split(".")[1]) for value in values)
        random_values = rng.uniform(min(values), max(values), size=num_samples)
        random_values = np.round(random_values, decimals=decimal_places)
    else:
        raise ValueError(
            f"Unsupported value type {type(values[0])} for during sampling"
        )

    # Erase duplicates from the random values and the provided values
    unique_values = set(values)
    unique_random_values = set(random_values)
    unique_random_values = unique_random_values - unique_values

    return list(unique_random_values)
