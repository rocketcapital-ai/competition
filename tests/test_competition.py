from utils_for_testing import *
from brownie import Token, Competition, reverts, accounts


class TestCompetition:
    def setup(self):
        self.use_multi_admin = False
        self.admin = accounts[0]
        self.participants = accounts[1:]
        self.token = Token.deploy("RockCap Token", "RCP", int(Decimal('100000000e18')), {'from': self.admin})
        self.competition = Competition.deploy({'from': self.admin})

        # airdrop to participants
        total_airdrop = int(Decimal(0.01) * Decimal(self.token.totalSupply()))
        single_airdrop = total_airdrop // (len(accounts) - 1)
        for i in range(len(self.participants)):
            self.execute_fn(self.token, self.token.transfer,
                            [self.participants[i], single_airdrop, {'from': self.admin}],
                            self.use_multi_admin, exp_revert=False)

        stake_threshold = int(Decimal('10e18'))
        challenge_rewards_threshold = int(Decimal('10e18'))

        # Cannot initialize with self.token address set to 0.
        self.execute_fn(self.competition, self.competition.initialize,
                        [stake_threshold, challenge_rewards_threshold, '0x{}'.format('0'*40), {'from': self.admin}],
                        self.use_multi_admin, exp_revert=True)

        self.execute_fn(self.competition, self.competition.initialize,
                        [stake_threshold, challenge_rewards_threshold, self.token, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=False)

        self.execute_fn(self.token, self.token.authorizeCompetition,
                        [self.competition, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=False)

        verify(stake_threshold, self.competition.getStakeThreshold())
        verify(challenge_rewards_threshold, self.competition.getRewardsThreshold())
        verify(0, self.competition.getLatestChallengeNumber())
        verify(4, self.competition.getPhase(0))
        verify(Decimal('0.2'), uint_to_float(self.competition.getChallengeRewardsPercentageInWei()))
        verify(Decimal('0.6'), uint_to_float(self.competition.getTournamentRewardsPercentageInWei()))
        verify(self.token, self.competition.getTokenAddress())
        verify(True, self.token.competitionIsAuthorized(self.competition))

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

    def staking_restricted_check(self, non_admin):
        self.execute_fn(self.competition, self.competition.increaseStake, [non_admin, 1, {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.decreaseStake, [non_admin, 1, {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.token, self.token.increaseStake, [self.competition, 1, {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.token, self.token.decreaseStake, [self.competition, 1, {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.token, self.token.setStake, [self.competition, 1, {'from': non_admin}], use_multi_admin=False, exp_revert=True)


    def unauthorized_calls_check(self, non_admin, admin):
        main_admin_hash = self.competition.RCI_MAIN_ADMIN().hex()
        child_admin_hash = self.competition.RCI_CHILD_ADMIN().hex()
        challenge_number = self.competition.getLatestChallengeNumber()
        self.execute_fn(self.competition, self.competition.revokeRole, [child_admin_hash, admin, {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.grantRole, [child_admin_hash, non_admin, {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.renounceRole, [child_admin_hash, admin, {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.revokeRole, [main_admin_hash, admin, {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.grantRole, [main_admin_hash, non_admin, {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.renounceRole, [main_admin_hash, admin, {'from': non_admin}], use_multi_admin=False, exp_revert=True)

        self.execute_fn(self.competition, self.competition.updateMessage, [str(getHash()), {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.updateDeadlines, [challenge_number, 0, 123456, {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.updateRewardsThreshold, [1, {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.updateStakeThreshold, [1, {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.updateChallengeRewardsPercentageInWei, [1, {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.updateTournamentRewardsPercentageInWei, [1, {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.openChallenge, [getHash(), getHash(), getTimestamp(), getTimestamp(), {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.updateDataset, [self.competition.getDatasetHash(challenge_number), getHash(), {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.updateKey, [self.competition.getKeyHash(challenge_number), getHash(), {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.updatePrivateKey, [challenge_number, getHash(), {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.closeSubmission, [{'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.submitResults, [getHash(), {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.updateResults, [self.competition.getResultsHash(challenge_number), getHash(), {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.payRewards, [[non_admin], [1], [1], [1], {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.updateChallengeAndTournamentScores, [challenge_number, [non_admin], [1], [1], {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.updateInformationBatch, [challenge_number, [non_admin], 1, [1], {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.advanceToPhase, [self.competition.getPhase(challenge_number) + 1, {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.moveRemainderToPool, [{'from': non_admin}], use_multi_admin=False, exp_revert=True)


    def set_new_rewards_percentages(self, admin):
        if random.choice([True, False]):
            new_challenge_rewards_percentage = Decimal(random.uniform(0, 1))
            new_tnmt_rewards_percentage = Decimal(random.uniform(0, 1 - float(new_challenge_rewards_percentage)))

            new_challenge_rewards_percentage *= Decimal('1e18')
            new_challenge_rewards_percentage = int(new_challenge_rewards_percentage)
            new_tnmt_rewards_percentage *= Decimal('1e18')
            new_tnmt_rewards_percentage = int(new_tnmt_rewards_percentage)

            self.execute_fn(self.competition, self.competition.updateChallengeRewardsPercentageInWei, [new_challenge_rewards_percentage, {'from': admin}], self.use_multi_admin, exp_revert=False)
            self.execute_fn(self.competition, self.competition.updateTournamentRewardsPercentageInWei, [new_tnmt_rewards_percentage, {'from': admin}], self.use_multi_admin, exp_revert=False)


    def test_rewards_percentage_adjustment(self):
        for challenge_round in range(2):
            sponsor_amount = int(Decimal('1000e18'));
            self.execute_fn(self.token, self.token.increaseAllowance, [self.competition, sponsor_amount, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            self.execute_fn(self.competition, self.competition.sponsor, [sponsor_amount, {'from': self.admin}], self.use_multi_admin, exp_revert=False)

            pool = self.competition.getCompetitionPool()
            challenge_rewards_percentage = self.competition.getChallengeRewardsPercentageInWei()
            tnmt_rewards_percentage = self.competition.getTournamentRewardsPercentageInWei()
            expected_challenge_budget = int(Decimal(pool * challenge_rewards_percentage) // Decimal('1e18'))
            expected_tnmt_budget = int(Decimal(pool * tnmt_rewards_percentage) // Decimal('1e18'))
            expected_staking_budget = pool - expected_challenge_budget - expected_tnmt_budget

            self.execute_fn(self.competition, self.competition.openChallenge, [getHash(), getHash(), getTimestamp(), getTimestamp(), {'from': self.admin}], self.use_multi_admin, exp_revert=False)

            actual_staking_budget = self.competition.getCurrentStakingRewardsBudget()
            actual_challenge_budget = self.competition.getCurrentChallengeRewardsBudget()
            actual_tnmt_budget = self.competition.getCurrentTournamentRewardsBudget()

            verify(expected_staking_budget, actual_staking_budget)
            verify(expected_challenge_budget, actual_challenge_budget)
            verify(expected_tnmt_budget, actual_tnmt_budget)

            self.execute_fn(self.competition, self.competition.closeSubmission, [{'from': self.admin}], self.use_multi_admin, exp_revert=False)
            self.set_new_rewards_percentages(self.admin)

            self.execute_fn(self.competition, self.competition.advanceToPhase, [3, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            self.set_new_rewards_percentages(self.admin)

            self.execute_fn(self.competition, self.competition.advanceToPhase, [4, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            self.set_new_rewards_percentages(self.admin)


    def test_full_run(self):
        self.execute_fn(self.competition, self.competition.initialize, [int(Decimal('10e18')), int(Decimal('10e18')), self.token, {'from': self.admin}], self.use_multi_admin, exp_revert=True)

        participants = self.participants

        for challenge_round in range(2):
            # Sponsor
            current_pool = self.competition.getCompetitionPool()
            rewards_threshold = self.competition.getRewardsThreshold()
            if current_pool < rewards_threshold:
                self.execute_fn(self.competition, self.competition.openChallenge, [getHash(), getHash(), getTimestamp(), getTimestamp(), {'from': self.admin}], self.use_multi_admin, exp_revert=True)

            sponsor_amount = int(rewards_threshold * 2)
            self.execute_fn(self.token, self.token.increaseAllowance, [self.competition, sponsor_amount, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            self.execute_fn(self.competition, self.competition.sponsor, [sponsor_amount, {'from': self.admin}], self.use_multi_admin, exp_revert=False)

            self.unauthorized_calls_check(non_admin=participants[-1], admin=self.admin)

            self.execute_fn(self.competition, self.competition.submitNewPredictions, [getHash(), {'from': participants[0]}], use_multi_admin=False, exp_revert=True)

            challenge_number = self.competition.getLatestChallengeNumber()
            verify(self.competition.getPhase(challenge_number), 4)

            #############################
            ########## PHASE 1 ##########
            #############################

            dataset_hash = getHash()
            key_hash = getHash()

            self.execute_fn(self.competition, self.competition.openChallenge, [dataset_hash, key_hash, getTimestamp(), getTimestamp(), {'from': self.admin}], self.use_multi_admin, exp_revert=False)

            challenge_number = self.competition.getLatestChallengeNumber()
            verify(1, self.competition.getPhase(challenge_number))
            verify(dataset_hash, self.competition.getDatasetHash(challenge_number).hex())
            verify(key_hash, self.competition.getKeyHash(challenge_number).hex())

            # Update dataset and public key hashes
            new_dataset_hash = getHash()
            new_key_hash = getHash()

            self.execute_fn(self.competition, self.competition.updateDataset, [bytes([0] * 32), new_dataset_hash, {'from': self.admin}], self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.updateDataset, [dataset_hash, dataset_hash, {'from': self.admin}], self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.updateDataset, [new_dataset_hash, new_dataset_hash, {'from': self.admin}], self.use_multi_admin, exp_revert=True)

            self.execute_fn(self.competition, self.competition.updateDataset, [dataset_hash, new_dataset_hash, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            verify(new_dataset_hash, self.competition.getDatasetHash(challenge_number).hex())

            self.execute_fn(self.competition, self.competition.updateKey, [bytes([0] * 32), new_key_hash, {'from': self.admin}], self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.updateKey, [key_hash, key_hash, {'from': self.admin}], self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.updateKey, [new_key_hash, new_key_hash, {'from': self.admin}], self.use_multi_admin, exp_revert=True)

            self.execute_fn(self.competition, self.competition.updateKey, [key_hash, new_key_hash, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            verify(new_key_hash, self.competition.getKeyHash(challenge_number).hex())

            # Update deadlines
            new_deadlines = [getTimestamp(), getTimestamp(), getTimestamp(), getTimestamp()]
            new_ddline_indices = random.sample(list(range(50)), 4)

            for i in range(4):
                self.execute_fn(self.competition, self.competition.updateDeadlines, [challenge_number, new_ddline_indices[i], new_deadlines[i], {'from': self.admin}], self.use_multi_admin, exp_revert=False)

            for i in range(4):
                verify(new_deadlines[i], self.competition.getDeadlines(challenge_number, new_ddline_indices[i]))

            # test new staking and submissions logic
            p = random.choice(participants)

            if self.competition.getStake(p) != 0:
                self.execute_fn(self.token, self.token.setStake, [self.competition, 0, {'from': p}], use_multi_admin=False, exp_revert=False)

            # Should not be able to withdraw beyond current stake.
            self.execute_fn(self.token, self.token.decreaseStake, [self.competition, 1, {'from': p}], use_multi_admin=False, exp_revert=True)

            stake_threshold = self.competition.getStakeThreshold()
            verify(bytes([0] * 32).hex(), self.competition.getSubmission(challenge_number, p).hex())

            self.execute_fn(self.competition, self.competition.submitNewPredictions, [getHash(), {'from': p}], use_multi_admin=False, exp_revert=True)
                # submitNewPrediction 0, 0, 0

            self.execute_fn(self.competition, self.competition.updateSubmission, [ self.competition.getSubmission(challenge_number, p).hex(), getHash(), {'from': p}], use_multi_admin=False, exp_revert=True)
                # updateSubmission 0, 0, 0

            self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold, {'from': p}], use_multi_admin=False, exp_revert=False)
            # increaseStake 0, 0, 1

            self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold - 1, {'from': p}], use_multi_admin=False, exp_revert=False)
            # decreaseStake 1, 0, 1

            self.execute_fn(self.token, self.token.setStake, [self.competition, 0, {'from': p}], use_multi_admin=False, exp_revert=False)
            # decreaseStake 0, 0, 1

            self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold, {'from': p}], use_multi_admin=False, exp_revert=False)
            self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold + 1, {'from': p}], use_multi_admin=False, exp_revert=False)
            # increaseStake 1, 0, 1

            self.execute_fn(self.competition, self.competition.updateSubmission, [self.competition.getSubmission(challenge_number, p).hex(), getHash(), {'from': p}], use_multi_admin=False, exp_revert=True)
            # updateSubmission 1, 0, 0

            self.execute_fn(self.competition, self.competition.submitNewPredictions, [getHash(), {'from': p}], use_multi_admin=False, exp_revert=False)
            # submitNewPrediction 1, 0, 1

            self.execute_fn(self.competition, self.competition.submitNewPredictions, [getHash(), {'from': p}], use_multi_admin=False, exp_revert=True)
                # submitNewPrediction 1, 1, 0

            self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold + 2, {'from': p}], use_multi_admin=False, exp_revert=False)
            # increaseStake 1, 1, 1

            self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold, {'from': p}], use_multi_admin=False, exp_revert=False)
            # decreaseStake 1, 1, 1 final stake >= threshold

            self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold - 1, {'from': p}], use_multi_admin=False, exp_revert=True)
                # decreaseStake 1, 1, 0 final stake < threshold

            self.execute_fn(self.competition, self.competition.updateSubmission, [self.competition.getSubmission(challenge_number, p.address).hex(), getHash(), {'from': p}], use_multi_admin=False, exp_revert=False)
            # updateSubmission 1, 1, 1

            ## Withdraw
            length_of_submitters = self.competition.getSubmissionCounter(challenge_number)
            self.execute_fn(self.competition, self.competition.updateSubmission, [self.competition.getSubmission(challenge_number, p.address).hex(), bytes([0] * 32), {'from': p}], use_multi_admin=False, exp_revert=False)
            new_length_of_submitters = self.competition.getSubmissionCounter(challenge_number)
            verify(length_of_submitters, new_length_of_submitters + 1)

            stakers = getRandomSelection(participants, min_num=len(participants) * 3 // 4)

            # Increase Stake
            for i in range(len(stakers)):
                p = stakers[i]
                p_bal = self.token.balanceOf(p)
                if p_bal > 1:
                    stake_amount = random.randint(1, p_bal)

                    if random.choice([True, False]):
                        self.execute_fn(self.token, self.token.setStake, [self.competition, stake_amount, {'from': p}], use_multi_admin=False, exp_revert=False)
                        assert self.competition.getStake(p) == stake_amount == self.token.getStake(
                            self.competition, p)
                    else:
                        current_stake = self.competition.getStake(p)
                        self.execute_fn(self.competition, self.competition.increaseStake, [p, stake_amount, {'from': p}], use_multi_admin=False, exp_revert=True)
                        self.execute_fn(self.token, self.token.increaseStake, [self.competition, stake_amount, {'from': p}], use_multi_admin=False, exp_revert=False)
                        assert self.competition.getStake(p) == (current_stake + stake_amount) == self.token.getStake(
                            self.competition, p)

            # Decrease Stake
            random_stakers = getRandomSelection(stakers)

            for i in range(len(random_stakers)):
                p = random_stakers[i]
                staked = self.competition.getStake(p)
                decrease_amt = random.randint(0, staked)

                if random.choice([True, False]):
                    self.execute_fn(self.token, self.token.setStake, [self.competition, decrease_amt, {'from': p}],
                                    use_multi_admin=False, exp_revert=False)
                    assert self.competition.getStake(p) == decrease_amt == self.token.getStake(
                        self.competition, p)
                else:
                    current_stake = self.competition.getStake(p)
                    self.execute_fn(self.competition, self.competition.decreaseStake, [p, stake_amount, {'from': p}],
                                    use_multi_admin=False, exp_revert=True)
                    self.execute_fn(self.token, self.token.decreaseStake, [self.competition, decrease_amt, {'from': p}],
                                    use_multi_admin=False, exp_revert=False)
                    assert self.competition.getStake(p) == (
                            current_stake - decrease_amt) == self.token.getStake(self.competition, p)
            # Send Submission
            submitters = getRandomSelection(stakers, min_num=len(stakers) * 9 // 10)
            actual_submitted = set()

            for p in submitters:
                staked = self.competition.getStake(p)
                self.competition.getDatasetHash(challenge_number)
                if staked >= stake_threshold:
                    new_submission = getHash()
                    self.execute_fn(self.competition, self.competition.submitNewPredictions, [new_submission, {'from': p}], use_multi_admin=False, exp_revert=False)
                    verify(self.competition.getStake(p), self.competition.getStakedAmountForChallenge(
                        challenge_number, p))
                    actual_submitted.add(p)

                    self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold - 1, {'from': p}], use_multi_admin=False, exp_revert=True)
                    self.execute_fn(self.token, self.token.decreaseStake, [self.competition, self.token.getStake(self.competition, p) - stake_threshold + 1, {'from': p}], use_multi_admin=False, exp_revert=True)
                else:
                    self.execute_fn(self.competition, self.competition.submitNewPredictions, [getHash(), {'from': p}], use_multi_admin=False, exp_revert=True)

            # Update Submission
            for p in participants:
                submission = self.competition.getSubmission(challenge_number, p)
                if int(submission.hex(), 16) != 0:
                    if random.choice([True, False]):
                        self.execute_fn(self.competition, self.competition.updateSubmission, [submission, getHash(), {'from': p}], use_multi_admin=False, exp_revert=False)
                        verify(self.competition.getStake(p), self.competition.getStakedAmountForChallenge(
                            challenge_number, p))
                        self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold - 1, {'from': p}], use_multi_admin=False, exp_revert=True)
                        self.execute_fn(self.token, self.token.decreaseStake, [self.competition, self.token.getStake(self.competition, p) - stake_threshold + 1, {'from': p}], use_multi_admin=False, exp_revert=True)
                    else:
                        # Withdraw
                        self.execute_fn(self.competition, self.competition.updateSubmission, [submission, bytes([0] * 32), {'from': p}], use_multi_admin=False, exp_revert=False)
                        verify(0, self.competition.getStakedAmountForChallenge(
                            challenge_number, p))
                        actual_submitted.remove(p)

                        # should be able to withdraw entire stake at this point
                        self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold - 1, {'from': p}], use_multi_admin=False, exp_revert=False)
                        self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold, {'from': p}], use_multi_admin=False, exp_revert=False)
                        self.execute_fn(self.token, self.token.decreaseStake, [self.competition, self.token.getStake(self.competition, p), {'from': p}], use_multi_admin=False, exp_revert=False)
                else:
                    self.execute_fn(self.competition, self.competition.updateSubmission, [submission, getHash(), {'from': p}], use_multi_admin=False, exp_revert=True)

            # Verify stake record
            for p in participants:
                submission = self.competition.getSubmission(challenge_number, p)
                if int(submission.hex(), 16) != 0:
                    recorded_stake = self.competition.getStake(p)
                    recorded_stake_b = self.token.getStake(self.competition, p)
                    recorded_stake_c = self.competition.getStakedAmountForChallenge(challenge_number, p)

                    assert recorded_stake == recorded_stake_b == recorded_stake_c, '{} : {} : {}'.format(
                        recorded_stake,
                        recorded_stake_b,
                        recorded_stake_c)
                else:
                    verify(0, self.competition.getStakedAmountForChallenge(challenge_number, p))

            # Increase Stake should still work at this point regardless of submission
            for p in participants:
                p_bal = self.token.balanceOf(p)
                p_stake = self.competition.getStake(p)
                if p_bal > 1:
                    if random.choice([True, False]):
                        stake_amount = random.randint(p_stake + 1, p_stake + p_bal)
                        self.execute_fn(self.token, self.token.setStake, [self.competition, stake_amount, {'from': p}], use_multi_admin=False, exp_revert=False)
                        assert self.competition.getStake(p) == stake_amount == self.token.getStake(
                            self.competition, p)
                        submission = self.competition.getSubmission(challenge_number, p)
                        if int(submission.hex(), 16) != 0:
                            verify(self.competition.getStake(p), self.competition.getStakedAmountForChallenge(
                                challenge_number, p))
                    else:
                        stake_amount = random.randint(1, p_bal)
                        current_stake = self.competition.getStake(p)
                        self.execute_fn(self.competition, self.competition.increaseStake, [p, stake_amount, {'from': p}], use_multi_admin=False, exp_revert=True)
                        self.execute_fn(self.token, self.token.increaseStake, [self.competition, stake_amount, {'from': p}], use_multi_admin=False, exp_revert=False)
                        assert self.competition.getStake(p) == (
                                current_stake + stake_amount) == self.token.getStake(
                            self.competition, p)
                        submission = self.competition.getSubmission(challenge_number, p)
                        if int(submission.hex(), 16) != 0:
                            assert self.competition.getStake(p) == self.competition.getStakedAmountForChallenge(
                                challenge_number, p)

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

            #############################
            ########## PHASE 2 ##########
            #############################
            self.execute_fn(self.competition, self.competition.closeSubmission, [{'from': self.admin}], self.use_multi_admin, exp_revert=False)
            verify(2, self.competition.getPhase(challenge_number))

            self.staking_restricted_check(non_admin=participants[-1])

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

            # Verify total stakes of submitters
            total_stakes = 0
            total_recorded_stakes = 0
            for s in actual_submitted:
                total_stakes += self.competition.getStake(s)
                total_recorded_stakes += self.competition.getStakedAmountForChallenge(challenge_number, s)
            verify(total_stakes, total_recorded_stakes)

            self.unauthorized_calls_check(non_admin=participants[-1], admin=self.admin)

            # Test authorized actions expected to fail
            s = random.choice(list(actual_submitted))
            self.execute_fn(self.token, self.token.increaseStake, [self.competition, 1, {'from': s}],
                            use_multi_admin=False, exp_revert=True)
            self.execute_fn(self.token, self.token.decreaseStake, [self.competition, 1, {'from': s}],
                            use_multi_admin=False, exp_revert=True)
            self.execute_fn(self.competition, self.competition.submitNewPredictions, [getHash(), {'from': self.admin}],
                            use_multi_admin=False, exp_revert=True)
            self.execute_fn(self.competition, self.competition.updateSubmission,
                            [self.competition.getSubmission(challenge_number, p), getHash(), {'from': s}],
                            use_multi_admin=False, exp_revert=True)
            self.execute_fn(self.competition, self.competition.openChallenge,
                            [getHash(), getHash(), getTimestamp(), getTimestamp(), {'from': self.admin}],
                            self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.updateDataset,
                            [self.competition.getDatasetHash(challenge_number), getHash(), {'from': self.admin}],
                            self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.updateKey,
                            [self.competition.getKeyHash(challenge_number), getHash(), {'from': self.admin}],
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

            #############################
            ########## PHASE 3 ##########
            #############################
            p = submitters[0]
            self.execute_fn(self.competition, self.competition.advanceToPhase, [3, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            verify(3, self.competition.getPhase(challenge_number))
            challenge_number = self.competition.getLatestChallengeNumber()

            self.unauthorized_calls_check(non_admin=participants[-1], admin=self.admin)

            # Test authorized actions expected to fail
            s = random.choice(list(actual_submitted))
            self.execute_fn(self.competition, self.competition.submitNewPredictions, [getHash(), {'from': self.admin}],
                            use_multi_admin=False, exp_revert=True)
            self.execute_fn(self.competition, self.competition.updateSubmission,
                            [self.competition.getSubmission(challenge_number, p), getHash(), {'from': s}],
                            use_multi_admin=False, exp_revert=True)
            self.execute_fn(self.competition, self.competition.openChallenge,
                            [getHash(), getHash(), getTimestamp(), getTimestamp(), {'from': self.admin}],
                            self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.updateDataset,
                            [self.competition.getDatasetHash(challenge_number), getHash(), {'from': self.admin}],
                            self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.updateKey,
                            [self.competition.getKeyHash(challenge_number), getHash(), {'from': self.admin}],
                            self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.closeSubmission, [{'from': self.admin}],
                            self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.advanceToPhase, [3, {'from': self.admin}],
                            self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.moveRemainderToPool, [{'from': self.admin}],
                            self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.sponsor, [1, {'from': self.admin}], self.use_multi_admin,
                            exp_revert=True)

            results_hash = getHash()
            self.execute_fn(self.competition, self.competition.submitResults, [results_hash, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            verify(results_hash, self.competition.getResultsHash(challenge_number).hex())

            new_results_hash = getHash()
            self.execute_fn(self.competition, self.competition.updateResults, [results_hash, new_results_hash, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            verify(new_results_hash, self.competition.getResultsHash(challenge_number).hex())

            # make rewards payment
            staking_rewards_budget = self.competition.getCurrentStakingRewardsBudget()
            challenge_rewards_budget = self.competition.getCurrentChallengeRewardsBudget()
            tournament_rewards_budget = self.competition.getCurrentTournamentRewardsBudget()

            awardees = getRandomSelection(submitters, min_num=len(submitters) * 1 // 2)
            winners = []
            staking_rewards = []
            challenge_rewards = []
            tournament_rewards = []
            challenge_scores = []
            tournament_scores = []
            proportion = random.randint(0, 95)
            rand_ceil = 95 - proportion
            for a in awardees[:-1]:
                winners.append(a)
                staking_rewards.append(int(proportion * staking_rewards_budget // 100))
                challenge_rewards.append(int(proportion * challenge_rewards_budget // 100))
                tournament_rewards.append(int(proportion * tournament_rewards_budget // 100))
                challenge_scores.append(int(random.random() * 1e18))
                tournament_scores.append(int(random.random() * 1e18))
                proportion = random.randint(0, rand_ceil)
                rand_ceil = rand_ceil - proportion

            winners.append(awardees[-1])
            total_rewards = sum(staking_rewards)
            staking_rewards.append(int(staking_rewards_budget - total_rewards))
            total_rewards = sum(challenge_rewards)
            challenge_rewards.append(int(challenge_rewards_budget - total_rewards))
            total_rewards = sum(tournament_rewards)
            tournament_rewards.append(int(tournament_rewards_budget - total_rewards))
            challenge_scores.append(int(random.random() * 1e18))
            tournament_scores.append(int(random.random() * 1e18))

            self.execute_fn(self.competition, self.competition.payRewards, [winners[:-1], staking_rewards, challenge_rewards, tournament_rewards, {'from': self.admin}], self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.payRewards, [winners, staking_rewards, challenge_rewards, tournament_rewards, {'from': self.admin}], self.use_multi_admin, exp_revert=False)

            self.execute_fn(self.competition, self.competition.updateChallengeAndTournamentScores, [challenge_number, winners[:-1], challenge_scores, tournament_scores, {'from': self.admin}], self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.updateChallengeAndTournamentScores, [challenge_number, winners, challenge_scores, tournament_scores, {'from': self.admin}], self.use_multi_admin, exp_revert=False)

            for i in range(len(winners)):
                verify(staking_rewards[i], self.competition.getStakingRewards(challenge_number, winners[i]))
                verify(challenge_rewards[i], self.competition.getChallengeRewards(challenge_number, winners[i]))
                verify(tournament_rewards[i], self.competition.getTournamentRewards(challenge_number, winners[i]))
                verify(staking_rewards[i] + challenge_rewards[i] + tournament_rewards[i],
                       self.competition.getOverallRewards(challenge_number, winners[i]))
                verify(challenge_scores[i], self.competition.getChallengeScores(challenge_number, winners[i]))
                verify(tournament_scores[i], self.competition.getTournamentScores(challenge_number, winners[i]))

            #############################
            ########## PHASE 4 ##########
            #############################
            self.execute_fn(self.competition, self.competition.advanceToPhase, [4, {'from': self.admin}], self.use_multi_admin, exp_revert=False)

            self.unauthorized_calls_check(non_admin=participants[-1], admin=self.admin)

            # Test authorized actions expected to fail
            s = random.choice(list(actual_submitted))
            self.execute_fn(self.competition, self.competition.submitNewPredictions, [getHash(), {'from': self.admin}],
                            use_multi_admin=False, exp_revert=True)
            self.execute_fn(self.competition, self.competition.updateSubmission,
                            [self.competition.getSubmission(challenge_number, p), getHash(), {'from': s}],
                            use_multi_admin=False, exp_revert=True)
            self.execute_fn(self.competition, self.competition.updateDataset,
                            [self.competition.getDatasetHash(challenge_number), getHash(), {'from': self.admin}],
                            self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.updateKey,
                            [self.competition.getKeyHash(challenge_number), getHash(), {'from': self.admin}],
                            self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.closeSubmission, [{'from': self.admin}],
                            self.use_multi_admin, exp_revert=True)
            self.execute_fn(self.competition, self.competition.advanceToPhase, [4, {'from': self.admin}],
                            self.use_multi_admin, exp_revert=True)

            verify(4, self.competition.getPhase(challenge_number))

            priv_key = getHash()
            self.execute_fn(self.competition, self.competition.updatePrivateKey, [challenge_number, priv_key, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            verify(priv_key, self.competition.getPrivateKeyHash(challenge_number).hex())

            message = str(getHash())
            self.execute_fn(self.competition, self.competition.updateMessage, [message, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            verify(message, self.competition.getMessage())

            new_rewards_threshold = random.randint(int(Decimal('100e18')), int(Decimal('10000e18')))
            new_stake_threshold = random.randint(int(Decimal('0.1e18')), int(Decimal('100e18')))
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

            verify(total_stake, self.competition.getCurrentTotalStaked())

            competition_pool = self.competition.getCompetitionPool()
            verify(0, self.competition.getRemainder())
            verify(self.token.balanceOf(self.competition),
                   self.competition.getCompetitionPool() + self.competition.getCurrentTotalStaked() + self.competition.getRemainder())

            # should revert since no remainder to move
            self.execute_fn(self.competition, self.competition.moveRemainderToPool, [{'from': self.admin}], self.use_multi_admin, exp_revert=True)

            if not self.use_multi_admin:
                admin_bal = self.token.balanceOf(self.admin)
            else:
                admin_bal = self.token.balanceOf(self.multi_sig)

            transfer_amount = int(0.001 * admin_bal)
            self.execute_fn(self.token, self.token.transfer, [self.competition, transfer_amount, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            verify(transfer_amount, self.competition.getRemainder())
            verify(self.token.balanceOf(self.competition),
                   self.competition.getCompetitionPool() + self.competition.getCurrentTotalStaked() + self.competition.getRemainder())

            self.execute_fn(self.competition, self.competition.moveRemainderToPool, [{'from': self.admin}], self.use_multi_admin, exp_revert=False)
            verify(0, self.competition.getRemainder())
            verify(self.token.balanceOf(self.competition),
                   self.competition.getCompetitionPool() + self.competition.getCurrentTotalStaked() + self.competition.getRemainder())
            verify(competition_pool + transfer_amount, self.competition.getCompetitionPool())
