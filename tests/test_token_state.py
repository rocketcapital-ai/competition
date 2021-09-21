from brownie import Token, accounts, reverts
from brownie.test import strategy
from brownie.exceptions import VirtualMachineError
from collections import defaultdict
from state_parent import StateParent
from decimal import Decimal

class TokenStateMachine(StateParent):
    st_amount = strategy("uint256")
    st_owner = strategy("address")
    st_spender = strategy("address")
    st_sender = strategy("address")
    st_receiver = strategy("address")
    st_permitter = strategy("address")
    st_permittee = strategy("address")
    st_supply = strategy("uint256", min_value = "1000000 ether")

    def __init__(self, accounts, contract, st_supply):
        StateParent.__init__(self)
        self.accounts = accounts
        self.token = contract.deploy("Test Token", "TT", st_supply, {'from': accounts[0]})
        self.totalSupply = st_supply
        self.uint_max = 115792089237316195423570985008687907853269984665640564039457584007913129639935

    def setup(self):
        self.allowances = defaultdict(lambda: 0)
        self.balances = defaultdict(lambda: 0)
        self.balances[self.accounts[0]] = self.totalSupply
        self.value_failure = False

    def teardown(self):
        if not self.value_failure:
            self.verifyTotalSupply()
            self.verifyAllBalances()
            self.verifyAllAllowances()

    def rule_transfer(self, st_sender, st_receiver, st_amount):
        if st_amount <= self.balances[st_sender]:
            tx = self.token.transfer(
                st_receiver, st_amount, {"from": st_sender}
            )
            self.verifyTransfer(st_sender, st_receiver, st_amount)
            self.verifyEvent(
                tx,
                "Transfer",
                {"from": st_sender, "to": st_receiver, "value": st_amount},
            )
            self.verifyReturnValue(tx, True)
        else:
            with reverts():
                self.token.transfer(
                    st_receiver, st_amount, {"from": st_sender}
                )
            self.verifyTransfer(st_sender, st_receiver, 0)

    def rule_transferFrom(self, st_spender, st_owner, st_receiver, st_amount):
        if st_amount == 0 or (
            (st_owner, st_spender) in self.allowances.keys()
            and self.balances[st_owner] >= st_amount
            and (self.allowances[(st_owner, st_spender)] >= st_amount)
        ):
            tx = self.token.transferFrom(
                st_owner, st_receiver, st_amount, {"from": st_spender}
            )
            self.verifyTransfer(st_owner, st_receiver, st_amount)
            if st_amount != 0:
                self.verifyAllowance(st_owner, st_spender, -st_amount)
            self.verifyEvent(
                tx,
                "Transfer",
                {"from": st_owner, "to": st_receiver, "value": st_amount},
            )
            self.verifyReturnValue(tx, True)
        else:
            with reverts():
                self.token.transferFrom(
                    st_owner, st_receiver, st_amount, {"from": st_spender}
                )
            self.verifyTransfer(st_owner, st_receiver, 0)

    def rule_approve(self, st_owner, st_spender, st_amount):
        tx = self.token.approve(
            st_spender, st_amount, {"from": st_owner}
        )
        self.verifyApproval(st_owner, st_spender, st_amount)
        self.verifyEvent(
            tx,
            "Approval",
            {"owner": st_owner, "spender": st_spender, "value": st_amount},
        )
        self.verifyReturnValue(tx, True)

    def rule_increaseAllowance(self, st_owner, st_spender, st_amount):
        current_allowance = self.token.allowance(st_owner, st_spender)
        if ((current_allowance + st_amount) <= self.uint_max):
            tx = self.token.increaseAllowance(
                st_spender, st_amount, {"from": st_owner}
            )
            self.verifyAllowance(st_owner, st_spender, delta=st_amount)
            new_allowance = self.allowances[(st_owner,st_spender)]
            self.verifyEvent(
                tx,
                "Approval",
                {"owner": st_owner, "spender": st_spender, "value": new_allowance},
            )
        else:
            with reverts():
                self.token.increaseAllowance(
                    st_spender, st_amount, {"from": st_owner}
                )
            self.verifyAllowance(st_owner, st_spender, delta=0)

    def rule_decreaseAllowance(self, st_owner, st_spender, st_amount):
        if self.token.allowance(st_owner,st_spender) >= st_amount:
            tx = self.token.decreaseAllowance(
                st_spender, st_amount, {"from": st_owner}
            )
            self.verifyAllowance(st_owner, st_spender, delta=-st_amount)
            new_allowance = self.allowances[(st_owner,st_spender)]
            self.verifyEvent(
                tx,
                "Approval",
                {"owner": st_owner, "spender": st_spender, "value": new_allowance},
            )
        else:
            with reverts():
                self.token.decreaseAllowance(
                    st_spender, st_amount, {"from": st_owner}
                )
            self.verifyAllowance(st_owner, st_spender, delta=0)

    def rule_transferAll(self, st_sender, st_receiver):
        self.rule_transfer(st_sender, st_receiver, self.balances[st_sender])

    def rule_approveAndTransferAll(self, st_owner, st_spender, st_receiver):
        amount = self.balances[st_owner]
        self.rule_approve(st_owner, st_spender, amount)
        self.rule_transferFrom(st_spender, st_owner, st_receiver, amount)

    def rule_burn(self, st_sender, st_amount):
        if st_amount >= 0 and self.balances[st_sender] >= st_amount:
            tx = self.token.burn(st_amount, {"from": st_sender})
            self.totalSupply -= st_amount
            self.balances[st_sender] -= st_amount
            self.verifyBalance(st_sender)
            self.verifyTotalSupply()
            self.verifyEvent(
                tx, "Transfer",
                {"from": st_sender, "to": '0x'+('0'*40), "value": st_amount},
            )
        else:
            with reverts():
                self.token.burn(st_amount, {"from": st_sender})

    def rule_burn_all(self, st_sender):
        self.rule_burn(st_sender, self.balances[st_sender])

    def invariant_total_supply(self):
        assert sum(self.balances.values()) == self.token.totalSupply()

#
# ### VERIFICATION METHODS ###
    def verifyTotalSupply(self):
        self.verifyValue(
            "totalSupply()", self.totalSupply, self.token.totalSupply()
        )

    def verifyAllBalances(self):
        for account in self.balances:
            self.verifyBalance(account)

    def verifyAllAllowances(self):
        for (owner, spender) in self.allowances:
            self.verifyApproval(owner, spender)

    def verifyBalance(self, addr):
        self.verifyValue(
            "balanceOf({})".format(addr),
            self.balances[addr],
            self.token.balanceOf(addr),
        )

    def verifyTransfer(self, src, dst, amount):
        self.balances[src] -= amount
        self.balances[dst] += amount
        self.verifyBalance(src)
        self.verifyBalance(dst)

    def verifyApproval(self, owner, spender, delta=None):
        if delta != None:
            if delta >= 0:
                self.allowances[(owner, spender)] = delta
        self.verifyValue(
            "allowance({},{})".format(owner, spender),
            self.allowances[(owner, spender)],
            self.token.allowance(owner, spender),
        )

    def verifyAllowance(self, owner, spender, delta=None):
        if delta != None:
            self.allowances[(owner, spender)] += delta
        self.verifyValue(
            "allowance({},{})".format(owner, spender),
            self.allowances[(owner, spender)],
            self.token.allowance(owner, spender),
        )

def test_stateful(accounts, Token, state_machine):
    state_machine(TokenStateMachine, accounts, Token, int(Decimal('100000000e18')))