from utils_for_testing import *
from brownie import ChildToken, Competition, reverts, accounts, chain, Contract


class TestCompetition:
    def setup(self):
        print('Setting up.')
        random.seed(7788)
        self.num_rounds = 3
        self.use_multi_admin = False
        self.admin = accounts[0]
        self.participants = accounts[1:]
        self.initial_supply = 100_000_000 * 1_000_000

        # Upgradeable ChildToken
        token_logic = ChildToken.deploy({'from': self.admin})
        proxy_admin = op.ProxyAdmin.deploy({'from': self.admin})
        data = token_logic.initialize.encode_input("Yiedl", "YIEDL", self.initial_supply, self.admin)
        tup = op.TransparentUpgradeableProxy.deploy(token_logic, proxy_admin, data, {'from': self.admin})
        op.TransparentUpgradeableProxy.remove(tup)
        combined_abi = op.TransparentUpgradeableProxy.abi + ChildToken.abi
        self.token = Contract.from_abi("ChildToken", tup.address, combined_abi)

        self.competition = Competition.deploy({'from': self.admin})
        self.competition_name = "The new competition"
        self.stake_amt_history = {}
        self.staker_set_history = {}
        self.staker_set = {}
        self.challenge_opened_block_numbers = {}
        self.submission_closed_block_numbers = {}
        self.fork = False
        self.challenge_list = list(range(1, self.num_rounds+1))
        self.vault = "0x" + (1234567).to_bytes(20, "big").hex()
        self.vault2 = "0x" + (1234566).to_bytes(20, "big").hex()

        self.old_dataset_hashes = []
        self.old_public_key_hashes = []

        # airdrop to participants
        total_airdrop = int(Decimal(0.01) * Decimal(self.token.totalSupply()))
        single_airdrop = total_airdrop // (len(accounts) - 1)
        for i in range(len(self.participants)):
            self.execute_fn(self.token, self.token.transfer,
                            [self.participants[i], single_airdrop, {'from': self.admin}],
                            self.use_multi_admin, exp_revert=False)

        stake_threshold = int(Decimal('1e6'))
        challenge_rewards_threshold = int(Decimal('0e6'))

        # Cannot initialize with self.token address set to 0.
        self.execute_fn(self.competition, self.competition.initialize,
                        [stake_threshold, challenge_rewards_threshold, '0x{}'.format('0'*40), {'from': self.admin}],
                        self.use_multi_admin, exp_revert=True)

        self.execute_fn(self.competition, self.competition.initialize,
                        [stake_threshold, challenge_rewards_threshold, self.token, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=False)

        self.execute_fn(self.token, self.token.authorizeCompetition,
                        [self.competition, self.competition_name, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=False)

        self.execute_fn(self.competition, self.competition.updateVault,
                        [self.vault, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=False)

        verify(stake_threshold, self.competition.getStakeThreshold())
        verify(challenge_rewards_threshold, self.competition.getRewardsThreshold())
        verify(0, self.competition.getLatestChallengeNumber())
        verify(4, self.competition.getPhase(0))
        verify(self.token, self.competition.getTokenAddress())
        verify(True, self.token.getCompetitionActiveByAddress(self.competition))

        verify(0, int(self.competition.getBurnRecipient(), 16))
        verify(self.vault, self.competition.getVault())

    def get_historical_stakers_and_amounts(self, challenge_number):
        counter = self.competition.getHistoricalStakersCounter(challenge_number)
        chunk = 2500
        stakers_list = []
        amounts_list = []
        for i in range(0, counter + 1, chunk):
            if i + chunk >= counter:
                stakers_chunk = self.competition.getHistoricalStakersPartial(challenge_number, i, counter)
            else:
                stakers_chunk = self.competition.getHistoricalStakersPartial(challenge_number, i, i + chunk)
            amounts_chunk = self.competition.getHistoricalStakeAmounts(challenge_number, stakers_chunk)
            stakers_list.extend(stakers_chunk)
            amounts_list.extend(amounts_chunk)
        assert counter == len(stakers_list)
        assert counter == len(amounts_list)
        assert sum(amounts_list) == self.competition.getHistoricalTotalStaked(challenge_number)
        return stakers_list, amounts_list

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

    def staking_restricted_check(self, sender):
        self.execute_fn(self.competition, self.competition.increaseStake, [sender, 1, {'from': sender}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.decreaseStake, [sender, 1, {'from': sender}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.token, self.token.increaseStake, [self.competition, 1, {'from': sender}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.token, self.token.decreaseStake, [self.competition, 1, {'from': sender}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.token, self.token.setStake, [self.competition, 1, {'from': sender}], use_multi_admin=self.use_multi_admin, exp_revert=True)

    def staking_submissions_restricted_check(self, sender):
        self.staking_restricted_check(sender)
        staked = self.competition.getStake(sender)
        self.execute_fn(
            self.token, self.token.stakeAndSubmit,
            [self.competition, staked, getHash(),  {'from': sender}],
            use_multi_admin=False, exp_revert=True)
        challenge_number = self.competition.getLatestChallengeNumber()
        staked = self.competition.getStake(sender)
        self.execute_fn(
            self.token, self.token.stakeAndSubmit,
            [self.competition, staked, getHash(),  {'from': sender}],
            use_multi_admin=False, exp_revert=True)

    def unauthorized_calls_check(self, non_admin, admin):
        main_admin_hash = self.competition.RCI_MAIN_ADMIN().hex()
        child_admin_hash = self.competition.RCI_CHILD_ADMIN().hex()
        challenge_number = self.competition.getLatestChallengeNumber()
        with reverts(): self.competition.revokeRole(child_admin_hash, admin, {'from': non_admin})
        with reverts(): self.competition.grantRole(child_admin_hash, non_admin, {'from': non_admin})
        with reverts(): self.competition.renounceRole(child_admin_hash, admin, {'from': non_admin})
        with reverts(): self.competition.revokeRole(main_admin_hash, admin, {'from': non_admin})
        with reverts(): self.competition.grantRole(main_admin_hash, non_admin, {'from': non_admin})
        with reverts(): self.competition.renounceRole(main_admin_hash, admin, {'from': non_admin})
        with reverts(): self.competition.updateMessage(str(getHash()), {'from': non_admin})
        with reverts(): self.competition.updateDeadlines(challenge_number, 0, 123456, {'from': non_admin})
        with reverts(): self.competition.updateRewardsThreshold(1, {'from': non_admin})
        with reverts(): self.competition.updateStakeThreshold(1, {'from': non_admin})
        with reverts(): self.competition.openChallenge(getHash(), getHash(), getTimestamp(), getTimestamp(), {'from': non_admin})
        with reverts(): self.competition.updateDataset(getHash(), {'from': non_admin})
        with reverts(): self.competition.updateKey(getHash(), {'from': non_admin})
        with reverts(): self.competition.updatePrivateKey(challenge_number, getHash(), {'from': non_admin})
        with reverts(): self.competition.closeSubmission({'from': non_admin})
        with reverts(): self.competition.submitResults(getHash(), {'from': non_admin})
        with reverts(): self.competition.updateResults(self.competition.getResultsHash(challenge_number), getHash(), {'from': non_admin})
        with reverts(): self.competition.payRewards([non_admin], [1], [1], [1], {'from': non_admin})
        with reverts(): self.competition.updateChallengeAndTournamentScores(challenge_number, [non_admin], [1], [1], {'from': non_admin})
        with reverts(): self.competition.updateInformationBatch(challenge_number, [non_admin], 1, [1], {'from': non_admin})
        with reverts(): self.competition.advanceToPhase(self.competition.getPhase(challenge_number) + 1, {'from': non_admin})
        with reverts(): self.competition.moveRemainderToPool({'from': non_admin})
        with reverts(): self.competition.recordStakes(0, 1, {'from': non_admin})
        with reverts(): self.competition.burn([non_admin], [1], {'from': non_admin})
        with reverts(): self.competition.moveBurnedToPool(1, {'from': non_admin})
        with reverts(): self.competition.moveBurnedOut(1, {'from': non_admin})
        with reverts(): self.competition.updateBurnRecipient(non_admin, {'from': non_admin})
        with reverts(): self.competition.updateBurnRecipient(non_admin, {'from': non_admin})
        with reverts(): self.competition.updateVault(self.vault, {'from': non_admin})

    def test_full_run(self):
        self.execute_fn(self.competition, self.competition.initialize, [int(Decimal('10e6')), int(Decimal('10e6')), self.token, {'from': self.admin}], self.use_multi_admin, exp_revert=True)

        participants = self.participants
        cn = self.competition.getLatestChallengeNumber()
        current_phase = self.competition.getPhase(cn)

        # Test Roles section
        admin_2 = participants[-1]
        child_admin_hash = self.competition.RCI_CHILD_ADMIN()
        verify(False, self.competition.hasRole(child_admin_hash, admin_2))
        self.execute_fn(self.competition, self.competition.grantRole,
                        [child_admin_hash, admin_2, {'from': self.admin}],
                        use_multi_admin=self.use_multi_admin, exp_revert=False)
        verify(True, self.competition.hasRole(child_admin_hash, admin_2))
        self.execute_fn(self.competition, self.competition.grantRole,
                        [child_admin_hash, admin_2, {'from': self.admin}],
                        use_multi_admin=self.use_multi_admin, exp_revert=False)  # Should simply have no effect
        verify(True, self.competition.hasRole(child_admin_hash, admin_2))

        self.execute_fn(self.competition, self.competition.revokeRole,
                        [child_admin_hash, admin_2, {'from': self.admin}],
                        use_multi_admin=self.use_multi_admin, exp_revert=False)
        verify(False, self.competition.hasRole(child_admin_hash, admin_2))
        self.execute_fn(self.competition, self.competition.revokeRole,
                        [child_admin_hash, admin_2, {'from': self.admin}],
                        use_multi_admin=self.use_multi_admin, exp_revert=False)  # Should simply have no effect
        verify(False, self.competition.hasRole(child_admin_hash, admin_2))

        self.execute_fn(self.competition, self.competition.grantRole,
                        [child_admin_hash, admin_2, {'from': self.admin}],
                        use_multi_admin=self.use_multi_admin, exp_revert=False)
        verify(True, self.competition.hasRole(child_admin_hash, admin_2))
        self.execute_fn(self.competition, self.competition.renounceRole, [child_admin_hash, admin_2, {'from': self.admin}],
                        use_multi_admin=self.use_multi_admin, exp_revert=True)
        self.competition.renounceRole(child_admin_hash, admin_2, {'from': admin_2})
        verify(False, self.competition.hasRole(child_admin_hash, admin_2))

        if current_phase == 1:
            self.execute_fn(self.competition, self.competition.closeSubmission, [{'from': self.admin}],
                            self.use_multi_admin, exp_revert=False)
            current_phase = self.competition.getPhase(cn)
        if current_phase == 2:
            self.execute_fn(self.competition, self.competition.advanceToPhase, [3, {'from': self.admin}],
                            self.use_multi_admin, exp_revert=False)
            current_phase = self.competition.getPhase(cn)
        if current_phase == 3:
            self.execute_fn(self.competition, self.competition.advanceToPhase, [4, {'from': self.admin}],
                            self.use_multi_admin, exp_revert=False)

        existing_stake = self.competition.getCurrentTotalStaked()
        challenge_history = []

        for challenge_round in self.challenge_list:
            print('\n##### Processing challenge {} of {}. #####'.format(challenge_round, self.challenge_list[-1]))

            # Sponsor
            current_pool = self.competition.getCompetitionPool()
            rewards_threshold = self.competition.getRewardsThreshold()
            if current_pool < rewards_threshold:
                self.execute_fn(self.competition, self.competition.openChallenge, [getHash(), getHash(), getTimestamp(), getTimestamp(), {'from': self.admin}], self.use_multi_admin, exp_revert=True)

            sponsor_amount = int(rewards_threshold * 2)
            self.execute_fn(self.token, self.token.increaseAllowance, [self.competition, sponsor_amount, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            self.execute_fn(self.competition, self.competition.sponsor, [sponsor_amount, {'from': self.admin}], self.use_multi_admin, exp_revert=False)

            self.unauthorized_calls_check(non_admin=participants[-1], admin=self.admin)

            staked = self.competition.getStake(participants[0])
            self.execute_fn(
                self.token, self.token.stakeAndSubmit,
                [self.competition, staked, getHash(), {'from': participants[0]}],
                use_multi_admin=False, exp_revert=True)

            challenge_number = self.competition.getLatestChallengeNumber()
            verify(self.competition.getPhase(challenge_number), 4)

            #############################
            ########## PHASE 1 ##########
            #############################
            print('--- Phase 1 ---')
            dataset_hash = getHash()
            key_hash = getHash()
            self.execute_fn(self.competition, self.competition.openChallenge, [dataset_hash, key_hash, getTimestamp(), getTimestamp(), {'from': self.admin}], self.use_multi_admin, exp_revert=False)

            challenge_number = self.competition.getLatestChallengeNumber()
            challenge_history.append(challenge_number)
            verify(1, self.competition.getPhase(challenge_number))
            verify(dataset_hash, self.competition.getDatasetHash(challenge_number).hex())
            verify(key_hash, self.competition.getKeyHash(challenge_number).hex())
            verify(len(chain) - 1, self.competition.challengeOpenedBlockNumbers(challenge_number))
            self.challenge_opened_block_numbers[challenge_number] = self.competition.challengeOpenedBlockNumbers(challenge_number)

            # Update dataset and public key hashes
            new_dataset_hash = getHash()
            new_key_hash = getHash()

            self.execute_fn(self.competition, self.competition.updateDataset, [dataset_hash, {'from': self.admin}], self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.updateDataset, [new_dataset_hash, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            verify(new_dataset_hash, self.competition.getDatasetHash(challenge_number).hex())
            self.old_dataset_hashes.append(new_dataset_hash)
            for odh in self.old_dataset_hashes:
                self.execute_fn(self.competition, self.competition.updateDataset, [odh, {'from': self.admin}], self.use_multi_admin, exp_revert=True)

            self.execute_fn(self.competition, self.competition.updateKey, [key_hash, {'from': self.admin}], self.use_multi_admin, exp_revert=True)

            self.execute_fn(self.competition, self.competition.updateKey, [new_key_hash, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            verify(new_key_hash, self.competition.getKeyHash(challenge_number).hex())
            self.old_public_key_hashes.append(new_key_hash)
            for opkh in self.old_public_key_hashes:
                self.execute_fn(self.competition, self.competition.updateKey, [opkh, {'from': self.admin}], self.use_multi_admin, exp_revert=True)

            # Update deadlines
            new_deadlines = [getTimestamp(), getTimestamp(), getTimestamp(), getTimestamp()]
            new_ddline_indices = random.sample(list(range(50)), 4)

            for i in range(4):
                self.execute_fn(self.competition, self.competition.updateDeadlines, [challenge_number, new_ddline_indices[i], new_deadlines[i], {'from': self.admin}], self.use_multi_admin, exp_revert=False)

            for i in range(4):
                verify(new_deadlines[i], self.competition.getDeadlines(challenge_number, new_ddline_indices[i]))

            p = participants[-1]
            p2 = participants[-2]
            p3 = participants[-3]

            assert p != p2 and p != p3, 'Not enough accounts! Please re-run the test with more accounts initialized.'

            self.execute_fn(self.competition, self.competition.updateVault, [self.vault2, {'from': self.admin}],
                            use_multi_admin=self.use_multi_admin, exp_revert=False)
            verify(self.vault2, self.competition.getVault())
            self.execute_fn(self.competition, self.competition.updateVault, [self.vault, {'from': self.admin}],
                            use_multi_admin=self.use_multi_admin, exp_revert=False)

            self.staking_submissions_test(challenge_number, p)

            stakers = getRandomSelection(participants, min_num=len(participants) * 7 // 10)
            stake_threshold = self.competition.getStakeThreshold()

            if self.competition.getStake(p) == 0:
                self.execute_fn(self.token, self.token.decreaseStake, [self.competition, 1, {'from': p}], use_multi_admin=False, exp_revert=True)
                self.execute_fn(self.competition, self.competition.increaseStake, [p, stake_threshold, {'from': p}], use_multi_admin=False, exp_revert=True)
                self.execute_fn(self.token, self.token.increaseStake, [self.competition, stake_threshold//2, {'from': p}], use_multi_admin=False, exp_revert=True)
                self.execute_fn(self.token, self.token.increaseStake, [self.competition, stake_threshold, {'from': p}], use_multi_admin=False, exp_revert=False)

            # Increase Stake
            print('Increasing stakes.')
            for i in tqdm(range(len(stakers))):
                p = stakers[i]
                p_bal = self.token.balanceOf(p)
                if p_bal > 1:
                    stake_amount = random.randint(1, p_bal)

                    if random.choice([True, False]):
                        self.execute_fn(self.token, self.token.setStake, [self.competition, stake_amount, {'from': p}], use_multi_admin=False, exp_revert=stake_amount < stake_threshold)
                        if stake_amount >= stake_threshold:
                            assert self.competition.getStake(p) == stake_amount == self.token.getStake(
                                self.competition, p)
                    else:
                        current_stake = self.competition.getStake(p)
                        self.execute_fn(self.competition, self.competition.increaseStake, [p, stake_amount, {'from': p}], use_multi_admin=False, exp_revert=True)
                        self.execute_fn(self.token, self.token.increaseStake, [self.competition, stake_amount, {'from': p}], use_multi_admin=False, exp_revert=(current_stake + stake_amount) < stake_threshold)
                        if (current_stake + stake_amount) >= stake_threshold:
                            assert self.competition.getStake(p) == (current_stake + stake_amount) == self.token.getStake(
                                self.competition, p)

            # Decrease Stake
            random_stakers = getRandomSelection(stakers)
            print('Decreasing stakes.')
            for i in tqdm(range(len(random_stakers))):
                p = random_stakers[i]
                staked = self.competition.getStake(p)
                decrease_amt = random.randint(0, staked)

                if random.choice([True, False]):
                    self.execute_fn(self.token, self.token.setStake, [self.competition, decrease_amt, {'from': p}],
                                    use_multi_admin=False, exp_revert=decrease_amt < stake_threshold)
                    if decrease_amt >= stake_threshold:
                        assert self.competition.getStake(p) == decrease_amt == self.token.getStake(
                            self.competition, p)
                else:
                    # print("===", staked, decrease_amt, stake_threshold)
                    self.execute_fn(self.competition, self.competition.decreaseStake, [p, stake_amount, {'from': p}],
                                    use_multi_admin=False, exp_revert=True)
                    self.execute_fn(self.token, self.token.decreaseStake, [self.competition, decrease_amt, {'from': p}],
                                    use_multi_admin=False,
                                    exp_revert=not(((staked-decrease_amt) >= stake_threshold) or (staked == decrease_amt))
                                    )
                    if (staked-decrease_amt) >= stake_threshold :
                        assert self.competition.getStake(p) == (
                                staked - decrease_amt) == self.token.getStake(self.competition, p)

            # Send Submission
            submitters = getRandomSelection(stakers, min_num=len(stakers) * 9 // 10)
            actual_submitted = set()
            print('Sending submissions.')
            for p in tqdm(submitters):
                staked = self.competition.getStake(p)
                self.competition.getDatasetHash(challenge_number)
                if staked >= stake_threshold:
                    new_submission = getHash()

                    self.execute_fn(
                        self.token, self.token.stakeAndSubmit,
                        [self.competition, staked, new_submission, {'from': p}],
                        use_multi_admin=False, exp_revert=False)
                    actual_submitted.add(p)

                    self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold - 1, {'from': p}], use_multi_admin=False, exp_revert=True)
                    self.execute_fn(self.token, self.token.decreaseStake, [self.competition, self.token.getStake(self.competition, p) - stake_threshold + 1, {'from': p}], use_multi_admin=False, exp_revert=True)
                else:
                    self.execute_fn(
                        self.token, self.token.stakeAndSubmit,
                        [self.competition, staked, getHash(), {'from': p}], use_multi_admin=False, exp_revert=True)

            # Update Submission
            print('Updating submissions.')
            for p in tqdm(participants):
                submission = self.competition.getSubmission(challenge_number, p)
                staked = self.competition.getStake(p)
                if int(submission.hex(), 16) != 0:
                    if random.choice([True, False]):
                        self.execute_fn(self.token, self.token.stakeAndSubmit, [self.competition, staked, getHash(), {'from': p}], use_multi_admin=False, exp_revert=False)
                        self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold - 1, {'from': p}], use_multi_admin=False, exp_revert=True)
                        self.execute_fn(self.token, self.token.decreaseStake, [self.competition, self.token.getStake(self.competition, p) - stake_threshold + 1, {'from': p}], use_multi_admin=False, exp_revert=True)
                    else:
                        # Withdraw
                        self.execute_fn(self.token, self.token.stakeAndSubmit, [self.competition, 0, bytes([0] * 32), {'from': p}], use_multi_admin=False, exp_revert=False)
                        actual_submitted.remove(p)

                        # should be able to withdraw entire stake at this point
                        self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold - 1, {'from': p}], use_multi_admin=False, exp_revert=True)
                        if self.competition.getStake(p) > stake_threshold:
                            self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold, {'from': p}], use_multi_admin=False, exp_revert=False)
                        self.execute_fn(self.token, self.token.decreaseStake, [self.competition, self.token.getStake(self.competition, p), {'from': p}], use_multi_admin=False, exp_revert=False)

            # Verify stake record
            print('Verify stake records.')
            for p in tqdm(participants):
                submission = self.competition.getSubmission(challenge_number, p)
                recorded_stake = self.competition.getStake(p)
                recorded_stake_b = self.token.getStake(self.competition, p)

                assert recorded_stake == recorded_stake_b, '{} : {}'.format(
                    recorded_stake,
                    recorded_stake_b)

            # Increase Stake should still work at this point regardless of submission
            for p in participants:
                p_bal = self.token.balanceOf(p)
                p_stake = self.competition.getStake(p)
                if p_bal > 1:
                    if random.choice([True, False]):
                        stake_amount = random.randint(p_stake + 1, p_stake + p_bal)
                        self.execute_fn(self.token, self.token.setStake, [self.competition, stake_amount, {'from': p}], use_multi_admin=False, exp_revert=stake_amount < stake_threshold)
                        if stake_amount >= stake_threshold:
                            assert self.competition.getStake(p) == stake_amount == self.token.getStake(
                                self.competition, p)
                    else:
                        stake_amount = random.randint(1, p_bal)
                        current_stake = self.competition.getStake(p)
                        self.execute_fn(self.competition, self.competition.increaseStake, [p, stake_amount, {'from': p}], use_multi_admin=False, exp_revert=True)
                        self.execute_fn(self.token, self.token.increaseStake, [self.competition, stake_amount, {'from': p}], use_multi_admin=False, exp_revert=(p_stake + stake_amount) < stake_threshold)
                        if (p_stake + stake_amount) >= stake_threshold:
                            assert self.competition.getStake(p) == (
                                    current_stake + stake_amount) == self.token.getStake(
                                self.competition, p)

            self.unauthorized_calls_check(non_admin=participants[-1], admin=self.admin)

            # Test authorized actions expected to fail
            # https://app.gitbook.com/@rocket-capital-investment/s/competition-dapp/contract-details/method-restrictions-by-phase
            self.execute_fn(self.competition, self.competition.openChallenge,
                            [getHash(), getHash(), getTimestamp(), getTimestamp(), {'from': self.admin}],
                            self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.submitResults, [getHash(), {'from': self.admin}],
                            self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.updateResults,
                            [self.competition.getResultsHash(challenge_number), getHash(), {'from': self.admin}],
                            self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.payRewards, [[p], [1], [1], [1], {'from': self.admin}],
                            self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.updateChallengeAndTournamentScores,
                            [challenge_number, [self.admin], [1], [1], {'from': self.admin}], self.use_multi_admin,
                            exp_revert=True)
            self.execute_fn(self.competition, self.competition.updateInformationBatch,
                            [challenge_number, [self.admin], 1, [1], {'from': self.admin}], self.use_multi_admin,
                            exp_revert=True)
            self.execute_fn(self.competition, self.competition.advanceToPhase, [3, {'from': self.admin}],
                            self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.advanceToPhase, [4, {'from': self.admin}],
                            self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.moveRemainderToPool, [{'from': self.admin}],
                            self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.sponsor, [1, {'from': self.admin}], self.use_multi_admin,
                            exp_revert=True)
            self.execute_fn(self.competition, self.competition.recordStakes,
                            [0, 1, {'from': self.admin}], self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.burn, [[self.admin], [1], {'from': self.admin}],
                            use_multi_admin=self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.moveBurnedToPool, [1, {'from': self.admin}],
                            use_multi_admin=self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.moveBurnedOut, [1, {'from': self.admin}],
                            use_multi_admin=self.use_multi_admin, exp_revert=True)

            #############################
            ########## PHASE 2 ##########
            #############################
            print('--- Phase 2 ---')
            self.execute_fn(self.competition, self.competition.closeSubmission, [{'from': self.admin}], self.use_multi_admin, exp_revert=False)
            verify(2, self.competition.getPhase(challenge_number))
            verify(len(chain) - 1, self.competition.submissionClosedBlockNumbers(challenge_number))
            self.submission_closed_block_numbers[challenge_number] = self.competition.submissionClosedBlockNumbers(challenge_number)

            staker_list = self.competition.getAllStakers()
            recorded_stakes = self.competition.getHistoricalStakeAmounts(challenge_number, staker_list)
            total_staked = self.competition.getHistoricalTotalStaked(challenge_number)
            verify(0, sum(recorded_stakes))
            verify(0, total_staked)
            chunk = 2
            for i in range(0, len(staker_list), chunk):
                if (i+chunk) > len(staker_list):
                    end_index = len(staker_list)
                else:
                    end_index = i + chunk
                self.execute_fn(self.competition, self.competition.recordStakes, [i, end_index, {'from': self.admin}], self.use_multi_admin, exp_revert=False)

            # Test recording same participants repeatedly.
            self.execute_fn(self.competition, self.competition.recordStakes,
                            [i, end_index, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            # Test recording out of range index.
            self.execute_fn(self.competition, self.competition.recordStakes,
                            [0, len(staker_list) + 1, {'from': self.admin}], self.use_multi_admin, exp_revert=True)
            try:
                self.stake_amt_history[challenge_number]
            except:
                self.stake_amt_history[challenge_number] = {}
            print('Verify historical stakes.')
            stake_total = 0
            for s in tqdm(staker_list):
                self.stake_amt_history[challenge_number][s] = self.competition.getStake(s)
                verify(self.stake_amt_history[challenge_number][s], self.competition.getHistoricalStakeAmounts(challenge_number, [s])[0])
                stake_total += self.stake_amt_history[challenge_number][s]
            verify(stake_total, self.competition.getHistoricalTotalStaked(challenge_number))
            self.staker_set_history[challenge_number] = set(self.competition.getHistoricalStakers(challenge_number))

            staker_list = self.competition.getAllStakers()
            total_staked = 0
            total_staked2 = 0
            for st in staker_list:
                total_staked2 += self.competition.getStake(st)

            for i in range(0, len(staker_list), chunk):
                if (i + chunk) > len(staker_list):
                    stakers = staker_list[i:]
                else:
                    stakers = staker_list[i:i+chunk]

                recorded_stakes = self.competition.getHistoricalStakeAmounts(challenge_number, stakers)
                total_staked += sum(recorded_stakes)
            verify(self.competition.getCurrentTotalStaked(), total_staked)
            verify(total_staked, self.competition.getHistoricalTotalStaked(challenge_number))

            self.staking_submissions_restricted_check(participants[-1])

            submission_count = self.competition.getSubmissionCounter(challenge_number)

            split_0 = submission_count // 3
            split_1 = submission_count // 2

            submitters_0 = self.competition.getSubmitters(challenge_number, 0, split_0)
            verify(split_0, len(submitters_0))
            submitters_1 = self.competition.getSubmitters(challenge_number, split_0, split_1)
            verify(split_1 - split_0, len(submitters_1))
            submitters_2 = self.competition.getSubmitters(challenge_number, split_1, submission_count)
            verify(submission_count - split_1, len(submitters_2))

            verify(actual_submitted, set(submitters_0 + submitters_1 + submitters_2))

            submitters_list = self.competition.getSubmitters(challenge_number, 0, submission_count)
            verify(self.competition.getSubmissionCounter(challenge_number), len(submitters_list))

            verify(actual_submitted, set(submitters_list))

            self.execute_fn(self.competition, self.competition.updateVault, [self.vault2, {'from': self.admin}],
                            use_multi_admin=self.use_multi_admin, exp_revert=False)
            verify(self.vault2, self.competition.getVault())
            self.execute_fn(self.competition, self.competition.updateVault, [self.vault, {'from': self.admin}],
                            use_multi_admin=self.use_multi_admin, exp_revert=False)

            self.unauthorized_calls_check(non_admin=participants[-1], admin=self.admin)

            # Test authorized actions expected to fail
            for s in actual_submitted:
                self.execute_fn(self.token, self.token.increaseStake, [self.competition, 1, {'from': s}],
                                use_multi_admin=False, exp_revert=True)
                self.execute_fn(self.token, self.token.decreaseStake, [self.competition, 1, {'from': s}],
                                use_multi_admin=False, exp_revert=True)
                staked = self.competition.getStake(self.admin)
                self.execute_fn(
                    self.token, self.token.stakeAndSubmit,
                    [self.competition, staked, getHash(), {'from': self.admin}],
                                use_multi_admin=self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.token, self.token.stakeAndSubmit,
                                [self.competition, staked, getHash(), {'from': s}],
                                use_multi_admin=False, exp_revert=True)
                self.execute_fn(self.competition, self.competition.openChallenge,
                                [getHash(), getHash(), getTimestamp(), getTimestamp(), {'from': self.admin}],
                                self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.competition, self.competition.updateDataset,
                                [getHash(), {'from': self.admin}],
                                self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.competition, self.competition.updateKey,
                                [getHash(), {'from': self.admin}],
                                self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.competition, self.competition.closeSubmission, [{'from': self.admin}],
                                self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.competition, self.competition.submitResults, [getHash(), {'from': self.admin}],
                                self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.competition, self.competition.updateResults,
                                [self.competition.getResultsHash(challenge_number), getHash(), {'from': self.admin}],
                                self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.competition, self.competition.payRewards, [[p], [1], [1], [1], {'from': self.admin}],
                                self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.competition, self.competition.updateChallengeAndTournamentScores,
                                [challenge_number, [self.admin], [1], [1], {'from': self.admin}], self.use_multi_admin,
                                exp_revert=True)
                self.execute_fn(self.competition, self.competition.updateInformationBatch,
                                [challenge_number, [self.admin], 1, [1], {'from': self.admin}], self.use_multi_admin,
                                exp_revert=True)
                self.execute_fn(self.competition, self.competition.advanceToPhase, [4, {'from': self.admin}],
                                self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.competition, self.competition.moveRemainderToPool, [{'from': self.admin}],
                                self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.competition, self.competition.sponsor, [1, {'from': self.admin}], self.use_multi_admin,
                                exp_revert=True)
                self.execute_fn(self.competition, self.competition.burn, [[self.admin], [1], {'from': self.admin}],
                                use_multi_admin=self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.competition, self.competition.moveBurnedToPool, [1, {'from': self.admin}],
                                use_multi_admin=self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.competition, self.competition.moveBurnedOut, [1, {'from': self.admin}],
                                use_multi_admin=self.use_multi_admin, exp_revert=True)

            #############################
            ########## PHASE 3 ##########
            #############################
            print('--- Phase 3 ---')
            self.staking_submissions_restricted_check(participants[-1])
            p = submitters[0]
            self.execute_fn(self.competition, self.competition.advanceToPhase, [3, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            verify(3, self.competition.getPhase(challenge_number))
            challenge_number = self.competition.getLatestChallengeNumber()

            self.unauthorized_calls_check(non_admin=participants[-1], admin=self.admin)

            # Test authorized actions expected to fail
            for s in actual_submitted:
                staked = self.competition.getStake(self.admin)
                self.execute_fn(
                    self.token, self.token.stakeAndSubmit,
                    [self.competition, staked, getHash(), {'from': self.admin}],
                                use_multi_admin=self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.token, self.token.stakeAndSubmit,
                                [self.competition, staked, getHash(), {'from': s}],
                                use_multi_admin=False, exp_revert=True)
                self.execute_fn(self.competition, self.competition.openChallenge,
                                [getHash(), getHash(), getTimestamp(), getTimestamp(), {'from': self.admin}],
                                self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.competition, self.competition.updateDataset,
                                [getHash(), {'from': self.admin}],
                                self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.competition, self.competition.updateKey,
                                [getHash(), {'from': self.admin}],
                                self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.competition, self.competition.closeSubmission, [{'from': self.admin}],
                                self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.competition, self.competition.advanceToPhase, [3, {'from': self.admin}],
                                self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.competition, self.competition.moveRemainderToPool, [{'from': self.admin}],
                                self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.competition, self.competition.sponsor, [1, {'from': self.admin}], self.use_multi_admin,
                                exp_revert=True)  # expected to fail due to fail due to insufficient ERC20 alowance
                self.execute_fn(self.competition, self.competition.moveBurnedToPool, [1, {'from': self.admin}],
                                use_multi_admin=self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.competition, self.competition.moveBurnedOut, [1, {'from': self.admin}],
                                use_multi_admin=self.use_multi_admin, exp_revert=True)

            results_hash = getHash()
            self.execute_fn(self.competition, self.competition.submitResults, [results_hash, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            verify(results_hash, self.competition.getResultsHash(challenge_number).hex())

            new_results_hash = getHash()
            self.execute_fn(self.competition, self.competition.updateResults, [results_hash, new_results_hash, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            verify(new_results_hash, self.competition.getResultsHash(challenge_number).hex())
            self.execute_fn(self.competition, self.competition.updateResults, [results_hash, new_results_hash, {'from': self.admin}], self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.updateResults, [new_results_hash, new_results_hash, {'from': self.admin}], self.use_multi_admin, exp_revert=True)

            # Test that can add to competition pool at this point.
            if random.choice([True, False]):
                add_sponsor_amt = int(100000e6)
                competition_pool = self.competition.getCompetitionPool()
                self.execute_fn(self.token, self.token.increaseAllowance,
                                [self.competition, add_sponsor_amt, {'from': self.admin}],
                                self.use_multi_admin, exp_revert=False)
                self.execute_fn(self.competition, self.competition.sponsor, [add_sponsor_amt, {'from': self.admin}],
                                self.use_multi_admin, exp_revert=False)
                new_comp_pool = competition_pool + add_sponsor_amt
                verify(new_comp_pool, self.competition.getCompetitionPool())

            # make rewards payment
            awardees = getRandomSelection(submitters, min_num=len(submitters) * 1 // 2)
            winners = []
            staking_rewards = []
            challenge_rewards = []
            tournament_rewards = []
            burn_amounts = []
            challenge_scores = []
            tournament_scores = []
            proportion = random.randint(0, 95)
            rand_ceil = 95 - proportion
            initial_rewards_pool = self.competition.getCompetitionPool()

            for a in awardees[:-1]:
                winners.append(a)
                stake = self.competition.getStake(a)
                allocated = int(proportion * initial_rewards_pool // 100)
                stk_rewards, ch_rewards, tn_rewards = int(0.3 * allocated), int(0.45 * allocated), int(0.25 * allocated)
                staking_rewards.append(stk_rewards)
                challenge_rewards.append(ch_rewards)
                tournament_rewards.append(tn_rewards)
                burn_amounts.append(int(proportion * stake // 100))
                challenge_scores.append(int(random.random() * 1e6))
                tournament_scores.append(int(random.random() * 1e6))
                proportion = random.randint(0, rand_ceil)
                rand_ceil = rand_ceil - proportion

            winners.append(awardees[-1])
            stake = self.competition.getStake(awardees[-1])
            allocated = int(proportion * initial_rewards_pool // 100)
            stk_rewards, ch_rewards, tn_rewards = int(0.3 * allocated), int(0.45 * allocated), int(0.25 * allocated)
            staking_rewards.append(stk_rewards)
            challenge_rewards.append(ch_rewards)
            tournament_rewards.append(tn_rewards)
            burn_amounts.append(int(proportion * stake // 100))
            challenge_scores.append(int(random.random() * 1e6))
            tournament_scores.append(int(random.random() * 1e6))

            self.execute_fn(self.competition, self.competition.payRewards,
                            [winners[:-1], staking_rewards, challenge_rewards, tournament_rewards, {'from': self.admin}],
                            self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.payRewards,
                            [winners, staking_rewards, challenge_rewards, tournament_rewards, {'from': self.admin}],
                            self.use_multi_admin, exp_revert=False)

            self.execute_fn(self.competition, self.competition.burn,
                            [winners[:-1], burn_amounts, {'from': self.admin}], self.use_multi_admin, exp_revert=True)

            self.execute_fn(self.competition, self.competition.burn,
                            [winners, burn_amounts, {'from': self.admin}], self.use_multi_admin, exp_revert=False)

            # Test subsequent burn
            w = winners[0]
            second_burn_amt = self.competition.getStake(w)
            self.execute_fn(self.competition, self.competition.burn,
                            [[w], [second_burn_amt], {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            burn_amounts[0] += second_burn_amt

            self.execute_fn(self.competition, self.competition.updateChallengeAndTournamentScores, [challenge_number, winners[:-1], challenge_scores, tournament_scores, {'from': self.admin}], self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.updateChallengeAndTournamentScores, [challenge_number, winners, challenge_scores, tournament_scores, {'from': self.admin}], self.use_multi_admin, exp_revert=False)

            print('Verify reward, burned and score values.')
            for i in tqdm(range(len(winners))):
                verify(staking_rewards[i], self.competition.getStakingRewards(challenge_number, winners[i]))
                verify(challenge_rewards[i], self.competition.getChallengeRewards(challenge_number, winners[i]))
                verify(tournament_rewards[i], self.competition.getTournamentRewards(challenge_number, winners[i]))
                # verify(staking_rewards[i] + challenge_rewards[i] + tournament_rewards[i],
                #        self.competition.getOverallRewards(challenge_number, winners[i]))
                verify(burn_amounts[i], self.competition.getBurnedAmount(challenge_number, winners[i]))
                verify(challenge_scores[i], self.competition.getChallengeScores(challenge_number, winners[i]))
                verify(tournament_scores[i], self.competition.getTournamentScores(challenge_number, winners[i]))

            self.execute_fn(self.competition, self.competition.updateVault, [self.vault2, {'from': self.admin}],
                            use_multi_admin=self.use_multi_admin, exp_revert=False)
            verify(self.vault2, self.competition.getVault())
            self.execute_fn(self.competition, self.competition.updateVault, [self.vault, {'from': self.admin}],
                            use_multi_admin=self.use_multi_admin, exp_revert=False)

            #############################
            ########## PHASE 4 ##########
            #############################
            print('--- Phase 4 ---')
            self.staking_submissions_restricted_check(participants[-1])
            self.execute_fn(self.competition, self.competition.advanceToPhase, [4, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            self.unauthorized_calls_check(non_admin=participants[-1], admin=self.admin)

            # Test authorized actions expected to fail
            for s in actual_submitted:
                staked = self.competition.getStake(self.admin)
                self.execute_fn(
                    self.token, self.token.stakeAndSubmit,
                    [self.competition, staked, getHash(), {'from': self.admin}],
                                use_multi_admin=self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.token, self.token.stakeAndSubmit,
                                [self.competition, staked, getHash(), {'from': s}],
                                use_multi_admin=False, exp_revert=True)
                self.execute_fn(self.competition, self.competition.updateDataset,
                                [getHash(), {'from': self.admin}],
                                self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.competition, self.competition.updateKey,
                                [getHash(), {'from': self.admin}],
                                self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.competition, self.competition.closeSubmission, [{'from': self.admin}],
                                self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.competition, self.competition.advanceToPhase, [4, {'from': self.admin}],
                                self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.competition, self.competition.payRewards, [[p], [1], [1], [1], {'from': self.admin}],
                                self.use_multi_admin, exp_revert=True)
                self.execute_fn(self.competition, self.competition.burn, [[self.admin], [1], {'from': self.admin}],
                                use_multi_admin=self.use_multi_admin, exp_revert=True)

            verify(4, self.competition.getPhase(challenge_number))

            priv_key = getHash()
            self.execute_fn(self.competition, self.competition.updatePrivateKey, [challenge_number, priv_key, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            verify(priv_key, self.competition.getPrivateKeyHash(challenge_number).hex())

            message = str(getHash())
            self.execute_fn(self.competition, self.competition.updateMessage, [message, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            verify(message, self.competition.getMessage())

            new_rewards_threshold = random.randint(int(Decimal('100e6')), int(Decimal('10000e6')))
            new_stake_threshold = random.randint(int(Decimal('0.1e6')), int(Decimal('100e6')))
            self.execute_fn(self.competition, self.competition.updateRewardsThreshold, [new_rewards_threshold, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            self.execute_fn(self.competition, self.competition.updateStakeThreshold, [new_stake_threshold, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            verify(new_rewards_threshold, self.competition.getRewardsThreshold())
            verify(new_stake_threshold, self.competition.getStakeThreshold())

            info_participants = random.sample(participants, 2)
            item_num = random.randint(0, 10)
            info_values = [int(getHash(), 16), int(getHash(), 16)]

            self.execute_fn(self.competition, self.competition.updateInformationBatch, [challenge_number, info_participants[:-1], item_num, info_values, {'from': self.admin}], self.use_multi_admin, exp_revert=True)

            self.execute_fn(self.competition, self.competition.updateInformationBatch, [challenge_number, info_participants, item_num, info_values, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            verify(info_values[0], self.competition.getInformation(challenge_number, info_participants[0], item_num))
            verify(info_values[1], self.competition.getInformation(challenge_number, info_participants[1], item_num))

            total_stake = 0
            for p in participants:
                total_stake += self.competition.getStake(p)

            verify(total_stake, self.competition.getCurrentTotalStaked() - existing_stake)

            competition_pool = self.competition.getCompetitionPool()
            verify(0, self.competition.getRemainder())
            verify(self.token.balanceOf(self.competition),
                   self.competition.getCompetitionPool() + self.competition.getCurrentTotalStaked()
                   + self.competition.getRemainder() + self.competition.getTotalBurnedAmount())

            # should revert since no remainder to move
            self.execute_fn(self.competition, self.competition.moveRemainderToPool, [{'from': self.admin}], self.use_multi_admin, exp_revert=True)

            if not self.use_multi_admin:
                admin_bal = self.token.balanceOf(self.admin)
            else:
                admin_bal = self.token.balanceOf(self.multi_sig)

            transfer_amount = admin_bal // 1000
            self.execute_fn(self.token, self.token.transfer, [self.competition, transfer_amount, {'from': self.admin}],
                            self.use_multi_admin, exp_revert=False)
            verify(transfer_amount, self.competition.getRemainder())
            verify(self.token.balanceOf(self.competition),
                   self.competition.getCompetitionPool() + self.competition.getCurrentTotalStaked()
                   + self.competition.getRemainder() + self.competition.getTotalBurnedAmount())

            self.execute_fn(self.competition, self.competition.moveRemainderToPool, [{'from': self.admin}],
                            self.use_multi_admin, exp_revert=False)
            verify(0, self.competition.getRemainder())
            verify(self.token.balanceOf(self.competition),
                   self.competition.getCompetitionPool() + self.competition.getCurrentTotalStaked()
                   + self.competition.getRemainder() + self.competition.getTotalBurnedAmount())
            verify(competition_pool + transfer_amount, self.competition.getCompetitionPool())

            # Move burned amounts.
            print('Test moving burned amounts.')
            burned_amt = self.competition.getTotalBurnedAmount()
            competition_pool = self.competition.getCompetitionPool()
            move_amt = int(0.2 * burned_amt)

            self.execute_fn(self.competition, self.competition.moveBurnedToPool,
                            [burned_amt + 1, {'from': self.admin}],
                            use_multi_admin=self.use_multi_admin, exp_revert=True)

            self.execute_fn(self.competition, self.competition.moveBurnedToPool,
                            [move_amt, {'from': self.admin}],
                            use_multi_admin=self.use_multi_admin, exp_revert=False)
            
            verify(burned_amt - move_amt, self.competition.getTotalBurnedAmount())
            verify(competition_pool + move_amt, self.competition.getCompetitionPool())

            burned_amt = self.competition.getTotalBurnedAmount()
            competition_pool = self.competition.getCompetitionPool()
            move_amt = int(0.3 * burned_amt)
            extern_bal = self.token.balanceOf(self.admin)

            self.execute_fn(self.competition, self.competition.updateBurnRecipient, 
                            [self.competition, {'from': self.admin}],
                            use_multi_admin=self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.updateBurnRecipient,
                            [self.admin, {'from': self.admin}],
                            use_multi_admin=self.use_multi_admin, exp_revert=False)
            verify(self.admin, self.competition.getBurnRecipient())
            
            self.execute_fn(self.competition, self.competition.moveBurnedOut,
                            [burned_amt + 1, {'from': self.admin}],
                            use_multi_admin=self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.moveBurnedOut,
                            [move_amt, {'from': self.admin}],
                            use_multi_admin=self.use_multi_admin, exp_revert=False)
            verify(burned_amt - move_amt, self.competition.getTotalBurnedAmount())
            verify(extern_bal + move_amt, self.token.balanceOf(self.admin))
            
            # Change burn recipient and test again.
            burned_amt = self.competition.getTotalBurnedAmount()
            move_amt = burned_amt
            user = self.participants[-1]
            extern_bal = self.token.balanceOf(user)
            self.execute_fn(self.competition, self.competition.updateBurnRecipient,
                            [user, {'from': self.admin}],
                            use_multi_admin=self.use_multi_admin, exp_revert=False)
            verify(user, self.competition.getBurnRecipient())

            self.execute_fn(self.competition, self.competition.moveBurnedOut,
                            [move_amt, {'from': self.admin}],
                            use_multi_admin=self.use_multi_admin, exp_revert=False)
            verify(0, self.competition.getTotalBurnedAmount())
            verify(extern_bal + move_amt, self.token.balanceOf(user))
            verify(competition_pool, self.competition.getCompetitionPool())

        print('Verifying challenge history.')
        for ch in tqdm(challenge_history):
            historical_stakers, historical_amounts = self.get_historical_stakers_and_amounts(ch)
            verify(self.staker_set_history[ch], set(historical_stakers))
            total_staked = 0
            for stkr_amt in zip(historical_stakers, historical_amounts):
                staker = stkr_amt[0]
                amt = stkr_amt[1]
                verify(self.stake_amt_history[ch][staker], amt)
                total_staked += amt
            verify(total_staked, self.competition.getHistoricalTotalStaked(ch))

        self.execute_fn(self.competition, self.competition.updateVault, [self.vault2, {'from': self.admin}],
                        use_multi_admin=self.use_multi_admin, exp_revert=False)
        verify(self.vault2, self.competition.getVault())
        self.execute_fn(self.competition, self.competition.updateVault, [self.vault, {'from': self.admin}],
                        use_multi_admin=self.use_multi_admin, exp_revert=False)

    def staking_submissions_test(self, challenge_number, p):
        # test new staking and submissions logic

        if self.competition.getStake(p) != 0:
            self.execute_fn(self.token, self.token.setStake, [self.competition, 0, {'from': p}], use_multi_admin=False,
                            exp_revert=False)

        # Should not be able to withdraw beyond current stake.
        self.execute_fn(self.token, self.token.decreaseStake, [self.competition, 1, {'from': p}], use_multi_admin=False,
                        exp_revert=True)

        stake_threshold = self.competition.getStakeThreshold()
        verify(bytes([0] * 32).hex(), self.competition.getSubmission(challenge_number, p).hex())

        staked = self.competition.getStake(p)
        self.execute_fn(
            self.token, self.token.stakeAndSubmit,
            [self.competition, staked, getHash(), {'from': p}],
                        use_multi_admin=False, exp_revert=True)
        # submitNewPrediction 0, 0, 0

        staked = self.competition.getStake(p)
        self.execute_fn(self.token, self.token.stakeAndSubmit,
                        [self.competition, staked, getHash(), {'from': p}],
                        use_multi_admin=False, exp_revert=True)
        # updateSubmission 0, 0, 0

        self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold, {'from': p}],
                        use_multi_admin=False, exp_revert=False)
        # increaseStake 0, 0, 1

        self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold - 1, {'from': p}],
                        use_multi_admin=False, exp_revert=True)
        # decreaseStake 1, 0, 1

        self.execute_fn(self.token, self.token.setStake, [self.competition, 0, {'from': p}], use_multi_admin=False,
                        exp_revert=False)
        # decreaseStake 0, 0, 1

        self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold, {'from': p}],
                        use_multi_admin=False, exp_revert=False)
        self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold + 1, {'from': p}],
                        use_multi_admin=False, exp_revert=False)
        # increaseStake 1, 0, 1

        staked = self.competition.getStake(p)
        self.execute_fn(
            self.token, self.token.stakeAndSubmit,
            [self.competition, staked, getHash(), {'from': p}],
                        use_multi_admin=False, exp_revert=False)
        # submitNewPrediction 1, 0, 1

        staked = self.competition.getStake(p)
        self.execute_fn(
            self.token, self.token.stakeAndSubmit,
            [self.competition, staked, getHash(), {'from': p}],
                        use_multi_admin=False, exp_revert=False)
        # submitNewPrediction 1, 1, 0

        self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold + 2, {'from': p}],
                        use_multi_admin=False, exp_revert=False)
        # increaseStake 1, 1, 1

        self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold, {'from': p}],
                        use_multi_admin=False, exp_revert=False)
        # decreaseStake 1, 1, 1 final stake >= threshold

        self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold - 1, {'from': p}],
                        use_multi_admin=False, exp_revert=True)
        # decreaseStake 1, 1, 0 final stake < threshold

        staked = self.competition.getStake(p)
        self.execute_fn(
            self.token, self.token.stakeAndSubmit,
                        [self.competition, staked, getHash(), {'from': p}],
                        use_multi_admin=False, exp_revert=False)
        # updateSubmission 1, 1, 1

        ## Withdraw
        length_of_submitters = self.competition.getSubmissionCounter(challenge_number)
        self.execute_fn(self.token, self.token.stakeAndSubmit,
                        [self.competition, 0, bytes([0] * 32),
                         {'from': p}], use_multi_admin=False, exp_revert=False)
        new_length_of_submitters = self.competition.getSubmissionCounter(challenge_number)
        verify(length_of_submitters, new_length_of_submitters + 1)






