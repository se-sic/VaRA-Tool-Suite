"""Test case study."""
import typing as tp
import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile

from tests.test_utils import run_in_test_environment, UnitTestFixtures
from varats.data.reports.empty_report import EmptyReport
from varats.paper_mgmt.artefacts import (
    initialize_artefact_types,
    Artefacts,
    Artefact,
    load_artefacts_from_file,
)
from varats.paper_mgmt.paper_config import (
    load_paper_config,
    get_loaded_paper_config,
)
from varats.plot.plots import PlotArtefact, PlotConfig, CommonPlotOptions
from varats.plots.case_study_overview import CaseStudyOverviewGenerator
from varats.plots.discover_plots import initialize_plots
from varats.plots.paper_config_overview import PaperConfigOverviewGenerator
from varats.tables.discover_tables import initialize_tables
from varats.utils.settings import vara_cfg, save_config

YAML_ARTEFACTS = """DocType: Artefacts
Version: 2
---
artefacts:
- artefact_type: plot
  artefact_type_version: 2
  file_type: png
  name: overview
  output_dir: 'some/path'
  plot_config: {}
  plot_generator: pc-overview-plot
  report_type: EmptyReport
  view: false
"""


class TestArtefacts(unittest.TestCase):
    """Test basic Artefact functionality."""

    artefacts: Artefacts
    plot_artefact: PlotArtefact

    @classmethod
    def setUp(cls):
        """Setup artefacts file from yaml doc."""
        initialize_plots()
        initialize_tables()
        initialize_artefact_types()
        with NamedTemporaryFile('w') as yaml_file:
            yaml_file.write(YAML_ARTEFACTS)
            yaml_file.seek(0)
            cls.artefacts = load_artefacts_from_file(Path(yaml_file.name))
        cls.plot_artefact = tp.cast(
            PlotArtefact, next(cls.artefacts.__iter__())
        )
        if not isinstance(cls.plot_artefact, PlotArtefact):
            raise AssertionError("Test artefact is not a PlotArtefact!")

    # Artefact tests

    def test_artefact_type(self):
        """Check if artefact type is loaded correctly."""
        self.assertTrue(isinstance(self.plot_artefact, PlotArtefact))

    def test_artefact_name(self):
        """Check if artefact name is loaded correctly."""
        self.assertEqual(self.plot_artefact.name, 'overview')

    def test_artefact_output_path(self):
        """Check if artefact output_path is loaded correctly."""
        self.assertEqual(
            self.plot_artefact.output_dir,
            Artefact.base_output_dir() / 'some/path'
        )

    def test_artefact_to_dict(self):
        """Check if artefact is serialized correctly."""
        artefact_dict = self.plot_artefact.get_dict()
        self.assertEqual(artefact_dict['artefact_type'], 'plot')
        self.assertEqual(artefact_dict['artefact_type_version'], 2)
        self.assertEqual(artefact_dict['file_type'], 'png')
        self.assertEqual(artefact_dict['name'], 'overview')
        self.assertEqual(artefact_dict['output_dir'], 'some/path')
        self.assertEqual(artefact_dict['plot_generator'], 'pc-overview-plot')
        self.assertEqual(artefact_dict['report_type'], 'EmptyReport')

    # PlotArtefact tests

    def test_artefact_plot_type(self):
        """Check if plot type is loaded correctly."""
        self.assertEqual(
            self.plot_artefact.plot_generator_type, "pc-overview-plot"
        )

    def test_artefact_plot_type_class(self):
        """Check if plot class is resolved correctly."""
        self.assertEqual(
            self.plot_artefact.plot_generator_class,
            PaperConfigOverviewGenerator
        )

    def test_artefact_file_format(self):
        """Check if plot file format is loaded correctly."""
        self.assertEqual(self.plot_artefact.common_options.file_type, 'png')

    def test_artefact_plot_kwargs(self):
        """Check if plot kwargs are loaded correctly."""
        self.assertEqual(
            self.plot_artefact.plot_kwargs['report_type'], EmptyReport
        )

    def test_artefact_file_info(self):
        """Check if file info is generated correctly."""
        file_infos = self.plot_artefact.get_artefact_file_infos()
        self.assertEqual(1, len(file_infos))
        self.assertIsNone(file_infos[0].case_study)
        self.assertEqual(
            "paper_config_overview_plot.png", file_infos[0].file_name
        )

    @run_in_test_environment(UnitTestFixtures.PAPER_CONFIGS)
    def test_cli_option_converter(self):
        """Test whether CLI option conversion works correctly."""
        # setup config
        vara_cfg()['paper_config']['current_config'] = "test_artefacts_driver"
        load_paper_config()
        save_config()

        plot_generator = CaseStudyOverviewGenerator(
            PlotConfig.from_kwargs(view=False),
            report_type=EmptyReport,
            case_study=get_loaded_paper_config().get_case_studies("xz")[0]
        )
        artefact = PlotArtefact.from_generator(
            "CS Overview", plot_generator, CommonPlotOptions.from_kwargs()
        )
        artefact_dict = artefact.get_dict()
        self.assertEqual("xz_0", artefact_dict["case_study"])
        self.assertEqual("EmptyReport", artefact_dict["report_type"])

    # Artefacts tests

    def test_artefacts_iterator(self):
        """Check if artefacts are loaded correctly."""
        self.assertEqual(len(list(self.artefacts)), 1)

    def test_artefacts_add(self):
        """Check if artefact is added."""
        self.artefacts.add_artefact(
            PlotArtefact.create_artefact(
                'foo',
                Path('some/path'),
                plot_generator='pc-overview-plot',
                file_type='svg',
                some='argument'
            )
        )
        self.assertEqual(len(list(self.artefacts)), 2)

    def test_artefacts_to_dict(self):
        """Check if artefacts object is serialized correctly."""
        artefacts_dict = self.artefacts.get_dict()
        self.assertEqual(len(artefacts_dict['artefacts']), 1)
        artefact_dict = artefacts_dict['artefacts'][0]
        self.assertEqual(artefact_dict['name'], 'overview')
