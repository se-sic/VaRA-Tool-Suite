"""General tables module."""
import re
import sys
import typing as tp

if tp.TYPE_CHECKING:
    from varats.tables.table import Table


class TableRegistry(type):
    """Registry for all supported tables."""

    to_snake_case_pattern = re.compile(r'(?<!^)(?=[A-Z])')

    tables: tp.Dict[str, tp.Type[tp.Any]] = {}

    def __init__(
        cls, name: str, bases: tp.Tuple[tp.Any], attrs: tp.Dict[tp.Any, tp.Any]
    ):
        super(TableRegistry, cls).__init__(name, bases, attrs)
        if hasattr(cls, 'NAME'):
            key = getattr(cls, 'NAME')
        else:
            key = TableRegistry.to_snake_case_pattern.sub('_', name).lower()
        TableRegistry.tables[key] = cls

    @staticmethod
    def get_table_types_help_string() -> str:
        """
        Generates help string for visualizing all available tables.

        Returns:
            a help string that contains all available table names.
        """
        return "The following tables are available:\n  " + "\n  ".join([
            key for key in TableRegistry.tables if key != "table"
        ])

    @staticmethod
    def get_class_for_table_type(table: str) -> tp.Type['Table']:
        """
        Get the class for ``table`` from the table registry.

        Args:
            table: the name of the table

        Returns:
            the class implementing the table
        """
        from varats.tables.table import Table
        if table not in TableRegistry.tables:
            sys.exit(
                f"Unknown table '{table}'.\n" +
                TableRegistry.get_table_types_help_string()
            )

        table_cls = TableRegistry.tables[table]
        if not issubclass(table_cls, Table):
            raise AssertionError()
        return table_cls


def build_table(**kwargs: tp.Any) -> None:
    """Build the specified graph."""
    table_type = TableRegistry.get_class_for_table_type(kwargs['table_type'])
    table = table_type(**kwargs)

    if kwargs["view"]:
        from varats.tables.table import TableFormat
        table.format = TableFormat.fancy_grid
        print(table.tabulate())
    else:
        table.save()
