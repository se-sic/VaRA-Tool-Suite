"""MultiPatchReport to group together similar reports that where produced for
differently patched projects."""
import pickle
import shutil
import tempfile
import typing as tp
from pathlib import Path

from varats.provider.patch.patch_provider import Patch
from varats.report.report import ReportTy, BaseReport
from varats.utils.settings import vara_cfg


class MultiPatchReport(
    BaseReport, tp.Generic[ReportTy], shorthand="MPR", file_type=".zip"
):
    """Meta report to group together reports of the same type that where
    produced with differently patched projects."""

    def __init__(self, path: Path, report_type: tp.Type[ReportTy]) -> None:
        super().__init__(path)

        if not self.__load_from_data_cache():
            self.__load_from_report_path(report_type)

            # Update data cache
            self.__save_to_data_cache()

    def __get_cached_path(self) -> Path:
        original_path = self.path
        # The original path should have the prefix 'vara_cfg()["results"]'
        # The data_cache path is the same but with the prefix 'vara_cfg()["data_cache"]'
        data_cache_path = str(original_path).replace(
            str(vara_cfg()["result_dir"]), str(vara_cfg()["data_cache"])
        )

        # Report path contain a UUID that changes with every run
        # Replace it with a fixed string to ensure that the cache is reused
        data_cache_path = data_cache_path.replace(self.filename.uuid, "cached")

        return Path(data_cache_path)

    def __load_from_data_cache(self) -> bool:
        original_path = self.path
        # The original path should have the prefix 'vara_cfg()["results"]'
        # The data_cache path is the same but with the prefix 'vara_cfg()["data_cache"]'
        data_cache_path = self.__get_cached_path()

        if not data_cache_path.exists():
            return False

        # Compare whether the data cache version is newer than the original
        if data_cache_path.stat().st_mtime <= original_path.stat().st_mtime:
            # Data cache is older than original, do not load
            print("Data cache is outdated. Updating data cache.")
            return False

        # Load from data cache
        #print("Loading report from data cache:", data_cache_path)
        with open(data_cache_path, 'rb') as f:
            tmp_dict = pickle.load(f)

        self.__dict__.update(tmp_dict)

        return True

    def __load_from_report_path(self, report_type: tp.Type[ReportTy]) -> None:
        path = self.path
        self.__patched_reports: tp.Dict[str, ReportTy] = {}
        self.__base = None

        with tempfile.TemporaryDirectory() as tmp_result_dir:
            shutil.unpack_archive(path, extract_dir=tmp_result_dir)

            for report in Path(tmp_result_dir).iterdir():
                if self.is_baseline_report(report.name):
                    self.__base = report_type(report)
                elif self.is_patched_report(report.name):
                    self.__patched_reports[
                        self._parse_patch_shorthand_from_report_name(
                            report.name
                        )] = report_type(report)

            if not self.__base or not self.__patched_reports:
                raise AssertionError(
                    f"Reports where missing in the file {path=}"
                )

    def __save_to_data_cache(self) -> None:
        original_path = self.path
        # The original path should have the prefix 'vara_cfg()["results"]'
        # The data_cache path is the same but with the prefix 'vara_cfg()["data_cache"]'
        data_cache_path = self.__get_cached_path()

        # Ensure that the parent directory exists
        data_cache_path.parent.mkdir(parents=True, exist_ok=True)

        # Save to data cache
        #print("Saving report to data cache:", data_cache_path)
        with open(data_cache_path, 'wb') as f:
            pickle.dump(self.__dict__, f)

    def get_baseline_report(self) -> ReportTy:
        return self.__base

    def get_report_for_patch(self,
                             patch_shortname: str) -> tp.Optional[ReportTy]:
        """Get the report for a given patch shortname."""
        if patch_shortname in self.__patched_reports:
            return self.__patched_reports[patch_shortname]

        return None

    def get_patch_names(self) -> tp.List[str]:
        return list(self.__patched_reports.keys())

    def get_patched_reports(self) -> tp.ValuesView[ReportTy]:
        return self.__patched_reports.values()

    @staticmethod
    def create_baseline_report_name(base_file_name: str) -> str:
        return f"baseline_{base_file_name}"

    @staticmethod
    def is_baseline_report(file_name: str) -> bool:
        return file_name.startswith("baseline_")

    @staticmethod
    def create_patched_report_name(
        patch: Patch, base_file_name: str, **kwargs: tp.Any
    ) -> str:
        return (
            f"patched_{len(patch.rendered_name(**kwargs))}_" +
            f"{patch.rendered_name(**kwargs)}_{base_file_name}"
        )

    @staticmethod
    def is_patched_report(file_name: str) -> bool:
        return file_name.startswith("patched_")

    @staticmethod
    def _parse_patch_shorthand_from_report_name(file_name: str) -> str:
        """Parse the patch shorthand from a given patched report."""
        fn_without_prefix = file_name[len("patched_"):]
        split_leftover_fn = fn_without_prefix.partition("_")
        shortname_length = int(split_leftover_fn[0])
        patch_shortname = "".join(split_leftover_fn[2:])[:shortname_length]
        return patch_shortname
