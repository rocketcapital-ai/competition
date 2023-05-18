from utils_for_testing import *
from test_token import TestToken
from brownie import Token, Competition, ChildToken, reverts, accounts
import eth_abi

class TestChildToken(TestToken):

    def after_setup_hook(self):
        self.manager = self.participants[-1]
        # set manager
        verify(self.zero_address, self.token.fxManager())
        with reverts(): self.token.setFxManager(self.manager, {'from': self.manager})
        self.token.setFxManager(self.manager, {'from': self.admin})
        verify(self.manager, self.token.fxManager())

    def test_set_connected_token(self):
        token_addr = self.participants[-1]
        verify(self.zero_address, self.token.connectedToken())
        with reverts():
            self.token.setConnectedToken(token_addr, {'from': self.manager})
        self.token.setConnectedToken(token_addr, {'from': self.admin})
        verify(token_addr, self.token.connectedToken())

    def test_burn(self):
        p = self.participants[0]
        bef_bal = self.token.balanceOf(p)
        bef_supply = self.token.totalSupply()
        amt = bef_bal + 1

        # Cannot burn more than own balance.
        with reverts(): self.token.burn(p, amt, {'from': self.manager})
        amt = bef_bal // 2
        with reverts(): self.token.burn(p, amt, {'from': self.admin})
        self.token.burn(p, amt, {'from': self.manager})
        aft_bal = self.token.balanceOf(p)
        aft_supply = self.token.totalSupply()
        verify(bef_bal - amt, aft_bal)
        verify(bef_supply - amt, aft_supply)

    def test_mint(self):
        amt = int(Decimal("10e6"))
        p = self.participants[0]
        before_bal = self.token.balanceOf(p)
        before_supply = self.token.totalSupply()
        with reverts(): self.token.mint(p, amt, {'from': self.admin})
        self.token.mint(p, amt, {'from': self.manager})
        after_bal = self.token.balanceOf(p)
        after_supply = self.token.totalSupply()
        verify(before_bal + amt, after_bal)
        verify(before_supply + amt, after_supply)
