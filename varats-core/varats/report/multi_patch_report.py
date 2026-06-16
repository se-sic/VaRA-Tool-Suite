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

    @staticmethod
    def _parse_binary_name_from_baseline_report_name(file_name: str) -> str:
        # Baseline report name structure: baseline_{binary_name}.zip
        if file_name.endswith(".zip"):
            file_name = file_name.removesuffix(".zip")
        return file_name[len("baseline_"):]

    @staticmethod
    def _parse_binary_name_from_patched_report_name(file_name: str) -> str:
        # Patched report name structure: patched_{patch_shortname_length}_{patch_shortname}_{binary_name}.zip
        if file_name.endswith(".zip"):
            file_name = file_name.removesuffix(".zip")
        fn_without_prefix = file_name[len("patched_"):]
        split_leftover_fn = fn_without_prefix.partition("_")
        shortname_length = int(split_leftover_fn[0])
        return "".join(split_leftover_fn[2:])[shortname_length + 1:]

    def __init__(self, path: Path, report_type: tp.Type[ReportTy]) -> None:
        super().__init__(path)
        self.__patched_reports: tp.Dict[str, ReportTy] = {}
        self.__base = None
        self.__base_by_binary: dict[str, ReportTy] = {}
        self.__patched_reports_by_binary: dict[str, dict[str, ReportTy]] = {}

        with tempfile.TemporaryDirectory() as tmp_result_dir:
            shutil.unpack_archive(path, extract_dir=tmp_result_dir)

            for report in Path(tmp_result_dir).iterdir():
                if self.is_baseline_report(report.name):
                    base_report = report_type(report)
                    self.__base = base_report
                    self.__base_by_binary[
                        self._parse_binary_name_from_baseline_report_name(
                            report.name
                        )] = base_report
                elif self.is_patched_report(report.name):
                    binary_name = self._parse_binary_name_from_patched_report_name(
                        report.name
                    )
                    patch_shortname = self._parse_patch_shorthand_from_report_name(
                        report.name
                    )
                    self.__patched_reports[
                        patch_shortname] = report_type(report)
                    if binary_name not in self.__patched_reports_by_binary:
                        self.__patched_reports_by_binary[binary_name] = {}
                    self.__patched_reports_by_binary[binary_name][
                        patch_shortname] = report_type(report)

            if not self.__base or not self.__patched_reports:
                raise AssertionError(
                    f"Reports were missing in the file {path=}"
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
    def create_patched_report_name(
        patch: Patch, base_file_name: str, **kwargs: tp.Any
    ) -> str:
        rendered_name = patch.rendered_name(**kwargs)
        return (
            f"patched_{len(rendered_name)}_" +
            f"{rendered_name}_{base_file_name}"
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

    @staticmethod
    def _parse_base_file_name_from_report_name(file_name: str) -> str:
        """Parse the base file name from a given report."""
        if MultiPatchReport.is_baseline_report(file_name):
            return file_name[len("baseline_"):]
        elif MultiPatchReport.is_patched_report(file_name):
            fn_without_prefix = file_name[len("patched_"):]
            split_leftover_fn = fn_without_prefix.partition("_")
            shortname_length = int(split_leftover_fn[0])
            base_file_name = "".join(split_leftover_fn[2:]
                                    )[shortname_length + 1:]
            return base_file_name
        else:
            raise ValueError(f"Invalid report file name: {file_name}")

    @property
    def binaries(self) -> tp.Collection[str]:
        return self.__base_by_binary.keys()

    def baseline(self, binary_name: str) -> ReportTy:
        return self.__base_by_binary[binary_name]

    def patched(self, binary_name: str, patch_shortname: str) -> ReportTy:
        return self.__patched_reports_by_binary[binary_name][patch_shortname]