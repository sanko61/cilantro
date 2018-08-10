from seneca.engine.storage.mysql_intermediate import Query
from typing import List
from cilantro.messages.transaction.contract import ContractTransaction

WILDCARD = '*'


class ProcessedSqlIntermediate:

    def __init__(self, sql_intermediate: Query):
        self.intermediate = sql_intermediate

        self.contract_name, self.table_name, self.row_name = '', '', ''

class ContractOutputsNode:

    def __init__(self, relative_exec_time: int, contract: ContractTransaction, sql_intermediates: List[Query],
                 ordering_tuple: tuple):
        self.relative_exec = relative_exec_time
        self.contract = contract
        self.sql_intermediates = sql_intermediates
        self.order = ordering_tuple

        self.children = []
        self.parents = []

    def collides(self, other) -> bool:
        pass


class DAG:

    def __init__(self, nodes: List[ContractOutputsNode]=None, edges: List[tuple]=None):
        self.nodes = nodes or []
        self.edges = edges or []
        self.latest_dependencies = {}

    def append(self, node: ContractOutputsNode) -> None or List[ContractOutputsNode]:
        """
        Appends the Contract to the DAG. If there are ordering conflicts (ie other contracts should of been run AFTER
        the inserted contract), this method will return a list of ContractOutputNodes that need to be rerun in exact
        order.
        :param node:
        :return:
        """


