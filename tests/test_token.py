from utils_for_testing import *
from brownie import Token, Competition, ChildToken, ProxyAdmin, TransparentUpgradeableProxy, MultiSig, reverts, accounts, BadCompetition, BadCompetition2

class TestToken:
    def setup(self):
        self.admin = accounts[0]
        self.participants = accounts[1:]
        self.token = Token.deploy("RockCap Token", "RCP", int(Decimal('100000000e18')), {'from': self.admin})
        self.competition = Competition.deploy({'from': self.admin})

        # airdrop to participants
        total_airdrop = int(Decimal(0.01) * Decimal(self.token.totalSupply()))
        single_airdrop = total_airdrop // (len(accounts) - 1)
        for i in range(1, len(accounts)):
            tx = self.token.transfer(accounts[i], single_airdrop, {'from': self.admin})

        stake_threshold = int(Decimal('10e18'))
        challenge_rewards_threshold = int(Decimal('10e18'))

        self.competition.initialize(stake_threshold, challenge_rewards_threshold, self.token, {'from': self.admin})

    def test_stakes(self):

        # Test Competition Authorization
        # Should not be able to call stake-related functions
        p = self.participants[0]
        stake_amount = random.randint(1, self.token.balanceOf(p))
        with reverts():
            self.token.increaseStake(self.competition, stake_amount, {'from': p})
        with reverts():
            self.token.decreaseStake(self.competition, stake_amount, {'from': p})
        with reverts():
            self.token.setStake(self.competition, stake_amount, {'from': p})
        with reverts():
            self.token.getStake(self.competition, p)
        with reverts():
            self.token.authorizeCompetition(self.competition, {'from': p})

        verify(False, self.token.competitionIsAuthorized(self.competition))
        self.token.authorizeCompetition(self.competition, {'from': self.admin})
        verify(True, self.token.competitionIsAuthorized(self.competition))
        verify(0, self.token.getStake(self.competition, p))

        # Should not be able to add the zero address
        zero_address = '0x' + '0' * 40
        with reverts():
            self.token.authorizeCompetition(zero_address, {'from': self.admin})

        # Increase
        [p1] = random.sample(self.participants, 1)

        p1_bal = self.token.balanceOf(p1)
        p1_stake = self.token.getStake(self.competition, p1)
        with reverts():
            self.token.setStake(self.competition, 2 * p1_bal, {'from': p1})
        with reverts():
            self.token.increaseStake(self.competition, 2 * p1_bal, {'from': p1})

        # Increase using `setStake`
        set_stake_amount = random.randint(1, p1_bal)
        self.token.setStake(self.competition, set_stake_amount, {'from': p1})

        p1_new_bal = self.token.balanceOf(p1)
        verify(set_stake_amount-p1_stake, p1_bal - p1_new_bal)

        p1_stake = self.token.getStake(self.competition, p1)
        verify(set_stake_amount, p1_stake)

        # Increase using `increaseStake`
        increase_stake_amount = random.randint(1, p1_new_bal)
        self.token.increaseStake(self.competition, increase_stake_amount, {'from': p1})

        verify(increase_stake_amount, p1_new_bal - self.token.balanceOf(p1))
        verify(increase_stake_amount, self.token.getStake(self.competition, p1) - p1_stake)

        # Decrease
        p1_bal = self.token.balanceOf(p1)
        p1_stake = self.token.getStake(self.competition, p1)

        with reverts():
            self.token.decreaseStake(self.competition, 2 * p1_stake, {'from': p1})

        # Decrease using `setStake`
        set_stake_amount = random.randint(0, p1_stake - 1)
        self.token.setStake(self.competition, set_stake_amount, {'from': p1})

        p1_new_bal = self.token.balanceOf(p1)
        verify(set_stake_amount - p1_stake, p1_bal - p1_new_bal)

        p1_stake = self.token.getStake(self.competition, p1)
        verify(set_stake_amount, p1_stake)

        # Decrease using `decreaseStake`
        decrease_stake_amount = random.randint(1, p1_stake)
        self.token.decreaseStake(self.competition, decrease_stake_amount, {'from': p1})

        verify(decrease_stake_amount, self.token.balanceOf(p1) - p1_new_bal)
        verify(decrease_stake_amount, p1_stake - self.token.getStake(self.competition, p1))

        # Should revert if trying to set to existing stake
        p2 = self.participants[1]
        p2_stake = self.token.getStake(self.competition, p2)
        with reverts():
            self.token.setStake(self.competition, p2_stake, {'from': p2})

    def test_transfer(self):
        [p1, p2] = self.participants[:2]
        p1_bal = self.token.balanceOf(p1)
        p2_bal = self.token.balanceOf(p2)
        transfer_amount = random.randint(1, p1_bal)

        self.token.transfer(p2, transfer_amount, {'from': p1})

        verify(p1_bal - transfer_amount, self.token.balanceOf(p1))
        verify(p2_bal + transfer_amount, self.token.balanceOf(p2))

    #
    def test_allowance_transfer_from(self):
        [p1, p2, p3] = self.participants[:3]
        p1_bal = self.token.balanceOf(p1)
        p2_bal = self.token.balanceOf(p2)
        p3_bal = self.token.balanceOf(p3)
        transfer_amount = random.randint(10, p1_bal)
        allowance_amount = transfer_amount // 2

        # Cannot spend before allowing.
        with reverts():
            self.token.transferFrom(p1, p2, transfer_amount, {'from': p3})

        self.token.increaseAllowance(p3, allowance_amount, {'from': p1})
        verify(allowance_amount, self.token.allowance(p1, p3))

        # Cannot spend more than allowed amount.
        with reverts():
            self.token.transferFrom(p1, p2, transfer_amount, {'from': p3})

        transfer_amount = allowance_amount // 2
        self.token.transferFrom(p1, p2, transfer_amount, {'from': p3})

        verify(p1_bal - transfer_amount, self.token.balanceOf(p1))
        verify(p2_bal + transfer_amount, self.token.balanceOf(p2))
        verify(p3_bal, self.token.balanceOf(p3))
        verify(allowance_amount - transfer_amount, self.token.allowance(p1, p3))

    def test_approve(self):
        [p1, p2, p3] = self.participants[:3]
        p1_bal = self.token.balanceOf(p1)
        p2_bal = self.token.balanceOf(p2)
        p3_bal = self.token.balanceOf(p3)
        transfer_amount = random.randint(10, p1_bal)
        allowance_amount = transfer_amount // 2

        # Cannot spend before allowing.
        with reverts():
            self.token.transferFrom(p1, p2, transfer_amount, {'from': p3})

        self.token.approve(p3, allowance_amount, {'from': p1})
        verify(allowance_amount, self.token.allowance(p1, p3))

        transfer_amount = allowance_amount // 2
        self.token.transferFrom(p1, p2, transfer_amount, {'from': p3})

        verify(p1_bal - transfer_amount, self.token.balanceOf(p1))
        verify(p2_bal + transfer_amount, self.token.balanceOf(p2))
        verify(p3_bal, self.token.balanceOf(p3))
        verify(allowance_amount - transfer_amount, self.token.allowance(p1, p3))

    def test_burn(self):
        p1 = self.participants[0]
        p1_bal = self.token.balanceOf(p1)
        burn_amount = random.randint(1, p1_bal)
        current_supply = self.token.totalSupply()

        # Cannot burn more than own balance.
        with reverts():
            self.token.burn(p1_bal + 1, {'from': p1})

        self.token.burn(burn_amount, {'from': p1})

        verify(p1_bal - burn_amount, self.token.balanceOf(p1))
        verify(current_supply - burn_amount, self.token.totalSupply())

    def test_bad_competitions(self):

        bad_comp_1 = BadCompetition.deploy(self.token, {'from': self.admin}) # this messes with the final balances after increase/decreaseStake is called.
        bad_comp_2 = BadCompetition2.deploy(self.token, {'from': self.admin}) # this messes with the final stakes after increase/decreaseStake is called.

        self.token.authorizeCompetition(bad_comp_1, {'from': self.admin})
        self.token.authorizeCompetition(bad_comp_2, {'from': self.admin})

        self.token.transfer(bad_comp_1, self.token.balanceOf(self.admin) // 2, {'from': self.admin})
        self.token.transfer(bad_comp_2, self.token.balanceOf(self.admin), {'from': self.admin})


        p = self.participants[0]
        amt = random.randint(1, self.token.balanceOf(p))

        with reverts('Token - increaseStake: Sender final balance incorrect.'):
            self.token.increaseStake(bad_comp_1, amt, {'from': p})
        with reverts("Token - decreaseStake: Sender final balance incorrect."):
            self.token.decreaseStake(bad_comp_1, amt, {'from': p})
        with reverts("Token - increaseStake: Sender final stake incorrect."):
            self.token.increaseStake(bad_comp_2, amt, {'from': p})
        with reverts("Token - decreaseStake: Sender final stake incorrect."):
            self.token.decreaseStake(bad_comp_2, amt, {'from': p})