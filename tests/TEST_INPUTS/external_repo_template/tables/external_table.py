"""Dummy external table generator for registry tests."""

from varats.table.tables import TableGenerator


class ExternalTableGenerator(
    TableGenerator,
    generator_name="external_table",
    options=[]
):
    """Dummy external table generator."""

    def generate(self):
        return []
