import string, random, time
from hashlib import sha256
from web3 import exceptions as w3exceptions
from decimal import Decimal
from web3 import Web3
from tqdm import tqdm
import csv
from brownie import project
op = project.load("OpenZeppelin//openzeppelin-contracts@4.8.0")


def get_fn_id(fn_string):
    hashed_string = Web3.keccak(fn_string.encode('utf-8')).hex()[2:]
    return '0x{}'.format(hashed_string[:8])

def getRandomString(n=128):
    return ''.join(random.choice(string.ascii_letters) for i in range(n))

def getRandomSelection(array, min_num = 1):
    return random.sample(array, random.randint(min_num, len(array)))

def getHash():
    content = getRandomString()
    return sha256(content.encode('utf-8')).hexdigest()

def getTimestamp():
    now = int(time.time() * 1000)
    return now + random.randint(86400000, 864000000)

def verify(expected, actual):
    assert expected == actual, '\nExpected: {}\nActual: {}'.format(expected, actual)

def uint_to_float(value):
    return Decimal(value) / Decimal('1e6')

def progress_bar(work_done, prefix=''):
    print("\r"+prefix+"Progress: [{0:50s}] {1:.1f}%".format('#' * int(work_done * 50), work_done * 100), end="", flush=True)
    if work_done == 1:
        print()