from utils_for_testing import *
from brownie import ChildToken, Competition, reverts, accounts, BadCompetition, BadCompetition2
from brownie import ShareTaxPolicyVanilla, Contract
from brownie import TestTokenUpgraded

class TestToken:
    def setup(self):
        self.admin = accounts[0]
        self.client1 = accounts[1]
        self.client2 = accounts[2]
        self.fee_collector = accounts[3]
        self.tax_collector = accounts[4]
        self.participants = accounts[5:]
        self.initial_supply = 100_000_000 * 1_000_000

        # Upgradeable ChildToken
        token_logic = ChildToken.deploy({'from': self.admin})
        self.proxy_admin = op.ProxyAdmin.deploy({'from': self.admin})
        data = token_logic.initialize.encode_input("Yiedl", "YIEDL", self.initial_supply, self.admin)
        tup = op.TransparentUpgradeableProxy.deploy(token_logic, self.proxy_admin, data, {'from': self.admin})
        op.TransparentUpgradeableProxy.remove(tup)
        combined_abi = op.TransparentUpgradeableProxy.abi + ChildToken.abi
        self.token = Contract.from_abi("ChildToken", tup.address, combined_abi)

        # Upgradeable Competition
        self.competition = Competition.deploy({'from': self.admin})
        self.competition_name = "The new competition"
        self.zero_address = "0x" + (0).to_bytes(20, "big").hex()
        self.max_uint = 2 ** 256 - 1
        self.shareholders = set([self.admin.address])

        # airdrop to participants
        total_airdrop = int(Decimal(0.01) * Decimal(self.token.totalSupply()))
        single_airdrop = total_airdrop // (len(accounts) - 1)
        recipients = [self.client1, self.client2] + self.participants
        for recipient in recipients:
            tx = self.token.transfer(recipient, single_airdrop, {'from': self.admin})
            self.shareholders.add(recipient.address)

        stake_threshold = int(Decimal('10e6'))
        challenge_rewards_threshold = int(Decimal('10e6'))

        self.competition.initialize(stake_threshold, challenge_rewards_threshold, self.token, {'from': self.admin})
        self.token.increaseAllowance(self.competition, challenge_rewards_threshold * 2, {'from': self.admin})
        self.competition.sponsor(challenge_rewards_threshold * 2, {'from': self.admin})
        self.competition.openChallenge(getHash(), getHash(), getTimestamp(), getTimestamp())
        self.shareholders.add(self.competition.address)

        self.cleanup_local_shareholders()

        self.after_setup_hook()

    def after_setup_hook(self):
        pass

    def cleanup_local_shareholders(self):
        zero_bals = []
        for s in self.shareholders:
            if self.token.balanceOf(s) == 0:
                zero_bals.append(s)
        for s in zero_bals:
            self.shareholders.remove(s)

        sh = self.token.getShareHolders(0, self.token.numberOfShareHolders())
        for s in sh:
            self.shareholders.add(s)

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
            self.token.authorizeCompetition(self.competition, self.competition_name, {'from': p})

        verify(False, self.token.getCompetitionActiveByAddress(self.competition))
        self.token.authorizeCompetition(self.competition, self.competition_name, {'from': self.admin})
        verify(True, self.token.getCompetitionActiveByAddress(self.competition))
        verify(0, self.token.getStake(self.competition, p))

        # Should not be able to add the zero address
        zero_address = '0x' + '0' * 40
        with reverts():
            self.token.authorizeCompetition(zero_address, "000", {'from': self.admin})

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

        # Should not revert if trying to set to existing stake
        p2 = self.participants[1]
        p2_stake = self.token.getStake(self.competition, p2)
        self.token.setStake(self.competition, p2_stake, {'from': p2})
        verify(p2_stake, self.token.getStake(self.competition, p2))

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

    def test_share_tax(self):
        verify(False, self.token.transferFeeActive())
        tax_pct1 = int(Decimal("0.22e6"))
        tax_pct2 = int(Decimal("0.07e6"))
        share_tax_policy = ShareTaxPolicyVanilla.deploy(self.fee_collector, self.tax_collector, tax_pct1, tax_pct2, 6, {"from": self.admin})
        share_tax_policy.updateExempt(self.competition, True, {"from": self.admin})
        verify(self.zero_address, self.token.shareTaxPolicy())
        with reverts(): self.token.updateShareTaxPolicyAddress(self.client1, {"from": self.admin})
        with reverts(): self.token.updateShareTaxPolicyAddress(share_tax_policy, {"from": self.client1})
        self.token.updateShareTaxPolicyAddress(share_tax_policy, {"from": self.admin})
        verify(share_tax_policy, self.token.shareTaxPolicy())
        verify(True, self.token.transferFeeActive())

        # Test base erc20 functions.
        with reverts(): self.token.approve(self.zero_address, self.max_uint, {"from": self.client1})
        with reverts(): self.token.transferFrom(self.zero_address, self.client1, 0, {"from": self.client1})
        with reverts(): self.token.transferFrom(self.zero_address, self.client1, 1, {"from": self.client1})
        with reverts(): self.token.transfer(self.zero_address, 1, {"from": self.client1})

        num_shareholders = self.token.numberOfShareHolders()
        shareholders = set(self.token.getShareHolders(0, num_shareholders))
        verify(len(self.shareholders), num_shareholders)
        verify(self.shareholders, shareholders)

        share_bal = self.token.balanceOf(self.client1)
        trf_amt = share_bal // 2
        exp_tax_1 = trf_amt * tax_pct1 // 1000000
        exp_tax_2 = trf_amt * tax_pct2 // 1000000
        bef_client1 = self.token.balanceOf(self.client1)
        bef_client2 = self.token.balanceOf(self.client2)
        bef_fee_collector = self.token.balanceOf(self.fee_collector)
        bef_tax_collector = self.token.balanceOf(self.tax_collector)
        self.token.transfer(self.client2, trf_amt, {"from": self.client1})
        aft_client1 = self.token.balanceOf(self.client1)
        aft_client2 = self.token.balanceOf(self.client2)
        aft_fee_collector = self.token.balanceOf(self.fee_collector)
        aft_tax_collector = self.token.balanceOf(self.tax_collector)
        verify(trf_amt + exp_tax_1 + exp_tax_2, bef_client1 - aft_client1)
        verify(trf_amt, aft_client2 - bef_client2)
        verify(exp_tax_1, aft_fee_collector - bef_fee_collector)
        verify(exp_tax_2, aft_tax_collector - bef_tax_collector)
        num_shareholders = self.token.numberOfShareHolders()
        shareholders = set(self.token.getShareHolders(0, num_shareholders))
        self.shareholders.add(self.fee_collector.address)
        self.shareholders.add(self.tax_collector.address)
        verify(len(self.shareholders), num_shareholders)
        verify(self.shareholders, shareholders)

        # test no fees for vip sender
        share_bal = self.token.balanceOf(self.client1)
        with reverts(): self.token.transfer(self.client2, share_bal, {"from": self.client1})
        share_tax_policy.updateVip(self.client1, True, {"from": self.admin})
        self.token.transfer(self.client2, share_bal, {"from": self.client1})
        self.shareholders.remove(self.client1.address)
        num_shareholders = self.token.numberOfShareHolders()
        shareholders = set(self.token.getShareHolders(0, num_shareholders))
        verify(len(self.shareholders), num_shareholders)
        verify(self.shareholders, shareholders)

        self.token.updateShareTaxPolicyAddress(self.zero_address, {"from": self.admin})
        verify(False, self.token.transferFeeActive())
    def test_upgrade(self):
        new_impl = TestTokenUpgraded.deploy({'from': self.admin})
        old_impl = self.proxy_admin.getProxyImplementation(self.token)
        TestTokenUpgraded.remove(new_impl)
        TransparentUpgradeableProxy = op.TransparentUpgradeableProxy
        combined_abi = TransparentUpgradeableProxy.abi + TestTokenUpgraded.abi
        new_token = Contract.from_abi("doesnotmatter", self.token, combined_abi)
        self.proxy_admin.upgrade(self.token, new_impl, {'from': self.admin})
        verify(new_impl, self.proxy_admin.getProxyImplementation(self.token))

        verify(self.token.name(), new_token.name())
        verify(self.token.symbol(), new_token.symbol())
        verify(self.token.decimals(), new_token.decimals())

        key, val = "uint0", 123456
        verify(0, new_token.getUint(key))
        new_token.setUint(key, val, {'from': self.admin})
        verify(val, new_token.getUint(key))
        new_token.setUint(key, 0, {'from': self.admin})

        self.proxy_admin.upgrade(self.token, old_impl, {'from': self.admin})
        verify(old_impl, self.proxy_admin.getProxyImplementation(self.token))
        verify(self.token.name(), new_token.name())
        verify(self.token.symbol(), new_token.symbol())
        verify(self.token.decimals(), new_token.decimals())
        with reverts():
            new_token.getUint(key)
    def test_bad_competitions(self):

        bad_comp_1 = BadCompetition.deploy(self.token, {'from': self.admin}) # this messes with the final balances after increase/decreaseStake is called.
        bad_comp_2 = BadCompetition2.deploy(self.token, {'from': self.admin}) # this messes with the final stakes after increase/decreaseStake is called.

        self.token.authorizeCompetition(bad_comp_1, "bad comp 1", {'from': self.admin})
        self.token.authorizeCompetition(bad_comp_2, "bad comp 2", {'from': self.admin})

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
