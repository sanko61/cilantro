import unittest
from unittest import TestCase
from cilantro.logger import get_logger
import seneca.smart_contract_user_libs.stdlib as std
from tests.contracts.smart_contract_testcase import *
from seneca.execute_sc import execute_contract

log = get_logger("TestToken")

class TestToken(SmartContractTestCase):

    @contract(
        ('STU', 'token'),
        ('falcon', 'token'),
    )
    def test_transfer(self, stu, falcon):
        stu.transfer(falcon, 1000)
        falcon_balance = falcon.balance_of(falcon)
        print(falcon_balance)

if __name__ == '__main__':
    unittest.main()