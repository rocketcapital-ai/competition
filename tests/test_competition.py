from utils_for_testing import *
from brownie import Token, Competition, reverts, accounts


class TestCompetition:
    def setup(self):
        self.num_rounds = 5
        self.use_multi_admin = False
        self.admin = accounts[0]
        self.participants = accounts[1:]
        self.token = Token.deploy("RockCap Token", "RCP", int(Decimal('100000000e18')), {'from': self.admin})
        self.competition = Competition.deploy({'from': self.admin})
        self.stake_amt_history = {}
        self.staker_set_history = {}
        self.fork = False

        # airdrop to participants
        total_airdrop = int(Decimal(0.01) * Decimal(self.token.totalSupply()))
        single_airdrop = total_airdrop // (len(accounts) - 1)
        for i in range(len(self.participants)):
            self.execute_fn(self.token, self.token.transfer,
                            [self.participants[i], single_airdrop, {'from': self.admin}],
                            self.use_multi_admin, exp_revert=False)

        stake_threshold = int(Decimal('1000e18'))
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

    def staking_restricted_check(self, sender):
        self.execute_fn(self.competition, self.competition.increaseStake, [sender, 1, {'from': sender}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.decreaseStake, [sender, 1, {'from': sender}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.token, self.token.increaseStake, [self.competition, 1, {'from': sender}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.token, self.token.decreaseStake, [self.competition, 1, {'from': sender}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.token, self.token.setStake, [self.competition, 1, {'from': sender}], use_multi_admin=False, exp_revert=True)

    def staking_backing_submissions_restricted_check(self, sender, backed_participant):
        self.staking_restricted_check(sender)
        self.execute_fn(self.competition, self.competition.submitNewPredictions, [getHash(),  {'from': sender}], use_multi_admin=False, exp_revert=True)
        challenge_number = self.competition.getLatestChallengeNumber()
        old_submission_hash = self.competition.getSubmission(challenge_number, sender)
        self.execute_fn(self.competition, self.competition.updateSubmission, [old_submission_hash, getHash(),  {'from': sender}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.updateBackedParticipant, [backed_participant,  {'from': sender}], use_multi_admin=False, exp_revert=True)

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

        self.execute_fn(self.competition, self.competition.updateChallengeOpenedBlockNumbers, [1, 1, {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.updateSubmissionClosedBlockNumbers, [1, 1, {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.updateStakerSet, [[non_admin], [admin], {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.updateHistoricalStakedAmounts, [1, [], [], {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.recordStakes, [0, 1, {'from': non_admin}], use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.alignBacking, [[admin], {'from': non_admin}], use_multi_admin=False, exp_revert=True)

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


    def test_full_run(self):
        self.execute_fn(self.competition, self.competition.initialize, [int(Decimal('10e18')), int(Decimal('10e18')), self.token, {'from': self.admin}], self.use_multi_admin, exp_revert=True)

        participants = self.participants
        cn = self.competition.getLatestChallengeNumber()
        current_phase = self.competition.getPhase(cn)

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
        for challenge_round in range(self.num_rounds):
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

            if self.fork:
                self.verify_backed_participants_for_self()
                self.verify_historical_staked_amounts()

            #############################
            ########## PHASE 1 ##########
            #############################

            dataset_hash = getHash()
            key_hash = getHash()
            self.execute_fn(self.competition, self.competition.openChallenge, [dataset_hash, key_hash, getTimestamp(), getTimestamp(), {'from': self.admin}], self.use_multi_admin, exp_revert=False)

            challenge_number = self.competition.getLatestChallengeNumber()
            challenge_history.append(challenge_number)
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

            p = participants[-1]
            p2 = participants[-2]
            p3 = participants[-3]

            assert p != p2 and p != p3, 'Not enough accounts! Please re-run the test with more accounts initialized.'

            # test backing logic
            self.backing_test(p, p2, p3)


            # test new staking and submissions logic

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

            self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold - 1, {'from': p}], use_multi_admin=False, exp_revert=True)
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
            stake_threshold = self.competition.getStakeThreshold()
            # Increase Stake
            for i in range(len(stakers)):
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

            for i in range(len(random_stakers)):
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
                    current_stake = self.competition.getStake(p)
                    self.execute_fn(self.competition, self.competition.decreaseStake, [p, stake_amount, {'from': p}],
                                    use_multi_admin=False, exp_revert=True)
                    self.execute_fn(self.token, self.token.decreaseStake, [self.competition, decrease_amt, {'from': p}],
                                    use_multi_admin=False, exp_revert=(staked-decrease_amt) < stake_threshold)
                    if (staked-decrease_amt) >= stake_threshold :
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
                        self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold - 1, {'from': p}], use_multi_admin=False, exp_revert=True)
                        self.execute_fn(self.token, self.token.decreaseStake, [self.competition, self.token.getStake(self.competition, p) - stake_threshold + 1, {'from': p}], use_multi_admin=False, exp_revert=True)
                    else:
                        # Withdraw
                        self.execute_fn(self.competition, self.competition.updateSubmission, [submission, bytes([0] * 32), {'from': p}], use_multi_admin=False, exp_revert=False)
                        actual_submitted.remove(p)

                        # should be able to withdraw entire stake at this point
                        self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold - 1, {'from': p}], use_multi_admin=False, exp_revert=True)
                        self.execute_fn(self.token, self.token.setStake, [self.competition, stake_threshold, {'from': p}], use_multi_admin=False, exp_revert=False)
                        self.execute_fn(self.token, self.token.decreaseStake, [self.competition, self.token.getStake(self.competition, p), {'from': p}], use_multi_admin=False, exp_revert=False)
                else:
                    self.execute_fn(self.competition, self.competition.updateSubmission, [submission, getHash(), {'from': p}], use_multi_admin=False, exp_revert=True)

            # Verify stake record
            for p in participants:
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

            #############################
            ########## PHASE 2 ##########
            #############################
            self.execute_fn(self.competition, self.competition.closeSubmission, [{'from': self.admin}], self.use_multi_admin, exp_revert=False)
            verify(2, self.competition.getPhase(challenge_number))
            self.execute_fn(self.competition, self.competition.recordStakes,
                            [0, 1, {'from': self.participants[-1]}], self.use_multi_admin, exp_revert=True)
            staker_list = self.competition.getAllStakers()
            recorded_stakes = self.competition.getHistoricalStakeAmounts(challenge_number, staker_list)
            verify(0, sum(recorded_stakes))
            chunk = 5
            for i in range(0, len(staker_list), chunk):
                if (i+chunk) > len(staker_list):
                    end_index = len(staker_list)
                else:
                    end_index = i + chunk
                self.execute_fn(self.competition, self.competition.recordStakes, [i, end_index, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            self.execute_fn(self.competition, self.competition.recordStakes,
                            [0, len(staker_list) + 1, {'from': self.admin}], self.use_multi_admin, exp_revert=True)

            self.stake_amt_history[challenge_number] = {}
            for s in staker_list:
                self.stake_amt_history[challenge_number][s] = self.competition.getStake(s)
                verify(self.competition.getStake(s), self.competition.getHistoricalStakeAmounts(challenge_number, [s])[0])
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

            self.staking_backing_submissions_restricted_check(participants[-1], participants[-2])

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
            self.staking_backing_submissions_restricted_check(participants[-1], participants[-2])
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
            self.staking_backing_submissions_restricted_check(participants[-1], participants[-2])
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

            verify(total_stake, self.competition.getCurrentTotalStaked() - existing_stake)

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

            transfer_amount = admin_bal // 1000
            self.execute_fn(self.token, self.token.transfer, [self.competition, transfer_amount, {'from': self.admin}], self.use_multi_admin, exp_revert=False)
            verify(transfer_amount, self.competition.getRemainder())
            verify(self.token.balanceOf(self.competition),
                   self.competition.getCompetitionPool() + self.competition.getCurrentTotalStaked() + self.competition.getRemainder())

            self.execute_fn(self.competition, self.competition.moveRemainderToPool, [{'from': self.admin}], self.use_multi_admin, exp_revert=False)
            verify(0, self.competition.getRemainder())
            verify(self.token.balanceOf(self.competition),
                   self.competition.getCompetitionPool() + self.competition.getCurrentTotalStaked() + self.competition.getRemainder())
            verify(competition_pool + transfer_amount, self.competition.getCompetitionPool())

            for cn in challenge_history:
                verify(self.staker_set_history[cn], set(self.competition.getHistoricalStakers(cn)))
                for s in self.staker_set_history[cn]:
                    verify(self.stake_amt_history[cn][s], self.competition.getHistoricalStakeAmounts(cn, [s])[0])

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

        self.execute_fn(self.competition, self.competition.submitNewPredictions, [getHash(), {'from': p}],
                        use_multi_admin=False, exp_revert=True)
        # submitNewPrediction 0, 0, 0

        self.execute_fn(self.competition, self.competition.updateSubmission,
                        [self.competition.getSubmission(challenge_number, p).hex(), getHash(), {'from': p}],
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

        self.execute_fn(self.competition, self.competition.updateSubmission,
                        [self.competition.getSubmission(challenge_number, p).hex(), getHash(), {'from': p}],
                        use_multi_admin=False, exp_revert=True)
        # updateSubmission 1, 0, 0

        self.execute_fn(self.competition, self.competition.submitNewPredictions, [getHash(), {'from': p}],
                        use_multi_admin=False, exp_revert=False)
        # submitNewPrediction 1, 0, 1

        self.execute_fn(self.competition, self.competition.submitNewPredictions, [getHash(), {'from': p}],
                        use_multi_admin=False, exp_revert=True)
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

        self.execute_fn(self.competition, self.competition.updateSubmission,
                        [self.competition.getSubmission(challenge_number, p.address).hex(), getHash(), {'from': p}],
                        use_multi_admin=False, exp_revert=False)
        # updateSubmission 1, 1, 1

        ## Withdraw
        length_of_submitters = self.competition.getSubmissionCounter(challenge_number)
        self.execute_fn(self.competition, self.competition.updateSubmission,
                        [self.competition.getSubmission(challenge_number, p.address).hex(), bytes([0] * 32),
                         {'from': p}], use_multi_admin=False, exp_revert=False)
        new_length_of_submitters = self.competition.getSubmissionCounter(challenge_number)
        verify(length_of_submitters, new_length_of_submitters + 1)

    def backing_test(self, participant, backed_participant, backed_participant_2):
        # Allowable states.
        # State 0: Stake 0, Submission 0, Backed 0
        # State 1: Stake 1, Submission 0, Backed 0
        # State 2: Stake 1, Submission 1, Backed 0
        # State 3: Stake 1, Submission 0, Backed 1
        # State 4: Stake 1, Submission 1, Backed 1

        # Initialize to State 0
        ###########
        # STATE 0 #
        ###########
        challenge_number = self.competition.getLatestChallengeNumber()
        current_submission = self.competition.getSubmission(challenge_number, participant).hex()
        if int(current_submission, 16) != 0:
            self.execute_fn(self.competition, self.competition.updateSubmission,
                            [self.competition.getSubmission(challenge_number, participant).hex(), (0).to_bytes(32, 'big'),
                             {'from': participant}],
                            use_multi_admin=False, exp_revert=False)
        if (self.competition.getBackedParticipant(participant) != '0x'+('0'*40)) and (self.competition.getBackedParticipant(participant) != participant):
            self.execute_fn(self.competition, self.competition.updateBackedParticipant,
                            [participant,
                             {'from': participant}],
                            use_multi_admin=False, exp_revert=False)
        if self.competition.getStake(participant) > 0:
            self.execute_fn(self.token, self.token.setStake,
                            [self.competition, 0,
                             {'from': participant}],
                            use_multi_admin=False, exp_revert=False)

        # should fail
        self.execute_fn(self.competition, self.competition.submitNewPredictions,
                        [getHash(),
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.updateSubmission,
                        [self.competition.getSubmission(challenge_number, participant).hex(), getHash(),
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=True)
        self.execute_fn(self.competition, self.competition.updateBackedParticipant,
                        [backed_participant,
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=True)
        # increase stake by an amount less than the threshold. Should fail.
        if (self.competition.getStake(participant) + 1) < self.competition.getStakeThreshold():
            self.execute_fn(self.token, self.token.setStake,
                            [self.competition, 1,
                             {'from': participant}],
                            use_multi_admin=False, exp_revert=True)

        # Move from state 0 to state 1: Increase Stake
        current_backer_set = set(self.competition.getAllBackers(participant))
        self.execute_fn(self.token, self.token.setStake,
                        [self.competition, self.competition.getStakeThreshold(),
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)
        new_backer_set = set(self.competition.getAllBackers(participant))
        delta = list(new_backer_set - current_backer_set)
        assert 1 == len(delta)
        assert participant == self.competition.getBackedParticipant(participant), 'Default participant incorrect. Exp {} got {}'.format(participant, self.competition.getBackedParticipant(participant))
        assert participant == delta[0], 'Default backers incorrect. Exp {} got {}'.format(participant, delta[0])

        ###########
        # STATE 1 #
        ###########
        # Move from State 1 to State 2: Add submission.
        current_backer_set = set(self.competition.getAllBackers(participant))
        current_backed = self.competition.getBackedParticipant(participant)
        self.execute_fn(self.competition, self.competition.submitNewPredictions,
                        [getHash(),
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)
        new_backer_set = set(self.competition.getAllBackers(participant))
        new_backed = self.competition.getBackedParticipant(participant)
        assert participant == self.competition.getBackedParticipant(
            participant), 'Default participant incorrect. Exp {} got {}'.format(participant,
                                                                                self.competition.getBackedParticipant(
                                                                                    participant))
        assert current_backer_set == new_backer_set
        assert current_backed == new_backed

        ###########
        # STATE 2 #
        ###########
        # should fail
        # Try to remove stake when in state 2
        self.execute_fn(self.token, self.token.setStake,
                        [self.competition, 0,
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=True)

        # Move from state 2 to state 2: Change stake but remain above threshold.
        self.execute_fn(self.token, self.token.setStake,
                        [self.competition, self.competition.getStakeThreshold() + 3,
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)

        # Move from state 2 to state 2: Update submission.
        current_backer_set = self.competition.getAllBackers(participant)
        current_backed = self.competition.getBackedParticipant(participant)
        self.execute_fn(self.competition, self.competition.updateSubmission,
                        [self.competition.getSubmission(challenge_number, participant).hex(), getHash(),
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)
        new_backer_set = self.competition.getAllBackers(participant)
        new_backed = self.competition.getBackedParticipant(participant)
        assert participant == self.competition.getBackedParticipant(
            participant), 'Default participant incorrect. Exp {} got {}'.format(participant,
                                                                                self.competition.getBackedParticipant(
                                                                                    participant))
        assert new_backer_set == current_backer_set
        assert current_backed == new_backed

        # Move from state 2 to state 2: Increase Stake
        self.execute_fn(self.token, self.token.increaseStake,
                        [self.competition, 1,
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)

        # Move from state 2 to state 2: Decrease Stake
        self.execute_fn(self.token, self.token.decreaseStake,
                        [self.competition, 1,
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)

        # Move from state 2 to state 4: Bet on other participant.
        current_backer_set = set(self.competition.getAllBackers(backed_participant))
        self.execute_fn(self.competition, self.competition.updateBackedParticipant,
                        [backed_participant,
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)
        assert backed_participant == self.competition.getBackedParticipant(
            participant), 'New backed participant incorrect. Exp {} got {}'.format(backed_participant,
                                                                                self.competition.getBackedParticipant(
                                                                                    participant))
        new_backer_set = set(self.competition.getAllBackers(backed_participant))
        delta = list(new_backer_set - current_backer_set)
        assert 1 == len(delta), 'Backer set delta incorrect. Exp {} got {}'.format(1, delta)
        assert participant == delta[0], 'New backers incorrect. Exp {} got {}'.format(participant,
                                                                  delta[0])

        ###########
        # STATE 4 #
        ###########
        # should fail
        # Try to remove stake when in state 4
        self.execute_fn(self.token, self.token.setStake,
                        [self.competition, 0,
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=True)

        # Try to transfer backing to current.
        self.execute_fn(self.competition, self.competition.updateBackedParticipant,
                        [backed_participant,
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=True)

        # Move from state 4 to state 4: Update submission.
        self.execute_fn(self.competition, self.competition.updateSubmission,
                        [self.competition.getSubmission(challenge_number, participant).hex(), getHash(),
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)

        # Move from state 4 to state 4: Change stake.
        self.execute_fn(self.token, self.token.setStake,
                        [self.competition, self.competition.getStakeThreshold() + 5,
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)

        # Move from state 4 to state 4: Change backed participant.
        self.execute_fn(self.competition, self.competition.updateBackedParticipant,
                        [backed_participant_2,
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)

        # Move from state 4 to state 2: Change backed participant to self.
        self.execute_fn(self.competition, self.competition.updateBackedParticipant,
                        [participant,
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)

        # Move from state 2 back to state 1: Remove submission
        self.execute_fn(self.competition, self.competition.updateSubmission,
                        [self.competition.getSubmission(challenge_number, participant).hex(), (0).to_bytes(32, 'big'),
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)

        # Move from state 1 to state 3: Bet on other participant.
        self.execute_fn(self.competition, self.competition.updateBackedParticipant,
                        [backed_participant,
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)
        ###########
        # STATE 3 #
        ###########
        # should fail
        # Try to remove stake when in state 3
        self.execute_fn(self.token, self.token.setStake,
                        [self.competition, 0,
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=True)

        # Try to update submission when in state 3
        self.execute_fn(self.competition, self.competition.updateSubmission,
                        [self.competition.getSubmission(challenge_number, participant).hex(), getHash(),
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=True)

        # Move from state 3 to state 3: Update backed participant
        self.execute_fn(self.competition, self.competition.updateBackedParticipant,
                        [backed_participant_2,
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)

        # Move from state 3 to state 3: Increase Stake
        self.execute_fn(self.token, self.token.increaseStake,
                        [self.competition, 1,
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)

        # Move from state 3 to state 3: Decrease Stake
        self.execute_fn(self.token, self.token.decreaseStake,
                        [self.competition, 1,
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)

        # Move from state 3 to state 4: Send submission.
        current_backer_set = self.competition.getAllBackers(participant)
        current_backed = self.competition.getBackedParticipant(participant)
        self.execute_fn(self.competition, self.competition.submitNewPredictions,
                        [getHash(),
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)
        new_backer_set = self.competition.getAllBackers(participant)
        new_backed = self.competition.getBackedParticipant(participant)
        assert new_backer_set == current_backer_set
        assert current_backed == new_backed

        ###########
        # STATE 4 #
        ###########
        # should fail
        # Try to remove stake when in state 4
        self.execute_fn(self.token, self.token.setStake,
                        [self.competition, 0,
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=True)

        # Try to transfer backing to current.
        self.execute_fn(self.competition, self.competition.updateBackedParticipant,
                        [backed_participant_2,
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=True)

        # Move from state 4 to state 4: Update submission.
        self.execute_fn(self.competition, self.competition.updateSubmission,
                        [self.competition.getSubmission(challenge_number, participant).hex(), getHash(),
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)

        # Move from state 4 to state 4: Change backed participant.
        self.execute_fn(self.competition, self.competition.updateBackedParticipant,
                        [backed_participant,
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)

        # Move from state 4 to state 4: Increase Stake
        self.execute_fn(self.token, self.token.increaseStake,
                        [self.competition, 1,
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)

        # Move from state 4 to state 4: Decrease Stake
        self.execute_fn(self.token, self.token.decreaseStake,
                        [self.competition, 1,
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)

        # Move from state 4 back to state 3: Remove submission
        self.execute_fn(self.competition, self.competition.updateSubmission,
                        [self.competition.getSubmission(challenge_number, participant).hex(), (0).to_bytes(32, 'big'),
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)

        # Should fail: back 0 address
        self.execute_fn(self.competition, self.competition.updateBackedParticipant,
                        ['0x' + ('0'*40),
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=True)

        # Move from state 3 to state 1: Bet on self.
        self.execute_fn(self.competition, self.competition.updateBackedParticipant,
                        [participant,
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)

        # Move from state 1 to state 0: Reduce stake.
        self.execute_fn(self.token, self.token.setStake,
                        [self.competition, 0,
                         {'from': participant}],
                        use_multi_admin=False, exp_revert=False)

        verify('0x' + (40*'0'), self.competition.getBackedParticipant(participant))
