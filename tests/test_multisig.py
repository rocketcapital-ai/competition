from utils_for_testing import *
from brownie import Token, Competition, ChildToken, MultiSig, reverts, accounts

class TestMultiSig:

    def setup(self):
        self.admin = accounts[0]
        self.owners = accounts[1:11]
        self.non_owners = accounts[11:]
        self.required = 6
        self.multi_sig = MultiSig.deploy(self.owners, self.required, {'from': self.admin})
        self.token = Token.deploy("RockCap Token", "RCP", int(Decimal('100000000e18')), {'from': self.admin})
        self.competition = Competition.deploy({'from': self.admin})
        stake_threshold = int(Decimal('10e18'))
        challenge_rewards_threshold = int(Decimal('10e18'))
        self.competition.initialize(stake_threshold, challenge_rewards_threshold, self.token, {'from': self.admin})
        self.token.transfer(self.multi_sig, self.token.balanceOf(self.admin), {'from': self.admin})

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

    def test_add_remove_owner(self):

        verify(set(self.owners), set(self.multi_sig.getOwners()))
        receiver = self.non_owners[-1]
        with reverts():
            self.execute_one_transaction('0x{}'.format('0'*40), self.token.transfer.encode_input(receiver, 1))

        self.execute_one_transaction(self.token, self.token.transfer.encode_input(receiver, 1))

        latest_tx = self.multi_sig.getTransactionCount(False, True)
        with reverts():
            self.multi_sig.executeTransaction(latest_tx, {'from': self.owners[0]})

        verify(1, self.token.balanceOf(receiver))

        # # add
        with reverts():
            self.multi_sig.addOwner(self.non_owners[0], {'from': self.owners[0]})
        new_member = self.non_owners[0]
        self.execute_one_transaction(self.multi_sig, self.multi_sig.addOwner.encode_input(new_member))
        #
        self.owners.append(self.non_owners.pop(0))
        verify(set(self.owners), set(self.multi_sig.getOwners()))

        # remove
        with reverts():
            self.multi_sig.removeOwner(self.owners[0], {'from': self.owners[0]})
        self.execute_one_transaction(self.multi_sig, self.multi_sig.removeOwner.encode_input(new_member))
        self.non_owners.append(self.owners.pop(-1))
        verify(set(self.owners), set(self.multi_sig.getOwners()))

        # replace
        with reverts():
            self.multi_sig.replaceOwner(self.owners[0], self.non_owners[0], {'from': self.owners[0]})

        old_member = self.owners[0]
        verify(new_member, self.non_owners[-1])
        self.execute_one_transaction(self.multi_sig, self.multi_sig.replaceOwner.encode_input(new_member, new_member), execute_should_fail=True)
        self.execute_one_transaction(self.multi_sig, self.multi_sig.replaceOwner.encode_input(old_member, old_member), execute_should_fail=True)
        self.execute_one_transaction(self.multi_sig, self.multi_sig.replaceOwner.encode_input(old_member, new_member))
        self.owners.append(self.non_owners.pop(-1))
        self.non_owners.append(self.owners.pop(0))
        verify(set(self.owners), set(self.multi_sig.getOwners()))

        # change requirement
        new_required = random.randint(1, len(self.owners))
        with reverts():
            self.multi_sig.changeRequirement(new_required, {'from': self.owners[0]})

        self.execute_one_transaction(self.multi_sig, self.multi_sig.changeRequirement.encode_input(0), execute_should_fail=True)
        latest_tx = self.multi_sig.getTransactionCount(True, False)
        with reverts():
            self.multi_sig.executeTransaction(latest_tx, {'from': self.owners[-1]})

        self.execute_one_transaction(self.multi_sig, self.multi_sig.changeRequirement.encode_input(new_required))
        self.required = new_required
        verify(self.required, self.multi_sig.required())

        for o in self.owners[:-self.required]:
            self.execute_one_transaction(self.multi_sig, self.multi_sig.removeOwner.encode_input(o))
            self.owners.remove(o)
        self.execute_one_transaction(self.multi_sig, self.multi_sig.removeOwner.encode_input(self.owners[0]), execute_should_fail=True)
        # latest_tx = self.multi_sig.getTransactionCount(True, True)
        # with reverts():
        #     self.multi_sig.executeTransaction(latest_tx, {'from': self.owners[-1]})



        verify(set(self.owners), set(self.multi_sig.getOwners()))
















        # self.token = Token.deploy("RockCap Token", "RCP", int(Decimal('100000000e18')), {'from': self.admin})
        # self.competition = Competition.deploy({'from': self.admin})
        #
        # stake_threshold = int(Decimal('10e18'))
        # challenge_rewards_threshold = int(Decimal('10e18'))
        #
        # self.competition.initialize(stake_threshold, challenge_rewards_threshold, self.token, {'from': self.admin})
        #
        # self.main_admin_hash = self.competition.RCI_MAIN_ADMIN()
        # self.child_admin_hash = self.competition.RCI_CHILD_ADMIN()
        # self.default_admin_hash = self.competition.DEFAULT_ADMIN_ROLE()



