import typing as tp

from varats.table.table import Table
from varats.table.tables import TableFormat, TableGenerator


class WorkloadIntensityTable(Table, table_name="workload_intensity"):

    def tabulate(self, table_format: TableFormat, wrap_table: bool) -> str:

        pass


class WorkloadIntensityTableGenerator(
    TableGenerator, generator_name="workload-intensity", options=[]
):

    def generate(self) -> tp.List[Table]:

        return [WorkloadIntensityTable(self.table_config, **self.table_kwargs)]
