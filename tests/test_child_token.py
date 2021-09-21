from utils_for_testing import *
from test_token import TestToken
from brownie import Token, Competition, ChildToken, reverts, accounts
import eth_abi

class TestChildToken(TestToken):

    def setup(self):
        self.admin = accounts[0]
        self.manager = accounts[1]
        self.participants = accounts[2:]
        self.parent = Token.deploy("RockCap Token", "RCP", int(Decimal('100000000e18')), {'from': self.admin})
        self.token = ChildToken.deploy("RockCap Token", "RCP", self.manager, {'from': self.admin})
        self.competition = Competition.deploy({'from': self.admin})

        stake_threshold = int(Decimal('10e18'))
        challenge_rewards_threshold = int(Decimal('10e18'))
        self.competition.initialize(stake_threshold, challenge_rewards_threshold, self.token, {'from': self.admin})

        # Bridge over to child token contract on polygon chain
        amount = int(Decimal('50e24'))
        self.parent.transfer(self.manager, amount, {'from': self.admin})
        self.token.deposit(self.admin, eth_abi.encode_single('uint256', amount),  {'from': self.manager})
        verify(self.token.totalSupply(), self.parent.balanceOf(self.manager))

        # airdrop to participants
        total_airdrop = int(Decimal(0.01) * Decimal(self.token.totalSupply()))
        single_airdrop = total_airdrop // (len(accounts) - 1)
        for i in range(len(self.participants)):
            tx = self.token.transfer(self.participants[i], single_airdrop, {'from': self.admin})

        # also airdrop tokens on mainchain
        total_airdrop = int(Decimal(0.01) * Decimal(self.token.totalSupply()))
        single_airdrop = total_airdrop // (len(accounts) - 1)
        for i in range(len(self.participants)):
            tx = self.parent.transfer(self.participants[i], single_airdrop, {'from': self.admin})

    def test_burn(self):
        p1 = self.participants[0]
        p1_bal = self.token.balanceOf(p1)
        burn_amount = random.randint(1, p1_bal)

        # Cannot burn more than own balance.
        with reverts():
            self.token.burn(burn_amount, {'from': p1})

    def test_deposit(self):
        p = self.participants[0]
        main_bal = self.parent.balanceOf(p)
        polygon_bal = self.token.balanceOf(p)
        amount = int(0.3 * main_bal)
        self.parent.transfer(self.manager, amount, {'from': p})
        with reverts():
            self.token.deposit(p, eth_abi.encode_single('uint256', amount), {'from': p})
        self.token.deposit(p, eth_abi.encode_single('uint256', amount), {'from': self.manager})
        verify(main_bal - amount, self.parent.balanceOf(p))
        verify(polygon_bal + amount, self.token.balanceOf(p))
        verify(self.token.totalSupply(), self.parent.balanceOf(self.manager))

    def test_withdraw(self):
        p = self.participants[0]
        main_bal = self.parent.balanceOf(p)
        polygon_bal = self.token.balanceOf(p)
        amount = int(0.5 * polygon_bal)
        with reverts():
            self.token.withdraw(polygon_bal + 1, {'from': p})
        self.token.withdraw(amount, {'from': p})
        self.parent.transfer(p, amount, {'from': self.manager})
        verify(main_bal + amount, self.parent.balanceOf(p))
        verify(polygon_bal - amount, self.token.balanceOf(p))
        verify(self.token.totalSupply(), self.parent.balanceOf(self.manager))

    def test_update_manager(self):
        verify(self.manager, self.token.childChainManagerProxy())
        new_manager = self.participants[-1]
        with reverts():
            self.token.updateChildChainManager(new_manager, {'from': self.manager})
        with reverts():
            self.token.updateChildChainManager('0x{}'.format('0'*40), {'from': self.admin})

        self.token.updateChildChainManager(new_manager, {'from': self.admin})

        self.parent.burn(self.parent.balanceOf(new_manager), {'from': new_manager})
        self.parent.transfer(new_manager, self.parent.balanceOf(self.manager), {'from': self.manager})
        self.manager = new_manager

        verify(self.manager, self.token.childChainManagerProxy())
        verify(self.token.totalSupply(), self.parent.balanceOf(self.manager))

        self.test_deposit()
        self.test_withdraw()










