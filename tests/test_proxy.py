from utils_for_testing import *
from brownie import Contract, Token, Competition,ProxyAdmin, TransparentUpgradeableProxy, BadCompetition3, reverts, accounts


class TestProxy:

    def setup(self):
        self.admin = accounts[0]
        self.participants = accounts[1:]
        self.token = Token.deploy("RockCap Token", "RCP", int(Decimal('100000000e18')), {'from': self.admin})
        self.comp_logic = Competition.deploy({'from': self.admin})

        stake_threshold = int(Decimal('10e18'))
        challenge_rewards_threshold = int(Decimal('10e18'))

        self.proxy_admin = ProxyAdmin.deploy({'from': self.admin})
        data = self.comp_logic.initialize.encode_input(stake_threshold, challenge_rewards_threshold, self.token)
        self.proxy = TransparentUpgradeableProxy.deploy(self.comp_logic, self.proxy_admin, data, {'from': self.admin})

        TransparentUpgradeableProxy.remove(self.proxy)
        combined_abi = TransparentUpgradeableProxy.abi + Competition.abi
        self.competition = Contract.from_abi("doesnotmatter", self.proxy, combined_abi)

        self.token.authorizeCompetition(self.competition, {'from': self.admin})

        verify(stake_threshold, self.competition.getStakeThreshold())
        verify(challenge_rewards_threshold, self.competition.getRewardsThreshold())
        verify(0, self.competition.getLatestChallengeNumber())
        verify(4, self.competition.getPhase(0))
        verify(Decimal('0.2'), uint_to_float(self.competition.getChallengeRewardsPercentageInWei()))
        verify(Decimal('0.6'), uint_to_float(self.competition.getTournamentRewardsPercentageInWei()))
        verify(self.token, self.competition.getTokenAddress())

    def test_admin(self):
        with reverts():
            self.proxy.admin({'from': self.admin})
        with reverts():
            self.proxy.implementation({'from': self.admin})

        this_admin = self.proxy_admin.getProxyAdmin(self.competition)
        verify(self.proxy_admin, this_admin)
        this_impl = self.proxy_admin.getProxyImplementation(self.competition)
        verify(self.comp_logic, this_impl)

    def test_upgrade(self):
        new_impl = BadCompetition3.deploy({'from': self.admin})
        non_admin = self.participants[0]
        p = self.participants[1]

        # Put some stake in for testing. We will later upgrade to a contract that will
        # always return 1 when `getStake` is called.
        self.token.transfer(p, 500, {'from': self.admin})
        self.token.setStake(self.competition, self.token.balanceOf(p), {'from': p})
        verify(500, self.competition.getStake(p))

        with reverts():  # unauthorized call
            self.proxy_admin.upgrade(self.competition, new_impl, {'from': non_admin})

        self.proxy_admin.upgrade(self.competition, new_impl, {'from': self.admin})
        verify(new_impl, self.proxy_admin.getProxyImplementation(self.competition))
        verify(1, self.competition.getStake(p))

        # now point back to previous implementation
        self.proxy_admin.upgrade(self.competition, self.comp_logic, {'from': self.admin})
        verify(self.comp_logic, self.proxy_admin.getProxyImplementation(self.competition))
        verify(500, self.competition.getStake(p))

    def test_upgrade_and_call(self):
        p = self.participants[1]
        p_stake = self.competition.getStake(p)
        admin_2 = self.participants[2]
        new_impl = BadCompetition3.deploy({'from': self.admin})
        self.competition.grantRole(self.competition.RCI_MAIN_ADMIN(), self.proxy_admin, {'from': self.admin})
        data = self.comp_logic.grantRole.encode_input(self.competition.RCI_CHILD_ADMIN(), admin_2)

        with reverts():  # unauthorized call
            self.proxy_admin.upgradeAndCall(self.competition, new_impl, data, {'from': admin_2})

        verify(False, self.competition.hasRole(self.competition.RCI_CHILD_ADMIN(), admin_2))

        self.proxy_admin.upgradeAndCall(self.competition, new_impl, data, {'from': self.admin})
        verify(new_impl, self.proxy_admin.getProxyImplementation(self.competition))
        verify(1, self.competition.getStake(p))
        verify(True, self.competition.hasRole(self.competition.RCI_CHILD_ADMIN(), admin_2))

        # now point back to previous implementation
        self.proxy_admin.upgrade(self.competition, self.comp_logic, {'from': self.admin})
        verify(self.comp_logic, self.proxy_admin.getProxyImplementation(self.competition))
        verify(p_stake, self.competition.getStake(p))
        # admin_2's role should still be granted
        verify(True, self.competition.hasRole(self.competition.RCI_CHILD_ADMIN(), admin_2))

    def test_change_proxy_admin(self):
        new_admin = ProxyAdmin.deploy({'from': self.admin})
        non_owner = self.participants[0]
        new_impl = BadCompetition3.deploy({'from': self.admin})
        data = self.comp_logic.increaseStake.encode_input(self.participants[-1], 1)

        with reverts(): # unauthorized call
            self.proxy_admin.changeProxyAdmin(self.competition, new_admin, {'from': non_owner})

        verify(self.proxy_admin, self.proxy_admin.getProxyAdmin(self.competition))
        self.proxy_admin.changeProxyAdmin(self.competition, new_admin, {'from': self.admin})
        verify(new_admin, new_admin.getProxyAdmin(self.competition))

        # self.proxy_admin currently no longer admin of self.competition
        with reverts():
            self.proxy_admin.getProxyAdmin(self.competition)
        with reverts():
            self.proxy_admin.upgrade(self.competition, new_impl, {'from': self.admin})
        with reverts():
            self.proxy_admin.upgradeAndCall(self.competition, new_impl, data, {'from': self.admin})

        self.proxy_admin = new_admin

        self.test_upgrade()
        self.test_upgrade_and_call()















