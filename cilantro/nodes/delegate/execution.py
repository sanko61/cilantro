from contracting.execution.executor import Executor
from contracting.stdlib.bridge.time import Datetime
from contracting.db.encoder import encode, decode, safe_repr
from cilantro.crypto.canonical import tx_hash_from_tx, format_dictionary, merklize
from cilantro.logger.base import get_logger
from datetime import datetime

log = get_logger('EXE')

import multiprocessing as mp
import copy
from time import time, sleep
import queue

__N_WORKER_PER_DELEGATES__ = 4
__N_DELEGATES__ = 2
__N_WORKER__ = __N_WORKER_PER_DELEGATES__ * __N_DELEGATES__


PoolExecutor = None
stop_cmd = None
pool = []
busy_pool = []

N_TEST = 8
WORKER_SLEEP = 0.0001
RESULT_SLEEP = 0.01
POOL_WAIT_SLEEP = 0.01

TX_RERUN_SLEEP = 1
N_TRY_PER_TX = 3

def setPoolExecutor(executor):
    global PoolExecutor
    PoolExecutor = executor

def execute_tx(transaction, stamp_cost, environment: dict={}, tx_number=0, ini_writes=None):
    global PoolExecutor
    executor = PoolExecutor
    if ini_writes is not None:
        log.debug(f'ini_writes={ini_writes} cash ={executor.driver.cache}')
        p_cashe = executor.driver.cache
        for k, v in ini_writes.items():
            if k in p_cashe:
                log.debug(f"deleted {k} from cash")
                del p_cashe[k]

    output = executor.execute(
        sender=transaction['payload']['sender'],
        contract_name=transaction['payload']['contract'],
        function_name=transaction['payload']['function'],
        stamps=transaction['payload']['stamps_supplied'],
        stamp_cost=stamp_cost,
        kwargs=transaction['payload']['kwargs'],
        environment=environment,
        auto_commit=False
    )
    log.debug(output)

    tx_hash = tx_hash_from_tx(transaction)

    writes = [{'key': k, 'value': v} for k, v in output['writes'].items()]
    p_writes = executor.driver.pending_writes
    p_reads = executor.driver.reads

    tx_output = {
        'hash': tx_hash,
        'transaction': transaction,
        'status': output['status_code'],
        'state': writes,
        'stamps_used': output['stamps_used'],
        'result': safe_repr(output['result']),
        'tx_number': tx_number,
        'p_writes': p_writes,
        'reads': p_reads,
    }
    tx_output = format_dictionary(tx_output)
    executor.driver.pending_writes.clear() # add
    return tx_output


def generate_environment(driver, timestamp, input_hash, bhash='0' * 64, num=1):
    now = Datetime._from_datetime(
        datetime.utcfromtimestamp(timestamp)
    )

    return {
        'block_hash': bhash,
        'block_num': num,
        '__input_hash': input_hash,  # Used for deterministic entropy for random games
        'now': now
    }


class ProcessThread(mp.Process):
    def __init__(self, q_in, q_out, s_stop):
        super(ProcessThread, self).__init__()
        self.q_in = q_in
        self.q_out = q_out
        self.s_stop = s_stop

    def run(self):
        while 1:
            if (int(self.s_stop.value) == 1):
                # print("Process stopped")
                break
            # print("Process run")
            try:
                x = self.q_in.get_nowait()
                if x is not None:
                    # work()
                    try:
                        tx_input = x
                        if len(tx_input) >= 5:
                            ini_ps = tx_input[4]
                        else:
                            ini_ps = None
                        output = execute_tx(tx_input[0], tx_input[1], environment= tx_input[2], tx_number=tx_input[3], ini_writes=ini_ps)
                        self.q_out.put(output)
                    except Exception as err:
                        log.error(f"Worker stopped after exception={err}")
                        break
            except queue.Empty:
                sleep(WORKER_SLEEP)
        # print("Process exit")
        return


def start_pool():
    global stop_cmd
    stop_cmd = mp.Value('i', 0)

    for i in range(__N_WORKER__):
        queue_in1 = mp.Queue()
        queue_out1 = mp.Queue()
        p = ProcessThread(queue_in1, queue_out1,stop_cmd)
        pool.append(p)
        busy_pool.append(0)
        p.start()

    for i in range(5):
        n_proc = 0
        for i in range(__N_WORKER__):
            if pool[i].is_alive():
                n_proc += 1
        if n_proc == __N_WORKER__:
            log.info(f" Workers started OK")
            return True
        sleep(1)
    log.error(f" Can't start workers")
    return False


