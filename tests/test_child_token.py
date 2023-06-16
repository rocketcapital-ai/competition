from utils_for_testing import *
from test_token import TestToken
from brownie import Token, Competition, ChildToken, reverts, accounts, Contract, RciFxERC20ChildTunnel
import eth_abi


class TestChildToken(TestToken):

    def after_setup_hook(self):
        self.fx_child, self.fx_root = self.participants[0], self.participants[1]
        self.manager = RciFxERC20ChildTunnel.deploy(self.fx_child, self.token, {'from': self.admin})
        self.manager.setFxRootTunnel(self.fx_root, {'from': self.admin})

        # Set FX manager
        verify(self.zero_address, self.token.fxManager())
        with reverts(): self.token.setFxManager(self.manager, {'from':self.fx_child})
        with reverts(): self.token.setFxManager(self.fx_child, {'from': self.admin})
        self.token.setFxManager(self.manager, {'from': self.admin})
        verify(self.manager, self.token.fxManager())

        # Upgradeable Token
        token_logic = Token.deploy({'from': self.admin})
        data = token_logic.initialize.encode_input("Yiedl", "YIEDL", self.initial_supply, self.admin)
        tup = op.TransparentUpgradeableProxy.deploy(token_logic, self.proxy_admin, data, {'from': self.admin})
        op.TransparentUpgradeableProxy.remove(tup)
        combined_abi = op.TransparentUpgradeableProxy.abi + ChildToken.abi
        self.parent_token = Contract.from_abi("ParentToken", tup.address, combined_abi)

        # Map token
        sync_type = self.manager.MAP_TOKEN()
        root_token, name, symbol, decimals = self.parent_token.address, self.parent_token.name(), self.parent_token.symbol(), self.parent_token.decimals()
        sync_data = eth_abi.encode_abi(["address", "string", "string", "uint8"], [root_token, name, symbol, decimals])
        data = eth_abi.encode_abi(['bytes32', 'bytes'], [sync_type, sync_data])
        self.manager.processMessageFromRoot(0, self.fx_root, data, {'from': self.fx_child})
        verify(self.token, self.manager.rootToChildToken(root_token))

        # Set connected token
        verify(self.zero_address, self.token.connectedToken())
        with reverts(): self.token.setConnectedToken(self.parent_token, {'from': self.fx_child})
        with reverts(): self.token.setConnectedToken(self.fx_child, {'from': self.admin})
        self.token.setConnectedToken(self.parent_token, {'from': self.admin})
        verify(self.parent_token, self.token.connectedToken())

    def test_mint(self):
        amt = int(Decimal("10e6"))
        p = self.participants[0]
        before_bal = self.token.balanceOf(p)
        before_supply = self.token.totalSupply()
        with reverts(): self.token.mint(p, amt, {'from': self.admin})

        # Sync deposit. (Mint)
        sync_type = self.manager.DEPOSIT()
        root_token, name, symbol, decimals = self.parent_token.address, self.parent_token.name(), self.parent_token.symbol(), self.parent_token.decimals()
        depositor, to, amount, deposit_data = p.address, p.address, amt, b''
        sync_data = eth_abi.encode_abi(["address", "address", "address", "uint256", "bytes"],
                                       [root_token, depositor, to, amount, deposit_data])
        data = eth_abi.encode_abi(['bytes32', 'bytes'], [sync_type, sync_data])
        self.manager.processMessageFromRoot(0, self.fx_root, data, {'from': self.fx_child})

        after_bal = self.token.balanceOf(p)
        after_supply = self.token.totalSupply()
        verify(before_bal + amt, after_bal)
        verify(before_supply + amt, after_supply)

    def test_burn(self):
        p = self.participants[0]
        bef_bal = self.token.balanceOf(p)
        bef_supply = self.token.totalSupply()
        amt = bef_bal + 1

        # Cannot burn more than own balance.
        with reverts(): self.token.burn(p, amt, {'from': self.manager})
        amt = bef_bal // 2
        with reverts(): self.token.burn(p, amt, {'from': self.admin})

        # Withdraw (Burn)
        self.manager.withdraw(self.token.address, amt, {"from": p})

        aft_bal = self.token.balanceOf(p)
        aft_supply = self.token.totalSupply()
        verify(bef_bal - amt, aft_bal)
        verify(bef_supply - amt, aft_supply)
