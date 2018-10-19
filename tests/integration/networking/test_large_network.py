from cilantro.utils.test.testnet_config import set_testnet_config
set_testnet_config('2-2-4.json')
from cilantro.constants.testnet import *
from cilantro.constants.test_suites import CI_FACTOR

from cilantro.utils.test.mp_test_case import MPTestCase, vmnet_test, CILANTRO_PATH
from cilantro.utils.test.mp_testables import MPPubSubAuth
from cilantro.storage.db import VKBook
import unittest, time


def config_sub(test_obj):
    from unittest.mock import MagicMock
    test_obj.handle_sub = MagicMock()
    return test_obj


class TestLargeNetwork(MPTestCase):
    config_file = '{}/cilantro/vmnet_configs/cilantro-nodes-8.json'.format(CILANTRO_PATH)
    log_lvl = 0

    @vmnet_test(run_webui=True)
    def test_2_2_4(self):
        """
        Tests creating a network with 2 Masternodes, 2 Witnesses, and 4 Delegates. Ensures everyone can connect to
        each other.
        """
        def assert_sub(test_obj):
            c_args = test_obj.handle_sub.call_args_list
            assert len(c_args) == 7, "Expected 7 messages (one from each node). Instead, got:\n{}".format(c_args)

        BLOCK = False
        time.sleep(1)

        mn_0 = MPPubSubAuth(sk=TESTNET_MASTERNODES[0]['sk'], name='[node_1]MN_0', config_fn=config_sub, assert_fn=assert_sub, block_until_rdy=BLOCK)
        time.sleep(3)  # Pause after first MN boots (so we are extra sure he will be available for discovery)
        mn_1 = MPPubSubAuth(sk=TESTNET_MASTERNODES[1]['sk'], name='[node_2]MN_1', config_fn=config_sub, assert_fn=assert_sub, block_until_rdy=BLOCK)

        wit_0 = MPPubSubAuth(sk=TESTNET_WITNESSES[0]['sk'], name='[node_3]WITNESS_0', config_fn=config_sub, assert_fn=assert_sub, block_until_rdy=BLOCK)
        wit_1 = MPPubSubAuth(sk=TESTNET_WITNESSES[1]['sk'], name='[node_4]WITNESS_1', config_fn=config_sub, assert_fn=assert_sub, block_until_rdy=BLOCK)

        del_0 = MPPubSubAuth(sk=TESTNET_DELEGATES[0]['sk'], name='[node_5]DELEGATE_0', config_fn=config_sub, assert_fn=assert_sub, block_until_rdy=BLOCK)
        del_1 = MPPubSubAuth(sk=TESTNET_DELEGATES[1]['sk'], name='[node_6]DELEGATE_1', config_fn=config_sub, assert_fn=assert_sub, block_until_rdy=BLOCK)
        del_2 = MPPubSubAuth(sk=TESTNET_DELEGATES[2]['sk'], name='[node_7]DELEGATE_2', config_fn=config_sub, assert_fn=assert_sub, block_until_rdy=BLOCK)
        del_3 = MPPubSubAuth(sk=TESTNET_DELEGATES[3]['sk'], name='[node_8]DELEGATE_3', config_fn=config_sub, assert_fn=assert_sub, block_until_rdy=BLOCK)

        time.sleep(20*CI_FACTOR)  # Nap while nodes hookup

        all_nodes = (mn_0, mn_1, wit_0, wit_1, del_0, del_1, del_2, del_3)
        all_vks = (TESTNET_MASTERNODES[0]['vk'], TESTNET_MASTERNODES[1]['vk'], TESTNET_WITNESSES[0]['vk'],
                   TESTNET_WITNESSES[1]['vk'], TESTNET_DELEGATES[0]['vk'], TESTNET_DELEGATES[1]['vk'],
                   TESTNET_DELEGATES[2]['vk'], TESTNET_DELEGATES[3]['vk'],)

        # Each node PUBS on its own IP
        for n in all_nodes:
            n.add_pub_socket(ip=n.ip, secure=True)

        # Each node SUBs to everyone else (except themselves)
        for i, n in enumerate(all_nodes):
            n.add_sub_socket(secure=True)
            node_vk = all_vks[i]
            for vk in VKBook.get_all():
                if vk == node_vk: continue
                n.connect_sub(vk=vk)

        time.sleep(20*CI_FACTOR)  # Allow time for VK lookups

        # Make each node pub a msg
        for n in all_nodes:
            n.send_pub("hi from {} with ip {}".format(n.name, n.ip).encode())

        self.start(timeout=20)

    # @vmnet_test(run_webui=True)
    # def test_2_2(self):
    #     """
    #     Tests creating a network with 2 Masternodes, 2 Witnesses, and 4 Delegates. Ensures everyone can connect to
    #     each other.
    #     """
    #     def assert_sub(test_obj):
    #         c_args = test_obj.handle_sub.call_args_list
    #         assert len(c_args) == 3, "Expected 3 messages (one from each node). Instead, got:\n{}".format(c_args)
    #
    #     BLOCK = False
    #     time.sleep(1)
    #
    #     mn_0 = MPPubSubAuth(sk=TESTNET_MASTERNODES[0]['sk'], name='[node_1]MN_0', config_fn=config_sub, assert_fn=assert_sub, block_until_rdy=BLOCK)
    #     time.sleep(2)  # Pause after first MN boots (so we are extra sure he will be available for discovery)
    #     mn_1 = MPPubSubAuth(sk=TESTNET_MASTERNODES[1]['sk'], name='[node_2]MN_1', config_fn=config_sub, assert_fn=assert_sub, block_until_rdy=BLOCK)
    #
    #     wit_0 = MPPubSubAuth(sk=TESTNET_WITNESSES[0]['sk'], name='[node_3]WITNESS_0', config_fn=config_sub, assert_fn=assert_sub, block_until_rdy=BLOCK)
    #     wit_1 = MPPubSubAuth(sk=TESTNET_WITNESSES[1]['sk'], name='[node_4]WITNESS_1', config_fn=config_sub, assert_fn=assert_sub, block_until_rdy=BLOCK)
    #
    #     time.sleep(16*CI_FACTOR)  # Nap while nodes hookup
    #
    #     all_nodes = (mn_0, mn_1, wit_0, wit_1)
    #     all_vks = (TESTNET_MASTERNODES[0]['vk'], TESTNET_MASTERNODES[1]['vk'], TESTNET_WITNESSES[0]['vk'],
    #                TESTNET_WITNESSES[1]['vk'])
    #
    #     # Each node PUBS on its own IP
    #     for n in all_nodes:
    #         n.add_pub_socket(ip=n.ip, secure=True)
    #
    #     # Each node SUBs to everyone else (except themselves)
    #     for i, n in enumerate(all_nodes):
    #         n.add_sub_socket(secure=True)
    #         node_vk = all_vks[i]
    #         for vk in all_vks:
    #             if vk == node_vk: continue
    #             n.connect_sub(vk=vk)
    #
    #     time.sleep(16*CI_FACTOR)  # Allow time for VK lookups
    #
    #     # Make each node pub a msg
    #     for n in all_nodes:
    #         n.send_pub("hi from {} with ip {}".format(n.name, n.ip).encode())
    #
    #     self.start(timeout=30)