def get_pool(n_needed):
    rez_pool={}
    cnt=0
    n_step = 0
    if n_needed > 0:
        if n_needed > __N_WORKER_PER_DELEGATES__:
            n_needed = __N_WORKER_PER_DELEGATES__
        while n_step < 3:
            for i in range(__N_WORKER__):
                if busy_pool[i]== 0:
                    busy_pool[i] = 1
                    rez_pool[cnt] = i
                    cnt += 1
                if cnt >= n_needed:
                    break
            if cnt > 0:
                break
            else:
                time.sleep(POOL_WAIT_SLEEP)
                n_step += 1
    return rez_pool, cnt

def free_pool(rez_pool):
    for k,v in rez_pool.items():
        busy_pool[v] = 0


def stop_pool():
    if pool is None:
        return
    global stop_cmd
    stop_cmd.value = 1
    for i in range(__N_WORKER__):
        pool[i].join()
    log.info(f" Workers stopped OK")


def wait_tx_result(N_tx, work_pool):
    active_workers = len(work_pool)
    kk = 0
    k_step = 0
    k_wait = N_tx * N_TRY_PER_TX
    rez = []
    while k_step < k_wait:
        for i_tx in range(N_tx):
            try:
                k_step += 1
                i_prc = work_pool[i_tx % active_workers]
                r = pool[i_prc].q_out.get_nowait()
                if r is not None:
                    rez.append(r)
                    kk += 1
            except queue.Empty:
                sleep(RESULT_SLEEP)
        if kk >= N_tx:
            break
    return rez


def check_conflict(tx_data):
    tx_bad0 = set()
    for tx0 in tx_data:
        tx_hash = tx0['hash']
        conflict = False
        for tx in tx_data:
            if tx_hash != tx['hash']:
                for k, v in tx['p_writes'].items():
                    if v is not None:
                        if k in tx0['reads']:
                            conflict = True
                            break
                        if k in tx0['p_writes']:
                            conflict = True
                            break
                if conflict:
                    tx_bad0.append(tx_hash)
                    tx_bad0.append(tx['hash'])
    tx_bad = list(tx_bad0)
    return tx_bad


def check_conflict2(rez_batch):
    tx_bad0 = set()
    tx_index = {}
    i1a = 0
    for tx_data0 in rez_batch:
        i2a = 0
        for tx0 in tx_data0:
            tx_hash = tx0['hash']
            conflict = False
            i1b = 0
            for tx_data in rez_batch:
                i2b = 0
                for tx in tx_data:
                    if tx_hash != tx['hash']:
                        for k, v in tx['p_writes'].items():
                            if v is not None:
                                if k in tx0['reads']:
                                    conflict = True
                                    break
                                if k in tx0['p_writes']:
                                    conflict = True
                                    break
                    if conflict:
                        tx_bad0.append(tx['hash'])  # first
                        tx_bad0.append(tx_hash)  # second
                        tx_index[tx_hash] = (i1a,i2a)
                        tx_index[tx['hash']] = (i1b, i2b)
                    i2b += 1
            i2a += 1
    tx_bad = list(tx_bad0)


    #DEBUG mode tx_bad.append(rez_batch[0][0]['hash'])
    #DEBUG mode tx_index[rez_batch[0][0]['hash']] = (0,0)
    tx_bad = []
    tx_index = {}
    for i1 in range(len(rez_batch)):
        for i2 in range(len(rez_batch[i1])):
            tx_bad.append(rez_batch[i1][i2]['hash'])
            tx_index[rez_batch[i1][i2]['hash']] = (i1,i2)
    # DEBUG mode  END

    return tx_bad, tx_index


