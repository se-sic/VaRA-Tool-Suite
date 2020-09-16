"""General tables module."""
import re
import sys
import typing as tp

if tp.TYPE_CHECKING:
    import varats.tables.table as table  # pylint: disable=unused-import


class TableRegistry(type):
    """Registry for all supported tables."""

    TO_SNAKE_CASE_PATTERN = re.compile(r'(?<!^)(?=[A-Z])')

    tables: tp.Dict[str, tp.Type[tp.Any]] = {}
    tables_discovered = False

    def __init__(
        cls, name: str, bases: tp.Tuple[tp.Any], attrs: tp.Dict[tp.Any, tp.Any]
    ):
        super(TableRegistry, cls).__init__(name, bases, attrs)
        if hasattr(cls, 'NAME'):
            key = getattr(cls, 'NAME')
        else:
            key = TableRegistry.TO_SNAKE_CASE_PATTERN.sub('_', name).lower()
        TableRegistry.tables[key] = cls

    @staticmethod
    def __ensure_tables_are_loaded() -> None:
        """Ensures that all table files are loaded into the registry."""
        if not TableRegistry.tables_discovered:
            from . import discover  # pylint: disable=C0415
            discover()
            TableRegistry.tables_discovered = True

    @staticmethod
    def get_table_types_help_string() -> str:
        """
        Generates help string for visualizing all available tables.

        Returns:
            a help string that contains all available table names.
        """
        TableRegistry.__ensure_tables_are_loaded()
        return "The following tables are available:\n  " + "\n  ".join([
            key for key in TableRegistry.tables if key != "table"
        ])

    @staticmethod
    def get_class_for_table_type(table_param: str) -> tp.Type['table.Table']:
        """
        Get the class for ``table`` from the table registry.

        Args:
            table: the name of the table

        Returns:
            the class implementing the table
        """
        TableRegistry.__ensure_tables_are_loaded()

        from varats.tables.table import Table  # pylint: disable=C0415
        if table_param not in TableRegistry.tables:
            sys.exit(
                f"Unknown table '{table_param}'.\n" +
                TableRegistry.get_table_types_help_string()
            )

        table_cls = TableRegistry.tables[table_param]
        if not issubclass(table_cls, Table):
            raise AssertionError()
        return table_cls


def build_table(**kwargs: tp.Any) -> None:
    """Build the specified table."""
    table_type = TableRegistry.get_class_for_table_type(kwargs['table_type'])
    new_table_obj = table_type(**kwargs)

    if kwargs["view"]:
        from varats.tables.table import TableFormat  # pylint: disable=C0415
        new_table_obj.format = TableFormat.fancy_grid
        print(new_table_obj.tabulate())
    else:
        new_table_obj.save()
