"""Test case study."""
import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile

from varats.paper_mgmt.artefacts import (
    ArtefactType,
    PlotArtefact,
    load_artefacts_from_file,
)
from varats.plots.paper_config_overview import PaperConfigOverviewPlot
from varats.utils.settings import vara_cfg

YAML_ARTEFACTS = """DocType: Artefacts
Version: 1
---
artefacts:
- artefact_type: plot
  artefact_type_version: 1
  file_format: png
  name: overview
  output_path: 'some/path'
  plot_type: paper_config_overview_plot
  report_type: EmptyReport
"""


class TestArtefacts(unittest.TestCase):
    """Test basic Artefact functionality."""

    @classmethod
    def setUp(cls):
        """Setup artefacts file from yaml doc."""
        with NamedTemporaryFile('w') as yaml_file:
            yaml_file.write(YAML_ARTEFACTS)
            yaml_file.seek(0)
            cls.artefacts = load_artefacts_from_file(Path(yaml_file.name))
        cls.artefact = next(cls.artefacts.__iter__())

    # Artefact tests

    def test_artefact_type(self):
        """Check if artefact type is loaded correctly."""
        self.assertTrue(isinstance(self.artefact, PlotArtefact))
        self.assertEqual(self.artefact.artefact_type, ArtefactType.PLOT)

    def test_artefact_name(self):
        """Check if artefact name is loaded correctly."""
        self.assertEqual(self.artefact.name, 'overview')

    def test_artefact_output_path(self):
        """Check if artefact output_path is loaded correctly."""
        self.assertEqual(
            self.artefact.output_path,
            Path(str(vara_cfg()['artefacts']['artefacts_dir'])) /
            Path(str(vara_cfg()['paper_config']['current_config'])) /
            'some/path'
        )

    def test_artefact_to_dict(self):
        """Check if artefact is serialized correctly."""
        artefact_dict = self.artefact.get_dict()
        self.assertEqual(artefact_dict['artefact_type'], 'PLOT')
        self.assertEqual(artefact_dict['artefact_type_version'], 1)
        self.assertEqual(artefact_dict['file_format'], 'png')
        self.assertEqual(artefact_dict['name'], 'overview')
        self.assertEqual(artefact_dict['output_path'], 'some/path')
        self.assertEqual(
            artefact_dict['plot_type'], 'paper_config_overview_plot'
        )
        self.assertEqual(artefact_dict['report_type'], 'EmptyReport')

    # PlotArtefact tests

    def __test_plot_artefact(self, test_function):
        if isinstance(self.artefact, PlotArtefact):
            test_function(self.artefact)
        else:
            self.fail('self.artefact is not a PlotArtefact')

    def test_artefact_plot_type(self):
        """Check if plot type is loaded correctly."""
        self.__test_plot_artefact(
            lambda artefact: self.
            assertEqual(artefact.plot_type, 'paper_config_overview_plot')
        )

    def test_artefact_plot_type_class(self):
        """Check if plot class is resolved correctly."""
        self.__test_plot_artefact(
            lambda artefact: self.
            assertEqual(artefact.plot_type_class, PaperConfigOverviewPlot)
        )

    def test_artefact_file_format(self):
        """Check if plot file format is loaded correctly."""
        self.__test_plot_artefact(
            lambda artefact: self.assertEqual(artefact.file_format, 'png')
        )

    def test_artefact_plot_kwargs(self):
        """Check if plot kwargs are loaded correctly."""
        self.__test_plot_artefact(
            lambda artefact: self.
            assertEqual(artefact.plot_kwargs['report_type'], 'EmptyReport')
        )

    # Artefacts tests

    def test_artefacts_iterator(self):
        """Check if artefacts are loaded correctly."""
        self.assertEqual(len(list(self.artefacts)), 1)

    def test_artefacts_add(self):
        """Check if artefact is added."""
        self.artefacts.add_artefact(
            PlotArtefact(
                'foo',
                Path('some/path'),
                'paper_config_overview_plot',
                'svg',
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
