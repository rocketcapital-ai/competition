
from utils_for_testing import *
from brownie import Contract, MultiSig, TransparentUpgradeableProxy, ProxyAdmin, Token, Competition, ChildToken, reverts, accounts
from test_competition import TestCompetition
import eth_abi

class TestCompetitionChildTokenProxyMultiSig(TestCompetition):
    def setup(self):
        assert len(accounts) >= 20, 'Please run this test with at least 20 accounts.'
        self.use_multi_admin = True
        self.admin = accounts[0]
        self.owners = accounts[1:11]
        self.non_owners = accounts[11:14]
        self.manager = accounts[14]
        self.participants = accounts[14:]
        self.required = 6
        self.multi_sig = MultiSig.deploy(self.owners, self.required, {'from': self.admin})
        self.parent = Token.deploy("RockCap Token", "RCP", int(Decimal('100000000e18')), {'from': self.admin})
        self.token = ChildToken.deploy("RockCap Token", "RCP", self.manager, {'from': self.admin})
        self.comp_logic = Competition.deploy({'from': self.admin})

        # Hand admin rights to multisig contract
        self.main_admin_hash = self.comp_logic.RCI_MAIN_ADMIN()
        self.child_admin_hash = self.comp_logic.RCI_CHILD_ADMIN()

        self.parent.grantRole(self.main_admin_hash, self.multi_sig, {'from': self.admin})
        self.parent.grantRole(self.child_admin_hash, self.multi_sig, {'from': self.admin})
        self.parent.renounceRole(self.main_admin_hash, self.admin, {'from': self.admin})
        self.parent.renounceRole(self.child_admin_hash, self.admin, {'from': self.admin})

        self.token.grantRole(self.main_admin_hash, self.multi_sig, {'from': self.admin})
        self.token.grantRole(self.child_admin_hash, self.multi_sig, {'from': self.admin})
        self.parent.renounceRole(self.main_admin_hash, self.admin, {'from': self.admin})
        self.parent.renounceRole(self.child_admin_hash, self.admin, {'from': self.admin})

        # Bridge over to child token contract on polygon chain
        self.parent.transfer(self.multi_sig, self.parent.balanceOf(self.admin), {'from': self.admin})
        amount = self.parent.balanceOf(self.multi_sig) // 2
        self.execute_fn(self.parent, self.parent.transfer,
                        [self.manager, amount, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
        self.execute_fn(self.token, self.token.deposit,
                        [self.multi_sig, eth_abi.encode_single('uint256', amount), {'from': self.manager}],
                        use_multi_admin=False, exp_revert=False)
        verify(self.token.totalSupply(), self.parent.balanceOf(self.manager))

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
        # setup proxy
        self.proxy_admin = ProxyAdmin.deploy({'from': self.admin})

        stake_threshold = int(Decimal('10e18'))
        challenge_rewards_threshold = int(Decimal('10e18'))
        data = self.comp_logic.initialize.encode_input(stake_threshold, challenge_rewards_threshold, self.token)
        self.proxy = TransparentUpgradeableProxy.deploy(self.comp_logic, self.proxy_admin, data, {'from': self.admin})

        TransparentUpgradeableProxy.remove(self.proxy)
        combined_abi = TransparentUpgradeableProxy.abi + Competition.abi
        self.competition = Contract.from_abi("doesnotmatter", self.proxy, combined_abi)

        self.competition.grantRole(self.main_admin_hash, self.multi_sig, {'from': self.admin})
        self.competition.grantRole(self.child_admin_hash, self.multi_sig, {'from': self.admin})
        self.competition.renounceRole(self.main_admin_hash, self.admin, {'from': self.admin})
        self.competition.renounceRole(self.child_admin_hash, self.admin, {'from': self.admin})

        # Authorize Competition
        self.execute_fn(self.token, self.token.authorizeCompetition,
                        [self.competition, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=False)
        verify(True, self.token.competitionIsAuthorized(self.competition))

        verify(stake_threshold, self.competition.getStakeThreshold())
        verify(challenge_rewards_threshold, self.competition.getRewardsThreshold())
        verify(0, self.competition.getLatestChallengeNumber())
        verify(4, self.competition.getPhase(0))
        verify(Decimal('0.2'), uint_to_float(self.competition.getChallengeRewardsPercentageInWei()))
        verify(Decimal('0.6'), uint_to_float(self.competition.getTournamentRewardsPercentageInWei()))
        verify(self.token, self.competition.getTokenAddress())

    def execute_one_transaction(self, dest, data, execute_should_fail=False, value=0):
        proposer = self.owners[0]
        non_owner = self.non_owners[-1]

        with reverts():
            self.multi_sig.submitTransaction(dest, value, data, {'from': non_owner})

        self.multi_sig.submitTransaction(dest, value, data, {'from': proposer})
        count = self.multi_sig.getTransactionCount(True, False)
        txes = self.multi_sig.getTransactionIds(0, count, True, False)
        latest_id = txes[-1]

        verify(1, self.multi_sig.getConfirmationCount(latest_id))
        verify([proposer], self.multi_sig.getConfirmations(latest_id))
        verify(False, self.multi_sig.isConfirmed(latest_id))

        with reverts():
            self.multi_sig.confirmTransaction(latest_id, {'from': proposer})

        self.multi_sig.revokeConfirmation(latest_id, {'from': proposer})
        verify(0, self.multi_sig.getConfirmationCount(latest_id))
        verify([], self.multi_sig.getConfirmations(latest_id))
        verify(False, self.multi_sig.isConfirmed(latest_id))

        tx = self.multi_sig.transactions(latest_id)
        verify(dest, tx[0])     # Destination
        verify(value, tx[1])    # Value
        verify(data, tx[2])     # Data
        verify(False, tx[3])    # Executed

        # A small quirk in this implementation:
        # Once owners are removed, their records, such as their confirmations, are no longer considered.
        # For example, if an owner confirms a transaction to remove themselves as an owner,
        # and the transaction is executed, the transaction will be recorded as executed,
        # but the result from getConfirmationCount will be 1 less than `required`, since the confirmation from this
        # ex-owner is no longer considered.

        for i in range(self.required):
            self.multi_sig.confirmTransaction(latest_id, {'from': self.owners[i]})
            tx = self.multi_sig.transactions(latest_id)

            if i + 1 == self.required:
                if execute_should_fail:
                    verify(False, tx[3])
                else:
                    verify(True, tx[3])
            else:
                verify(i + 1, self.multi_sig.getConfirmationCount(latest_id))
                verify(set(self.owners[:i+1]), set(self.multi_sig.getConfirmations(latest_id)))
                verify(False, self.multi_sig.isConfirmed(latest_id))
                verify(False, tx[3])