def execute_tx_batch(executor, driver, batch, timestamp, input_hash, stamp_cost, bhash='0' * 64, num=1):

    environment = generate_environment(driver, timestamp, input_hash, bhash, num)
    setPoolExecutor(executor)

    global pool
    if len(pool)==0:
        start_pool()
        log.debug(f'Initialyze pool {len(pool)}')

    work_pool, active_workers = get_pool(len(batch['transactions']))
    i= 0
    s = time()
    log.debug(f"Start Pool len={active_workers}  prc={work_pool}")

    for transaction in batch['transactions']:
        log.debug(f'Transaction {i}   {type(executor)}')
        it = (transaction, stamp_cost, environment, i)
        i_prc = work_pool [i % active_workers]
        pool[i_prc].q_in.put(it)
        i += 1

    N_tx = i
    result_list2 = wait_tx_result(N_tx, work_pool)
    free_pool(work_pool)

    log.debug(f"End of pool. result_list={result_list2}")

    tx_data = copy.deepcopy(result_list2)
    tx_done_ok = [ tx['tx_number'] for tx in tx_data]
    log.debug(f"tx_data={len(tx_data)}  tx_done_ok={tx_done_ok} duration= {time() - s}")

    return tx_data


def prepare_data(tx_data):
    out_data = []
    for tx in tx_data:
        tx_output = {
            'hash': tx['hash'],
            'transaction': tx['transaction'],
            'status': tx['status'],
            'state': tx['state'],
            'stamps_used': tx['stamps_used'],
            'result': tx['result'],
        }
        tx_output = format_dictionary(tx_output)
        out_data.append(tx_output)
    return out_data


def rerun_txs(executor, driver, batch, timestamp, input_hash, stamp_cost, bhash='0' * 64, num=1, tx_idx=None, result0=None,):

    environment = generate_environment(driver, timestamp, input_hash, bhash, num)
    setPoolExecutor(executor)

    global pool
    work_pool, active_workers = get_pool(1) #One core for conflicting txs

    i= 0
    s = time()
    log.debug(f"Start rerun len={active_workers}  prc={work_pool}")
    executor.driver.pending_writes.clear()

    for tx_hash in batch:
        i1,i2 = tx_idx[tx_hash]
        transaction = result0[i1][i2]['transaction']
        log.debug(f'Transaction {i} {transaction} {type(executor)}')
        ini_pwrites = result0[i1][i2]['p_writes']
        it = (transaction, stamp_cost, environment, i, ini_pwrites)
        i_prc =work_pool[0]
        pool[i_prc].q_in.put(it)
        i += 1

    N_tx = i
    tx_data = wait_tx_result(N_tx, work_pool)
    free_pool(work_pool)
    i = 0
    for tx_hash in batch:
        i1,i2 = tx_idx[tx_hash]
        result0[i1][i2] = tx_data[i]
        i += 1

    log.debug(f"End of rerun. result_list={result0} duration= {time() - s}")

    return result0


def execute_work(executor, driver, work, wallet, previous_block_hash, current_height=0, stamp_cost=20000, parallelism=4):
    # Assume single threaded, single process for now.
    rez_batch = []
    for tx_batch in work:
        results = execute_tx_batch(
            executor=executor,
            driver=driver,
            batch=tx_batch,
            timestamp=tx_batch['timestamp'],
            input_hash=tx_batch['input_hash'],
            stamp_cost=stamp_cost,
            bhash=previous_block_hash,
            num=current_height
        )
        rez_batch.append(results)

    tx_bad, tx_bad_idx = check_conflict2(rez_batch)
    log.debug(f"tx_bad={tx_bad} tx_bad_idx= {tx_bad_idx}")

    rez_batch2 = rerun_txs(
        executor=executor,
        driver=driver,
        batch=tx_bad,
        timestamp= work[0]['timestamp'],
        input_hash=work[0]['input_hash'],
        stamp_cost=stamp_cost,
        bhash=previous_block_hash,
        num=current_height,
        tx_idx = tx_bad_idx,
        result0 = rez_batch,
    )
    log.debug(f"rez_batch2={rez_batch2}")

    subblocks = []
    i = 0
    for results0 in rez_batch:
        results = prepare_data(results0)
        tx_batch = work[i]

        if len(results) > 0:
            merkle = merklize([encode(r).encode() for r in results])
            proof = wallet.sign(merkle[0])
        else:
            merkle = merklize([bytes.fromhex(tx_batch['input_hash'])])
            proof = wallet.sign(tx_batch['input_hash'])

        merkle_tree = {
            'leaves': merkle,
            'signature': proof
        }

        sbc = {
            'input_hash': tx_batch['input_hash'],
            'transactions': results,
            'merkle_tree': merkle_tree,
            'signer': wallet.verifying_key,
            'subblock': i % parallelism,
            'previous': previous_block_hash
        }

        sbc = format_dictionary(sbc)

        subblocks.append(sbc)
        i += 1

    return subblocks
