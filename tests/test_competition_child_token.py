from utils_for_testing import *
from brownie import Token, Competition, ChildToken, reverts, accounts
from test_competition import TestCompetition
import eth_abi

class TestCompetitionChildToken(TestCompetition):
    def setup(self):
        self.use_multi_admin = False
        self.admin = accounts[0]
        self.manager = accounts[1]
        self.participants = accounts[2:]
        self.parent = Token.deploy("RockCap Token", "RCP", int(Decimal('100000000e18')), {'from': self.admin})
        self.token = ChildToken.deploy("RockCap Token", "RCP", self.manager, {'from': self.admin})
        self.competition = Competition.deploy({'from': self.admin})

        stake_threshold = int(Decimal('10e18'))
        challenge_rewards_threshold = int(Decimal('10e18'))
        self.execute_fn(self.competition, self.competition.initialize,
                        [stake_threshold, challenge_rewards_threshold, self.token, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=False)

        # Bridge over to child token contract on polygon chain
        amount = self.parent.totalSupply() // 2
        self.execute_fn(self.parent, self.parent.transfer,
                        [self.manager, amount, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
        self.execute_fn(self.token, self.token.deposit,
                        [self.admin, eth_abi.encode_single('uint256', amount), {'from': self.manager}],
                        self.use_multi_admin, exp_revert=False)
        verify(self.token.totalSupply(), self.parent.balanceOf(self.manager))

        # Authorize Competition
        self.execute_fn(self.token, self.token.authorizeCompetition,
                        [self.competition, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=False)
        verify(True, self.token.competitionIsAuthorized(self.competition))

        # Should not be able to authorize 0 address.
        zero_address = '0x' + '0' * 40
        self.execute_fn(self.token, self.token.authorizeCompetition,
                        [zero_address, {'from': self.admin}], self.use_multi_admin,
                        exp_revert=True)
        verify(False, self.token.competitionIsAuthorized(zero_address))

        # airdrop to participants
        total_airdrop = int(Decimal(0.01) * Decimal(self.token.totalSupply()))
        single_airdrop = total_airdrop // (len(accounts) - 1)
        for i in range(len(self.participants)):
            self.execute_fn(self.token, self.token.transfer,
                            [self.participants[i], single_airdrop, {'from': self.admin}],
                            self.use_multi_admin, exp_revert=False)

        # also airdrop tokens on mainchain
        total_airdrop = int(Decimal(0.01) * Decimal(self.parent.totalSupply()))
        single_airdrop = total_airdrop // (len(accounts) - 1)
        for i in range(len(self.participants)):
            self.execute_fn(self.parent, self.parent.transfer,
                            [self.participants[i], single_airdrop, {'from': self.admin}],
                            self.use_multi_admin, exp_revert=False)