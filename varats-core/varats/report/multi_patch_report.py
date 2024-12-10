"""MultiPatchReport to group together similar reports that where produced for
differently patched projects."""
import logging
import shutil
import tempfile
import typing as tp
from collections import defaultdict
from pathlib import Path

from varats.provider.patch.patch_provider import Patch
from varats.report.report import ReportTy, BaseReport

LOG = logging.getLogger(__name__)

class MultiPatchReport(
    BaseReport, tp.Generic[ReportTy], shorthand="MPR", file_type=".zip"
):
    """Meta report to group together reports of the same type that where
    produced with differently patched projects."""

    def __init__(self, path: Path, report_type: tp.Type[ReportTy]) -> None:
        super().__init__(path)
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
    def extract_base_file_name(file_name: str) -> str:
        if MultiPatchReport.is_patched_report(file_name):
            file_name = file_name[len("patched_"):]
            patch_name_length = int(file_name[:file_name.find("_")])
            file_name = file_name[file_name.find("_") + patch_name_length + 2:]
            return file_name
        elif file_name.startswith("baseline_"):
            return file_name[len("baseline_"):]
        else:
            raise AssertionError(f"Invalid report file name {file_name}")


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

class MultiBinaryMultiPatchReport(
    MultiPatchReport, tp.Generic[ReportTy], shorthand="MBMPR", file_type=".zip"
):
    """Special version of a MultiPatchReport that allows to store reports for multiple binaries, along
    with multiple patches."""

    def __init__(self, path: Path, report_type: tp.Type[ReportTy]):
        super().__init__(path, report_type)

        self.__all_bases: tp.Dict[str, ReportTy] = {}
        self.__all_patched_reports: tp.Dict[str, tp.Dict[str, ReportTy]] = defaultdict(dict)

        with tempfile.TemporaryDirectory() as tmp_result_dir:
            shutil.unpack_archive(path, extract_dir=tmp_result_dir)

            for report in Path(tmp_result_dir).iterdir():
                if self.is_baseline_report(report.stem):
                    self.__all_bases[self.extract_base_file_name(report.stem)] = report_type(report)
                if self.is_patched_report(report.stem):
                    patch_name = self._parse_patch_shorthand_from_report_name(report.name)
                    base_name = self.extract_base_file_name(report.stem)
                    self.__all_patched_reports[base_name][patch_name] = report_type(report)



    def get_baseline_report(self) -> ReportTy:
        LOG.warning("Using get_baseline_report on a MultiBinaryMultiPatchReport, this will only return one baseline report. Consider using get_specific_baseline_report instead.")
        return super().get_baseline_report()

    def get_report_for_patch(self, patch_shortname: str) -> tp.Optional[ReportTy]:
        LOG.warning("Using get_report_for_patch on a MultiBinaryMultiPatchReport, this will only return one patched report. Consider using get_specific_patched_report instead.")
        return super().get_report_for_patch(patch_shortname)

    def get_specific_patched_report(self, base_name: str, patch_name: str) -> tp.Optional[ReportTy]:
        if patch_name not in self.__all_patched_reports[base_name]:
            return None
        return self.__all_patched_reports[base_name][patch_name]

    def get_specific_baseline_report(self, base_name: str) -> ReportTy:
        return self.__all_bases[base_name]

    def get_baseline_reports(self) -> tp.ValuesView[ReportTy]:
        return self.__all_bases.values()

    def get_baseline_names(self) -> tp.List[str]:
        return list(self.__all_bases.keys())
