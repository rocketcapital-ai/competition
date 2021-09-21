from utils_for_testing import *
from brownie import Token, Competition, reverts, accounts

class TestAccessControl:

    def setup(self):
        self.admin = accounts[0]
        self.participants = accounts[1:]
        self.token = Token.deploy("RockCap Token", "RCP", int(Decimal('100000000e18')), {'from': self.admin})
        self.competition = Competition.deploy({'from': self.admin})

        stake_threshold = int(Decimal('10e18'))
        challenge_rewards_threshold = int(Decimal('10e18'))

        self.competition.initialize(stake_threshold, challenge_rewards_threshold, self.token, {'from': self.admin})

        self.main_admin_hash = self.competition.RCI_MAIN_ADMIN()
        self.child_admin_hash = self.competition.RCI_CHILD_ADMIN()
        self.default_admin_hash = self.competition.DEFAULT_ADMIN_ROLE()

    def test_grant_revoke(self):
        verify(False, self.competition.hasRole(self.default_admin_hash, self.admin))

        child1 = self.participants[0]
        child2 = self.participants[1]

        with reverts():
            self.competition.grantRole(self.child_admin_hash, child2, {'from': child1})

        verify(False, self.competition.hasRole(self.child_admin_hash, child1))
        verify(False, self.competition.hasRole(self.child_admin_hash, child2))

        self.competition.grantRole(self.child_admin_hash, child1, {'from': self.admin})
        self.competition.grantRole(self.child_admin_hash, child2, {'from': self.admin})

        verify(True, self.competition.hasRole(self.child_admin_hash, child1))
        verify(True, self.competition.hasRole(self.child_admin_hash, child2))

        with reverts():
            self.competition.revokeRole(self.child_admin_hash, child2, {'from': child1})

        self.competition.revokeRole(self.child_admin_hash, child1, {'from': self.admin})
        self.competition.revokeRole(self.child_admin_hash, child2, {'from': self.admin})

        verify(False, self.competition.hasRole(self.child_admin_hash, child1))
        verify(False, self.competition.hasRole(self.child_admin_hash, child2))

        # Grant main admin role to child1
        self.competition.grantRole(self.main_admin_hash, child1, {'from': self.admin})
        verify(True, self.competition.hasRole(self.main_admin_hash, child1))
        verify(False, self.competition.hasRole(self.child_admin_hash, child1))
        
        self.competition.grantRole(self.child_admin_hash, child2, {'from': child1})
        verify(True, self.competition.hasRole(self.child_admin_hash, child2))
        
        self.competition.revokeRole(self.child_admin_hash, child2, {'from': child1})
        verify(False, self.competition.hasRole(self.child_admin_hash, child2))

    def test_renounce(self):
        verify(self.main_admin_hash, self.competition.getRoleAdmin(self.main_admin_hash))
        verify(self.main_admin_hash, self.competition.getRoleAdmin(self.child_admin_hash))
        verify(True, self.competition.hasRole(self.main_admin_hash, self.admin))

        with reverts():
            self.competition.renounceRole(self.main_admin_hash, self.admin, {'from': self.participants[0]})
        self.competition.renounceRole(self.main_admin_hash, self.admin, {'from': self.admin})
        verify(False, self.competition.hasRole(self.main_admin_hash, self.admin))

        with reverts():
            self.competition.grantRole(self.main_admin_hash, self.participants[0], {'from': self.admin})
        with reverts():
            self.competition.grantRole(self.child_admin_hash, self.participants[0], {'from': self.admin})




        
        
        
        
        
        
        
        
        
        
    
















