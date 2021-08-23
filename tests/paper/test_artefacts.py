"""Test case study."""
import typing as tp
import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile

from varats.paper_mgmt.artefacts import (
    load_artefacts_from_file,
    initialize_artefacts,
)
from varats.plot.plots import PlotArtefact
from varats.plots.paper_config_overview import PaperConfigOverviewGenerator
from varats.utils.settings import vara_cfg

YAML_ARTEFACTS = """DocType: Artefacts
Version: 1
---
artefacts:
- artefact_type: plot
  artefact_type_version: 2
  file_type: png
  name: overview
  output_path: 'some/path'
  plot_generator: pc-overview-plot
  report_type: EmptyReport
"""


class TestArtefacts(unittest.TestCase):
    """Test basic Artefact functionality."""

    @classmethod
    def setUp(cls):
        """Setup artefacts file from yaml doc."""
        initialize_artefacts()
        with NamedTemporaryFile('w') as yaml_file:
            yaml_file.write(YAML_ARTEFACTS)
            yaml_file.seek(0)
            cls.artefacts = load_artefacts_from_file(Path(yaml_file.name))
        cls.artefact = next(cls.artefacts.__iter__())
        if not isinstance(cls.artefact, PlotArtefact):
            raise AssertionError("Test artefact is not a PlotArtefact!")

    # Artefact tests

    def test_artefact_type(self):
        """Check if artefact type is loaded correctly."""
        self.assertTrue(isinstance(self.artefact, PlotArtefact))

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
        self.assertEqual(artefact_dict['artefact_type'], 'plot')
        self.assertEqual(artefact_dict['artefact_type_version'], 2)
        self.assertEqual(artefact_dict['file_type'], 'png')
        self.assertEqual(artefact_dict['name'], 'overview')
        self.assertEqual(artefact_dict['output_path'], 'some/path')
        self.assertEqual(artefact_dict['plot_generator'], 'pc-overview-plot')
        self.assertEqual(artefact_dict['report_type'], 'EmptyReport')

    # PlotArtefact tests

    def test_artefact_plot_type(self):
        """Check if plot type is loaded correctly."""
        self.assertEqual(self.artefact.plot_generator_type, "pc-overview-plot")

    def test_artefact_plot_type_class(self):
        """Check if plot class is resolved correctly."""
        self.assertEqual(
            self.artefact.plot_generator_class, PaperConfigOverviewGenerator
        )

    def test_artefact_file_format(self):
        """Check if plot file format is loaded correctly."""
        self.assertEqual(self.artefact.common_options.file_type, 'png')

    def test_artefact_plot_kwargs(self):
        """Check if plot kwargs are loaded correctly."""
        self.assertEqual(
            self.artefact.plot_kwargs['report_type'], 'EmptyReport'
        )

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
