from utils_for_testing import *
from brownie import reverts, accounts, Registry, MultiSig

class TestRegistry:
    def setup(self):
        self.admin = accounts[0]
        self.competitions = accounts[1:6]
        self.tokens = accounts[6:10]
        self.use_multi_admin = False
        self.registry = Registry.deploy({'from': self.admin})
    
    def execute_fn(self, dest, fn, args_list, use_multi_admin, exp_revert):
        if not use_multi_admin:
            if exp_revert:
                with reverts():
                    fn(*args_list)
            else:
                fn(*args_list)
        else:
            args_no_sender = args_list[:-1]
            data = fn.encode_input(*args_no_sender)
            self.execute_one_transaction(dest, data, exp_revert)

    def test_register_new_competition(self):
        verify([], self.registry.getCompetitionList())
        comp_name = getRandomString(10)
        comp_address = self.competitions[0]
        rules_loc = getHash()        
        self.execute_fn(self.registry, self.registry.registerNewCompetition,
                        [comp_name, comp_address, rules_loc, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=False)
        
        verify(comp_address, self.registry.getCompetitionAddress(comp_name))
        verify('0x' + rules_loc, self.registry.getCompetitionRulesLocation(comp_name))
        verify(True, self.registry.getCompetitionActive(comp_name))
        verify([comp_name], self.registry.getCompetitionList())

        # should not be able to register again
        self.execute_fn(self.registry, self.registry.registerNewCompetition,
                        [comp_name, comp_address, rules_loc, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=True)

        # should not be able to register 0 address
        zero_address = '0x' + '0' * 40
        self.execute_fn(self.registry, self.registry.registerNewCompetition,
                        [comp_name, zero_address, rules_loc, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=True)

        # should not be able to register with 0 hash
        zero_hash = '0x' + '0' * 64
        self.execute_fn(self.registry, self.registry.registerNewCompetition,
                        [comp_name, comp_address, zero_hash, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=True)
        
    def test_toggle_competition_active(self):
        comp_name = getRandomString(10)
        comp_address = self.competitions[0]
        rules_loc = getHash()
        self.execute_fn(self.registry, self.registry.registerNewCompetition,
                        [comp_name, comp_address, rules_loc, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=False)
        
        self.execute_fn(self.registry, self.registry.toggleCompetitionActive,
                        [comp_name[0], {'from': self.admin}],
                        self.use_multi_admin, exp_revert=True)
        for i in range(2):
            currently_active = self.registry.getCompetitionActive(comp_name)
            self.execute_fn(self.registry, self.registry.toggleCompetitionActive,
                            [comp_name, {'from': self.admin}],
                            self.use_multi_admin, exp_revert=False)
            verify(not currently_active, self.registry.getCompetitionActive(comp_name))
            
    def test_change_rules_location(self):
        comp_name = getRandomString(10)
        comp_address = self.competitions[0]
        rules_loc = getHash()
        self.execute_fn(self.registry, self.registry.registerNewCompetition,
                        [comp_name, comp_address, rules_loc, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=False)
        new_loc = getHash()
    
        self.execute_fn(self.registry, self.registry.changeCompetitionRulesLocation,
                        [comp_name[0], new_loc, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=True)

        self.execute_fn(self.registry, self.registry.changeCompetitionRulesLocation,
                        [comp_name, bytes([0]*32), {'from': self.admin}],
                        self.use_multi_admin, exp_revert=True)

        self.execute_fn(self.registry, self.registry.changeCompetitionRulesLocation,
                        [comp_name, new_loc, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=False)
        
        verify('0x' + new_loc, self.registry.getCompetitionRulesLocation(comp_name))
        
    def test_change_token_address(self):

        self.execute_fn(self.registry, self.registry.changeTokenAddress,
                        ['0x{}'.format('0'*40), {'from': self.admin}],
                        self.use_multi_admin, exp_revert=True)
        
        token_address = random.choice(self.tokens)
        self.execute_fn(self.registry, self.registry.changeTokenAddress,
                        [token_address, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=False)
        
        verify(token_address, self.registry.getTokenAddress())

    def test_register_new_extension(self):
        verify([], self.registry.getExtensionList())
        ext_name = getRandomString(10)
        ext_address = self.competitions[1]
        rules_loc = getHash()
        self.execute_fn(self.registry, self.registry.registerNewExtension,
                        [ext_name, ext_address, rules_loc, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=False)

        verify(ext_address, self.registry.getExtensionAddress(ext_name))
        verify('0x' + rules_loc, self.registry.getExtensionInfoLocation(ext_name))
        verify(True, self.registry.getExtensionActive(ext_name))
        verify([ext_name], self.registry.getExtensionList())

        # should not be able to register again
        self.execute_fn(self.registry, self.registry.registerNewExtension,
                        [ext_name, ext_address, rules_loc, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=True)

        # should not be able to register 0 address
        zero_address = '0x' + '0' * 40
        self.execute_fn(self.registry, self.registry.registerNewExtension,
                        [ext_name, zero_address, rules_loc, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=True)

        # should not be able to register with 0 hash
        zero_hash = '0x' + '0' * 64
        self.execute_fn(self.registry, self.registry.registerNewExtension,
                        [ext_name, ext_address, zero_hash, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=True)


    def test_toggle_extension_active(self):
        ext_name = getRandomString(10)
        ext_address = self.competitions[1]
        rules_loc = getHash()
        self.execute_fn(self.registry, self.registry.registerNewExtension,
                        [ext_name, ext_address, rules_loc, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=False)

        self.execute_fn(self.registry, self.registry.toggleExtensionActive,
                        [ext_name[0], {'from': self.admin}],
                        self.use_multi_admin, exp_revert=True)
        for i in range(2):
            currently_active = self.registry.getExtensionActive(ext_name)
            self.execute_fn(self.registry, self.registry.toggleExtensionActive,
                            [ext_name, {'from': self.admin}],
                            self.use_multi_admin, exp_revert=False)
            verify(not currently_active, self.registry.getExtensionActive(ext_name))

    def test_change_info_location(self):
        ext_name = getRandomString(10)
        ext_address = self.competitions[1]
        rules_loc = getHash()
        self.execute_fn(self.registry, self.registry.registerNewExtension,
                        [ext_name, ext_address, rules_loc, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=False)
        new_loc = getHash()

        self.execute_fn(self.registry, self.registry.changeExtensionInfoLocation,
                        [ext_name[0], new_loc, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=True)

        self.execute_fn(self.registry, self.registry.changeExtensionInfoLocation,
                        [ext_name, bytes([0] * 32), {'from': self.admin}],
                        self.use_multi_admin, exp_revert=True)

        self.execute_fn(self.registry, self.registry.changeExtensionInfoLocation,
                        [ext_name, new_loc, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=False)

        verify('0x' + new_loc, self.registry.getExtensionInfoLocation(ext_name))

    def test_batch_call(self):
        comp_name = getRandomString(10)
        comp_address = self.competitions[0]
        rules_loc = getHash()
        self.execute_fn(self.registry, self.registry.registerNewCompetition,
                        [comp_name, comp_address, rules_loc, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=False)

        token_address = random.choice(self.tokens)
        self.execute_fn(self.registry, self.registry.changeTokenAddress,
                        [token_address, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=False)

        data = []
        addresses = []

        datum = self.registry.getTokenAddress.encode_input()
        data.append(datum)
        addresses.append(self.registry)

        datum = self.registry.getCompetitionActive.encode_input(comp_name)
        data.append(datum)
        addresses.append(self.registry)

        results = self.registry.batchCall(addresses, data)
        token_address = '0x' + results[0].hex()[-40:]
        is_actually_active = True if int(results[1].hex(), 16) == 1 else False

        verify(token_address, self.registry.getTokenAddress())
        verify(True, is_actually_active)

    def test_unauthorized(self):
        name = getRandomString(10)
        address = self.competitions[-1]
        non_admin = self.tokens[-1]

        with reverts(): self.registry.registerNewCompetition(name, address, getHash(), {'from': non_admin})
        with reverts(): self.registry.toggleCompetitionActive(name, {'from': non_admin})
        with reverts(): self.registry.changeCompetitionRulesLocation(name, getHash(), {'from': non_admin})
        with reverts(): self.registry.changeTokenAddress(address, {'from': non_admin})
        with reverts(): self.registry.registerNewExtension(name, address, getHash(), {'from': non_admin})
        with reverts(): self.registry.toggleExtensionActive(name, {'from': non_admin})
        with reverts(): self.registry.changeExtensionInfoLocation(name, getHash(), {'from': non_admin})


class TestRegistryMulti(TestRegistry):
    def setup(self):
        assert len(accounts) >= 10, 'Please run this test with at least 10 accounts.'
        self.use_multi_admin = True
        self.admin = accounts[0]
        self.owners = accounts[1:5]
        self.non_owners = [accounts[5]]
        self.competitions = accounts[6:8]
        self.tokens = accounts[8:]
        self.required = 3
        self.multi_sig = MultiSig.deploy(self.owners, self.required, {'from': self.admin})
        self.registry = Registry.deploy({'from': self.admin})

        # Hand admin rights to multisig contract
        self.main_admin_hash = self.registry.RCI_MAIN_ADMIN()
        self.child_admin_hash = self.registry.RCI_CHILD_ADMIN()

        self.registry.grantRole(self.main_admin_hash, self.multi_sig, {'from': self.admin})
        self.registry.grantRole(self.child_admin_hash, self.multi_sig, {'from': self.admin})
        self.registry.renounceRole(self.main_admin_hash, self.admin, {'from': self.admin})
        self.registry.renounceRole(self.child_admin_hash, self.admin, {'from': self.admin})

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


        
        
        
            
        
        
        
        