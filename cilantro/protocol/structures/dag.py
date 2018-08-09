from seneca.engine.storage.mysql_intermediate import QueryComponent
from typing import List
from cilantro.messages.transaction.contract import ContractTransaction


class ContractOutputsNode:

    def __init__(self, relative_exec_time: int, contract: ContractTransaction, sql_intermediates: List[QueryComponent],
                 ordering_tuple: tuple):
        self.relative_exec = relative_exec_time
        self.contract = contract
        self.sql_intermediates = sql_intermediates
        self.order = ordering_tuple

        self.children = []
        self.parents = []


class DAG:

    def __init__(self, nodes: List[ContractOutputsNode]=None, edges: List[tuple]=None):
        self.nodes = nodes or []
        self.edges = edges or []

    def append(self, node: ContractOutputsNode) -> None or List[ContractOutputsNode]:
        """
        Appends the Contract to the DAG. If there are ordering conflicts (ie other contracts should of been run AFTER
        the inserted contract), this method will return a list of ContractOutputNodes that need to be rerun in exact
        order.
        :param node:
        :return:
        """
        pass

    # def
