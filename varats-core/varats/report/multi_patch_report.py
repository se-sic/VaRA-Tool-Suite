"""MultiPatchReport to group together similar reports that where produced for
differently patched projects."""
import shutil
import tempfile
import typing as tp
from pathlib import Path

from varats.provider.patch.patch_provider import Patch
from varats.report.report import ReportTy, BaseReport


class MultiPatchReport(
    BaseReport, tp.Generic[ReportTy], shorthand="MPR", file_type=".zip"
):
    """Meta report to group together reports of the same type that where
    produced with differently patched projects."""

    def __init__(self, path: Path, report_type: tp.Type[ReportTy]) -> None:
        super().__init__(path)
        self.__patched_reports: tp.Dict[str, ReportTy] = {}

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
                    "Reports where missing in the file {report_path=}"
                )

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
    def create_patched_report_name(patch: Patch, base_file_name: str) -> str:
        return (
            f"patched_{len(patch.shortname)}_" +
            f"{patch.shortname}_{base_file_name}"
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
