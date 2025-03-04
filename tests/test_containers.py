"""Test varats container support module."""
import typing as tp
import unittest
import unittest.mock as mock

from benchbuild.environments.adapters.common import buildah_version
from benchbuild.environments.domain.model import (
    Layer,
    FromLayer,
    WorkingDirectory,
    CopyLayer,
    UpdateEnv,
    RunLayer,
    EntryPoint,
)
from varats.containers.containers import (
    ImageBase,
    StageBuilder,
    get_image_name,
    ImageStage,
    _STAGE_LAYERS,
)
from varats.tools.research_tools.research_tool import Distro
from varats.utils.settings import vara_cfg, bb_cfg

from tests.helper_utils import run_in_test_environment


class TestImageBase(unittest.TestCase):
    """Test ImageBase class."""

    def test_distro(self) -> None:
        self.assertEqual(Distro.DEBIAN, ImageBase.DEBIAN_10.distro)

    def test_distro_version_number(self) -> None:
        self.assertEqual(10, ImageBase.DEBIAN_10.version)
        self.assertEqual(12, ImageBase.DEBIAN_12.version)


class TestContainerSupport(unittest.TestCase):
    """Test container support related functionality."""

    def test_image_name(self) -> None:
        self.assertEqual(
            "debian_10:stage_00_base",
            get_image_name(
                ImageBase.DEBIAN_10, ImageStage.STAGE_00_BASE, False
            )
        )

    @run_in_test_environment()
    def test_image_name_no_tool(self) -> None:
        vara_cfg()["container"]["research_tool"] = None
        self.assertEqual(
            "debian_10:stage_20_tool",
            get_image_name(ImageBase.DEBIAN_10, ImageStage.STAGE_20_TOOL, True)
        )

    @run_in_test_environment()
    def test_image_name_vara(self) -> None:
        vara_cfg()["container"]["research_tool"] = "vara"
        self.assertEqual(
            "debian_10:stage_20_tool_vara",
            get_image_name(ImageBase.DEBIAN_10, ImageStage.STAGE_20_TOOL, True)
        )

    @run_in_test_environment()
    def test_create_stage_00(self) -> None:
        """Test base image creation."""
        vara_cfg()["container"]["research_tool"] = None
        vara_cfg()["container"]["from_source"] = False
        bb_cfg()["container"]["from_source"] = False
        bb_cfg()["jobs"] = 42

        base = ImageBase.DEBIAN_10
        stage = ImageStage.STAGE_00_BASE
        stage_builder = StageBuilder(base, stage, "test_stage_00")
        _STAGE_LAYERS[stage](stage_builder)

        layers = stage_builder.layers
        self.check_layer_type(layers[0], FromLayer)

    @run_in_test_environment()
    def test_create_stage_10_from_pip(self) -> None:
        """Test base image creation."""
        vara_cfg()["container"]["research_tool"] = None
        vara_cfg()["container"]["from_source"] = False
        bb_cfg()["container"]["from_source"] = False
        bb_cfg()["jobs"] = 42

        base = ImageBase.DEBIAN_10
        stage = ImageStage.STAGE_10_VARATS
        stage_builder = StageBuilder(base, stage, "test_stage_10")
        stage_builder.layers.from_(
            get_image_name(base, ImageStage.STAGE_00_BASE, False)
        )
        _STAGE_LAYERS[stage](stage_builder)

        layers = stage_builder.layers
        self.check_layer_type(layers[0], FromLayer)

        varats_core_install_layer = self.check_layer_type(layers[2], RunLayer)
        self.assertEqual("pip", varats_core_install_layer.command)
        self.assertTupleEqual(("install", "--ignore-installed", "varats"),
                              varats_core_install_layer.args)

    @run_in_test_environment()
    def test_create_stage_10_from_source(self) -> None:
        """Test varats install from source."""
        vara_cfg()["container"]["research_tool"] = None
        vara_cfg()["container"]["from_source"] = True
        vara_cfg()["container"]["varats_source"] = "varats_src"
        bb_cfg()["container"]["from_source"] = False
        bb_cfg()["jobs"] = 42

        base = ImageBase.DEBIAN_10
        stage = ImageStage.STAGE_10_VARATS
        stage_builder = StageBuilder(base, stage, "test_stage_10")
        stage_builder.layers.from_(
            get_image_name(base, ImageStage.STAGE_00_BASE, False)
        )
        _STAGE_LAYERS[stage](stage_builder)

        layers = stage_builder.layers
        self.check_layer_type(layers[0], FromLayer)

        varats_install_layer = self.check_layer_type(layers[4], RunLayer)
        self.assertEqual("pip", varats_install_layer.command)
        self.assertTupleEqual(("install", "/varats"), varats_install_layer.args)
        mounting_parameters = "type=bind,src=varats_src,target=/varats"
        if buildah_version() >= (1, 24, 0):
            mounting_parameters += ",rw"
        self.assertIn(("mount", mounting_parameters),
                      varats_install_layer.kwargs)

    @run_in_test_environment()
    def test_stage_30(self) -> None:
        """Test mapping of LD_LIBRARY_PATH into container."""
        vara_cfg()["container"]["research_tool"] = None
        vara_cfg()["container"]["from_source"] = False
        bb_cfg()["container"]["from_source"] = False
        bb_cfg()["jobs"] = 42
        bb_cfg()["env"] = {
            "LD_LIBRARY_PATH": ["foo/libs"],
            "PATH": ["/foo/bin"]
        }

        base = ImageBase.DEBIAN_10
        stage = ImageStage.STAGE_30_CONFIG
        stage_builder = StageBuilder(base, stage, "test_stage_30")
        stage_builder.layers.from_(
            get_image_name(base, ImageStage.STAGE_20_TOOL, False)
        )
        _STAGE_LAYERS[stage](stage_builder)

        layers = stage_builder.layers
        self.check_layer_type(layers[0], FromLayer)

        varats_copy_config_layer = self.check_layer_type(layers[1], CopyLayer)
        self.assertEqual(
            "/varats_root/.varats.yaml", varats_copy_config_layer.destination
        )

        varats_config_layer = self.check_layer_type(layers[2], UpdateEnv)
        self.assertTupleEqual(
            ("VARATS_CONFIG_FILE", "/varats_root/.varats.yaml"),
            varats_config_layer.env[0]
        )

        ld_copy_layer = self.check_layer_type(layers[3], CopyLayer)
        self.assertEqual("/varats_root/libs", ld_copy_layer.destination)
        self.assertTupleEqual(("foo/libs",), ld_copy_layer.sources)

        bb_config_layer = self.check_layer_type(layers[4], UpdateEnv)
        self.assertTupleEqual(("BB_VARATS_OUTFILE", "/varats_root/results"),
                              bb_config_layer.env[0])
        self.assertTupleEqual(("BB_VARATS_RESULT", "/varats_root/BC_files"),
                              bb_config_layer.env[1])
        self.assertTupleEqual(("BB_JOBS", "42"), bb_config_layer.env[2])
        self.assertTupleEqual(
            ("BB_ENV", "{LD_LIBRARY_PATH: [/varats_root/libs]}"),
            bb_config_layer.env[3]
        )

        cwd_layer = self.check_layer_type(layers[5], WorkingDirectory)
        self.assertEqual("/app", cwd_layer.directory)

    @run_in_test_environment()
    @mock.patch("varats.tools.research_tools.vara.VaRA.install_exists")
    def test_stage_20_vara(self, mock_install_exists: tp.Any) -> None:
        """Test VaRA install inside container."""
        mock_install_exists.return_value = True
        vara_cfg()["container"]["research_tool"] = "vara"
        vara_cfg()["vara"]["llvm_source_dir"] = "tools_src/vara-llvm-project"
        vara_cfg()["vara"]["llvm_install_dir"] = "tools/VaRA"
        vara_cfg()["container"]["from_source"] = False
        bb_cfg()["container"]["from_source"] = False

        base = ImageBase.DEBIAN_10
        stage = ImageStage.STAGE_20_TOOL
        stage_builder = StageBuilder(base, stage, "test_stage_20")
        stage_builder.layers.from_(
            get_image_name(base, ImageStage.STAGE_10_VARATS, False)
        )
        _STAGE_LAYERS[stage](stage_builder)

        layers = stage_builder.layers
        self.check_layer_type(layers[0], FromLayer)

        vara_copy_layer = self.check_layer_type(layers[1], CopyLayer)
        self.assertEqual(
            "/varats_root/tools/VaRA_DEBIAN_10", vara_copy_layer.destination
        )
        self.assertTupleEqual(("tools/VaRA_DEBIAN_10",),
                              vara_copy_layer.sources)

    @run_in_test_environment()
    def test_stage_00_with_vara(self,) -> None:
        """Test VaRA install inside container."""
        vara_cfg()["container"]["research_tool"] = "vara"
        vara_cfg()["container"]["from_source"] = False
        bb_cfg()["container"]["from_source"] = False

        base = ImageBase.DEBIAN_10
        stage = ImageStage.STAGE_00_BASE
        stage_builder = StageBuilder(base, stage, "test_stage_00")
        _STAGE_LAYERS[stage](stage_builder)

        layers = stage_builder.layers
        self.check_layer_type(layers[0], FromLayer)

        vara_deps_layer = self.check_layer_type(layers[-1], RunLayer)
        self.assertEqual("apt", vara_deps_layer.command)

    @run_in_test_environment()
    def test_stage_30_with_vara(self) -> None:
        """Test VaRA install inside container."""
        vara_cfg()["container"]["research_tool"] = "vara"
        vara_cfg()["container"]["from_source"] = False
        bb_cfg()["container"]["from_source"] = False

        base = ImageBase.DEBIAN_10
        stage = ImageStage.STAGE_30_CONFIG
        stage_builder = StageBuilder(base, stage, "test_stage_30")
        stage_builder.layers.from_(
            get_image_name(base, ImageStage.STAGE_20_TOOL, False)
        )
        _STAGE_LAYERS[stage](stage_builder)

        layers = stage_builder.layers
        self.check_layer_type(layers[0], FromLayer)

        bb_config_layer = self.check_layer_type(layers[3], UpdateEnv)
        self.assertTupleEqual(
            ("BB_ENV", "{PATH: [/varats_root/tools/VaRA_DEBIAN_10/bin]}"),
            bb_config_layer.env[3]
        )

    @run_in_test_environment()
    def test_stage_31(self) -> None:
        """Test VaRA install inside container."""
        vara_cfg()["vara"]["llvm_source_dir"] = "tools_src/vara-llvm-project"
        vara_cfg()["vara"]["llvm_install_dir"] = "tools/VaRA"
        vara_cfg()["container"]["from_source"] = False
        bb_cfg()["container"]["from_source"] = False

        base = ImageBase.DEBIAN_10
        stage = ImageStage.STAGE_31_CONFIG_DEV
        stage_builder = StageBuilder(base, stage, "test_stage_31")
        stage_builder.layers.from_(
            get_image_name(base, ImageStage.STAGE_10_VARATS, False)
        )
        _STAGE_LAYERS[stage](stage_builder)

        layers = stage_builder.layers
        self.check_layer_type(layers[0], FromLayer)

        entrypoint_layer = self.check_layer_type(layers[2], EntryPoint)
        self.assertEqual(("vara-buildsetup",), entrypoint_layer.command)

    LayerTy = tp.TypeVar("LayerTy", bound=Layer)

    def check_layer_type(
        self, layer: Layer, layer_ty: tp.Type[LayerTy]
    ) -> LayerTy:
        self.assertTrue(isinstance(layer, layer_ty))
        return layer