if __name__ == '__main__':
    unittest.main()

# FOR LOOKING UP f6a237b07376a4252bc4af21ce5e76fad9e7c180334559d7899a3d9d9dd532ca
# l = [('82367654d8959521992ebc8603676102a5c346f6b2f748f661d160be7610c015',
#     [
#         [663003795778126164802955979159404205349656965073, '172.29.0.4', 20003, '82367654d8959521992ebc8603676102a5c346f6b2f748f661d160be7610c015'],
#         [1092838824646018356267364973824546943271778925437, '172.29.0.2', 20003, '4d09a915a0b4cac25f5e427fb5e347e0d102697502283bdbc4771b846aaff9e8']
#     ]),
#
#      ('7fed90e37de48736901a3640eda2a2e5837ba23b8dc5993f1bd04733b8e23ca9',
#       [
#          [663003795778126164802955979159404205349656965073, '172.29.0.4', 20003, '82367654d8959521992ebc8603676102a5c346f6b2f748f661d160be7610c015'],
#          [1092838824646018356267364973824546943271778925437, '172.29.0.2', 20003, '4d09a915a0b4cac25f5e427fb5e347e0d102697502283bdbc4771b846aaff9e8']
#       ]),
#      (
#      '4d09a915a0b4cac25f5e427fb5e347e0d102697502283bdbc4771b846aaff9e8',
#      [
#          [663003795778126164802955979159404205349656965073, '172.29.0.4', 20003, '82367654d8959521992ebc8603676102a5c346f6b2f748f661d160be7610c015'],
#          [1092838824646018356267364973824546943271778925437, '172.29.0.2', 20003, '4d09a915a0b4cac25f5e427fb5e347e0d102697502283bdbc4771b846aaff9e8']]
#      )]
