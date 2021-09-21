from brownie.test import strategy
from brownie.exceptions import VirtualMachineError
from collections import defaultdict
from test_token_state import TokenStateMachine
from brownie import interface, Contract, Token, Competition, accounts, reverts
from decimal import Decimal


class CompetitionStateMachine(TokenStateMachine):
    bytes32 = strategy("bytes32")
    bytes32_2 = strategy("bytes32")
    bytes32_non_zero = strategy("bytes32", exclude=bytes([0]*32))
    bytes32_non_zero_2 = strategy("bytes32", exclude=bytes([0]*32))
    participant = strategy("address")
    non_admin = strategy("address", exclude=0)
    amount = strategy("uint256")
    amount_2 = strategy("uint256")
    challenge = strategy("uint32")
    phase = strategy("uint8")

    def __init__(self, accounts, token_contract, comp_contract):
        TokenStateMachine.__init__(self, accounts, token_contract, int('1{}'.format('0' * 25)))
        self.admin = accounts[0]
        self.participants = accounts[1:]
        self.zero_address = '0x' + ('0'* 40)
        self.competition = comp_contract.deploy({'from': self.admin})

    def authorizeCompetition(self):
        tx = self.token.authorizeCompetition(self.competition.address, {'from': self.admin})
        self.verifyEvent(tx=tx, eventName='CompetitionAuthorized',
                         data={'competitionAddress': self.competition.address})

    def rule_initialize(self):
        if not self.comp_initialized[self.competition]:
            self.competition.initialize(int(Decimal('12e18')), int(Decimal('100e18')), self.token.address,
                                        {'from': self.admin})

            # Verify initial values.
            self.verifyValue('Main admin role check', True,
                             self.competition.hasRole(self.competition.RCI_MAIN_ADMIN(), self.admin))
            self.verifyValue('Main admin role check', False,
                             self.competition.hasRole(self.competition.RCI_MAIN_ADMIN(), accounts[1]))
            self.verifyValue('Child admin role check', True,
                             self.competition.hasRole(self.competition.RCI_CHILD_ADMIN(), self.admin))
            self.verifyValue('Child admin role check', False,
                             self.competition.hasRole(self.competition.RCI_CHILD_ADMIN(), accounts[1]))
            self.comp_initialized[self.competition] = True
            self.stake_threshold = int(Decimal('12e18'))
            self.rewards_threshold = int(Decimal('100e18'))
            self.token_address = self.token.address
            self.challenge_counter = 0
            self.challenges[self.challenge_counter].phase = 4
            self.cr_percentage = int(Decimal('20e16'))
            self.tr_percentage = int(Decimal('60e16'))


        else:
            with reverts():
                tx = self.competition.initialize(int(Decimal('12e18')), int(Decimal('100e18')), self.token.address,
                                        {'from': self.admin})

    def setup(self):
        class Information_struct:
            def __init__(self):
                self.submission = '0x' + bytes([0]*32).hex()
                self.staked_amount = 0
                self.staking_rewards = 0
                self.challenge_rewards = 0
                self.tournament_rewards = 0
                self.challenge_scores = 0
                self.tournament_scores = 0
                self.info_map = defaultdict(lambda: 0)


        class Challenge_struct:
            def __init__(self):
                self.dataset = '0x' + bytes([0]*32).hex()
                self.result = '0x' + bytes([0]*32).hex()
                self.public_key = '0x' + bytes([0]*32).hex()
                self.private_key = '0x' + bytes([0]*32).hex()
                self.submitters = set()
                self.submitter_info = defaultdict(lambda: Information_struct())
                self.deadlines = defaultdict(lambda: 0)
                self.phase = 4

        TokenStateMachine.setup(self)
        self.stakes = defaultdict(lambda: 0)
        self.challenges = defaultdict(lambda: Challenge_struct())
        self.comp_initialized = defaultdict(lambda: False)

        self.cr_percentage = 0
        self.tr_percentage = 0
        self.message = ''
        self.rewards_threshold = 0
        self.stake_threshold = 0
        self.token_address = ''
        self.challenge_counter = 0

        airdrop_amount = int(Decimal('1000e18')) // len(accounts)

        # airdrop
        for a in accounts[1:]:
            self.rule_transfer(self.admin, a, airdrop_amount)

        self.authorizeCompetition()
        self.rule_initialize()

        self.single_challenge_run(self.participants[0],
                                  int(Decimal("12e18")), int(Decimal("15e18")),
                                  bytes([200]*32), bytes([3]*32),
                                  bytes([55]*32), bytes([26]*32), self.participants[-1])

    def invariant_latest_challenge_info(self):
        challenge_number = self.competition.getLatestChallengeNumber()
        this_challenge = self.challenges[challenge_number]
        self.verifyValue('dataset', this_challenge.dataset,
                         self.competition.getDatasetHash(challenge_number))
        self.verifyValue('public key', this_challenge.public_key,
                         self.competition.getKeyHash(challenge_number))
        self.verifyValue('deadline0', this_challenge.deadlines[0],
                         self.competition.getDeadlines(challenge_number, 0))
        self.verifyValue('deadline1', this_challenge.deadlines[1],
                         self.competition.getDeadlines(challenge_number, 1))
        self.verifyValue('private key', this_challenge.private_key,
                         self.competition.getPrivateKeyHash(challenge_number))
        self.verifyValue('phase', this_challenge.phase, self.competition.getPhase(challenge_number))
        self.verifyValue('submitters', this_challenge.submitters,
                         set(self.get_submitters(challenge_number)))

        for s in self.stakes.keys():
            submitter_info = this_challenge.submitter_info[s]
            if s in this_challenge.submitters:
                self.verifyValue('submission', submitter_info.submission,
                                 self.competition.getSubmission(challenge_number, s))
                self.verifyValue('staked amount', submitter_info.staked_amount,
                                 self.competition.getStakedAmountForChallenge(challenge_number, s))

            else:
                self.verifyValue('submission', '0x' + bytes([0]*32).hex(),
                                 self.competition.getSubmission(challenge_number, s))
                self.verifyValue('staked amount', 0,
                                 self.competition.getStakedAmountForChallenge(challenge_number, s))

    def invariant_competition_info(self):
        self.verifyValue('Stake Threshold Check', self.stake_threshold, self.competition.getStakeThreshold())
        self.verifyValue('Reward Threshold Check', self.rewards_threshold, self.competition.getRewardsThreshold())
        self.verifyValue('Token Address Check', self.token_address, self.competition.getTokenAddress())
        self.verifyValue('Challenge Counter Check', self.challenge_counter, self.competition.getLatestChallengeNumber())
        self.verifyValue('Phase Check', self.challenges[self.challenge_counter].phase, self.competition.getPhase(self.competition.getLatestChallengeNumber()))
        self.verifyValue('Challenge Rewards Percentage Check', self.cr_percentage,
                         self.competition.getChallengeRewardsPercentageInWei())
        self.verifyValue('Tournament Rewards Percentage Check', self.tr_percentage,
                         self.competition.getTournamentRewardsPercentageInWei())
        self.verifyValue('Message Check', self.message, self.competition.getMessage())


    def invariant_total_competition_tokens(self):
        self.verifyValue('Total Competition Balance',
                         self.token.balanceOf(self.competition.address),
                         self.competition.getRemainder() + self.competition.getCompetitionPool()
                         + self.competition.getCurrentTotalStaked())

    def invariant_total_staked(self):
        self.verifyValue('Total Staked',
                         self.competition.getCurrentTotalStaked(),
                         sum(self.stakes.values()))

    def invariant_total_staked_and_submitted(self):
        challenge_number = self.competition.getLatestChallengeNumber()
        phase = self.competition.getPhase(challenge_number)
        if phase >= 2:
            submitters = self.get_submitters(challenge_number)
            staked_submitted_actual = 0
            for s in submitters:
                individual_staked = self.competition.getStakedAmountForChallenge(challenge_number, s)
                staked_submitted_actual += individual_staked

                if phase == 2:
                    self.verifyValue('Participant {} recorded and acutal stake not correct.'.format(s), individual_staked,
                                     self.competition.getStake(s))

    def invariant_submitter_info(self):
        challenge_number = self.competition.getLatestChallengeNumber()
        for cn in range(1, challenge_number + 1):
            for a in accounts:
                submitter_info = self.challenges[challenge_number].submitter_info[a]
                self.verifyValue('submission', submitter_info.submission, self.competition.getSubmission(cn, a))
                self.verifyValue('challenge scores', submitter_info.challenge_scores, self.competition.getChallengeScores(cn, a))
                self.verifyValue('tournament scores', submitter_info.tournament_scores, self.competition.getTournamentScores(cn, a))
                self.verifyValue('staked amount', submitter_info.staked_amount, self.competition.getStakedAmountForChallenge(cn, a))

                self.verifyValue('staking reward', submitter_info.staking_rewards, self.competition.getStakingRewards(cn, a))
                self.verifyValue('challenge reward', submitter_info.challenge_rewards,
                                 self.competition.getChallengeRewards(cn, a))
                self.verifyValue('tournament reward', submitter_info.tournament_rewards,
                                 self.competition.getTournamentRewards(cn, a))
                self.verifyValue('staking reward', submitter_info.staking_rewards + submitter_info.challenge_rewards + submitter_info.tournament_rewards,
                                 self.competition.getOverallRewards(cn, a))

                for item_num in submitter_info.info_map.keys():
                    self.verifyValue('info at index {}'.format(item_num), submitter_info.info_map[item_num],
                                     self.competition.getInformation(cn, a, item_num))

    def invariant_unauthorized_calls_check(self):
        non_admin = self.participants[-1]
        amount = 1
        bytes32_non_zero = bytes([1]*32)
        bytes32_non_zero_2 = bytes([2] * 32)

        main_admin_hash = self.competition.RCI_MAIN_ADMIN().hex()
        child_admin_hash = self.competition.RCI_CHILD_ADMIN().hex()
        challenge_number = self.competition.getLatestChallengeNumber()
        with reverts(): self.competition.revokeRole(child_admin_hash, self.admin, {'from': non_admin})
        with reverts(): self.competition.grantRole(child_admin_hash, non_admin, {'from': non_admin})
        with reverts(): self.competition.renounceRole(child_admin_hash, self.admin, {'from': non_admin})
        with reverts(): self.competition.revokeRole(main_admin_hash, self.admin, {'from': non_admin})
        with reverts(): self.competition.grantRole(main_admin_hash, non_admin, {'from': non_admin})
        with reverts(): self.competition.renounceRole(main_admin_hash, self.admin, {'from': non_admin})

        with reverts(): self.competition.updateMessage(str(bytes32_non_zero), {'from': non_admin})
        with reverts(): self.competition.updateDeadlines(challenge_number, amount, amount, {'from': non_admin})
        with reverts(): self.competition.updateRewardsThreshold(amount, {'from': non_admin})
        with reverts(): self.competition.updateStakeThreshold(amount, {'from': non_admin})
        with reverts(): self.competition.updateChallengeRewardsPercentageInWei(amount, {'from': non_admin})
        with reverts(): self.competition.updateTournamentRewardsPercentageInWei(amount, {'from': non_admin})
        with reverts(): self.competition.openChallenge(bytes32_non_zero, bytes32_non_zero_2, amount, amount, {'from': non_admin})
        with reverts(): self.competition.updateDataset(self.competition.getDatasetHash(challenge_number), bytes32_non_zero_2, {'from': non_admin})
        with reverts(): self.competition.updateKey(self.competition.getKeyHash(challenge_number), bytes32_non_zero, {'from': non_admin})
        with reverts(): self.competition.updatePrivateKey(challenge_number, bytes32_non_zero, {'from': non_admin})
        with reverts(): self.competition.closeSubmission({'from': non_admin})
        with reverts(): self.competition.submitResults(bytes32_non_zero, {'from': non_admin})
        with reverts(): self.competition.updateResults(self.competition.getResultsHash(challenge_number), bytes32_non_zero_2, {'from': non_admin})
        with reverts(): self.competition.payRewards([non_admin], [amount], [amount], [amount], {'from': non_admin})
        with reverts(): self.competition.updateChallengeAndTournamentScores(challenge_number, [non_admin], [amount], [amount], {'from': non_admin})
        with reverts(): self.competition.updateInformationBatch(challenge_number, [non_admin], amount, [amount], {'from': non_admin})
        with reverts(): self.competition.advanceToPhase(self.competition.getPhase(challenge_number) + 1, {'from': non_admin})
        with reverts(): self.competition.moveRemainderToPool({'from': non_admin})

    def get_submitters(self, challenge_number):
        submitters_len = self.competition.getSubmissionCounter(challenge_number)
        submitters = []
        chunk = 10

        for i in range(0, submitters_len, chunk):
            if (i + chunk) >= submitters_len:
                end_index = submitters_len
            else:
                end_index = i + chunk
            submitters.extend(self.competition.getSubmitters(challenge_number, i, end_index))

        return submitters


    def rule_setStake(self, participant, amount):
        current_stake = self.stakes[participant]
        stake_diff = amount - current_stake
        current_bal = self.balances[participant]
        challenge_number = self.competition.getLatestChallengeNumber()
        phase = self.competition.getPhase(challenge_number)
        submission = int(self.competition.getSubmission(challenge_number, participant).hex(), 16)
        submission_exists = submission != 0
        stake_threshold = self.competition.getStakeThreshold()

        # stake increase
        if phase != 2 and stake_diff > 0 and stake_diff <= current_bal:
            tx = self.token.setStake(self.competition.address, amount, {"from": participant})
            self.verifySetStake(participant, stake_diff)
            self.verifyEvent(tx, 'StakeIncreased',
                             {'sender': participant, 'amount': stake_diff})
            self.verifyReturnValue(tx, True)

            if submission_exists:
                self.challenges[challenge_number].submitter_info[participant].staked_amount = self.competition.getStake(participant)
                self.verifyValue('Individual staked amount for challenge', self.competition.getStake(participant),
                                 self.competition.getStakedAmountForChallenge(challenge_number, participant))
            else:
                self.verifyValue('Individual staked amount for challenge', 0,
                                 self.competition.getStakedAmountForChallenge(challenge_number, participant))

        # stake decrease
        elif phase != 2 and stake_diff < 0 and (-stake_diff) <= current_stake and (not submission_exists or (amount >= stake_threshold)):
            tx = self.token.setStake(self.competition.address, amount, {"from": participant})
            self.verifySetStake(participant, stake_diff)
            self.verifyEvent(tx, 'StakeDecreased',
                             {'sender': participant, 'amount': -stake_diff})
            self.verifyReturnValue(tx, True)

            if submission_exists:
                self.challenges[challenge_number].submitter_info[participant].staked_amount = self.competition.getStake(participant)
                self.verifyValue('Individual staked amount for challenge', self.competition.getStake(participant),
                                 self.competition.getStakedAmountForChallenge(challenge_number, participant))
            else:
                self.verifyValue('Individual staked amount for challenge', 0,
                                 self.competition.getStakedAmountForChallenge(challenge_number, participant))


        else:
            with reverts():
                tx = self.token.setStake(self.competition.address, amount, {"from": participant})
            self.verifySetStake(participant, 0)

    def rule_increaseStake(self, participant, amount):
        current_bal = self.balances[participant]
        challenge_number = self.competition.getLatestChallengeNumber()
        phase = self.competition.getPhase(challenge_number)
        submission = int(self.competition.getSubmission(challenge_number, participant).hex(), 16)
        submission_exists = submission!=0

        if phase != 2 and amount <= current_bal:
            tx = self.token.increaseStake(self.competition.address, amount, {"from": participant})
            self.verifySetStake(participant, amount)
            self.verifyEvent(tx, 'StakeIncreased',
                             {'sender': participant, 'amount': amount})
            self.verifyReturnValue(tx, True)

            if submission_exists:
                self.challenges[challenge_number].submitter_info[participant].staked_amount = self.competition.getStake(participant)
                self.verifyValue('Individual staked ampunt for challenge', self.competition.getStake(participant),
                                 self.competition.getStakedAmountForChallenge(challenge_number, participant))
            else:
                self.verifyValue('Individual staked amount for challenge', 0,
                                 self.competition.getStakedAmountForChallenge(challenge_number, participant))
        else:
            with reverts():
                tx = self.token.increaseStake(self.competition.address, amount, {"from": participant})
            self.verifySetStake(participant, 0)

    def rule_decreaseStake(self, participant, amount):
        current_stake = self.stakes[participant]
        challenge_number = self.competition.getLatestChallengeNumber()
        phase = self.competition.getPhase(challenge_number)
        stake_threshold = self.competition.getStakeThreshold()
        submission = int(self.competition.getSubmission(challenge_number, participant).hex(), 16)
        submission_exists = submission != 0


        if (phase != 2) and (amount <= current_stake) and (not submission_exists or ((current_stake-amount) >= stake_threshold)):
            tx = self.token.decreaseStake(self.competition.address, amount, {"from": participant})
            self.verifySetStake(participant, -amount)
            self.verifyEvent(tx, 'StakeDecreased',
                             {'sender': participant, 'amount': amount})
            self.verifyReturnValue(tx, True)

            if submission_exists:
                self.challenges[challenge_number].submitter_info[participant].staked_amount = self.competition.getStake(participant)
                self.verifyValue('Individual staked ampunt for challenge', self.competition.getStake(participant),
                                 self.competition.getStakedAmountForChallenge(challenge_number, participant))
            else:
                self.verifyValue('Individual staked amount for challenge', 0,
                                 self.competition.getStakedAmountForChallenge(challenge_number, participant))

        else:
            with reverts():
                tx = self.token.decreaseStake(self.competition.address, amount, {"from": participant})
            self.verifySetStake(participant, 0)

    def rule_submitNewPredictions(self, participant, bytes32):
        current_stake = self.stakes[participant]
        challenge_number = self.competition.getLatestChallengeNumber()
        phase = self.competition.getPhase(challenge_number)
        submission = int(self.competition.getSubmission(challenge_number, participant).hex(), 16)
        stake_threshold = self.competition.getStakeThreshold()

        if phase == 1 and submission == 0 and current_stake >= stake_threshold and int(bytes32.hex(), 16) != 0:
            tx = self.competition.submitNewPredictions(bytes32, {"from": participant})
            self.challenges[challenge_number].submitter_info[participant].submission = '0x' + bytes32.hex()
            self.challenges[challenge_number].submitters.add(participant)
            self.challenges[challenge_number].submitter_info[participant].staked_amount = self.competition.getStake(
                participant)
            self.verifyEvent(tx, 'SubmissionUpdated',
                             {'challengeNumber': challenge_number,
                              'participantAddress': participant,
                              'newSubmissionHash': '0x'+bytes32.hex()})
            self.verifyValue('Updated submission',
                             '0x' + bytes32.hex(),
                             self.competition.getSubmission(challenge_number, participant))
            self.verifyValue('Individual staked amount for challenge',
                             self.competition.getStake(participant),
                             self.competition.getStakedAmountForChallenge(challenge_number, participant))
            self.verifyValue('Current submitters', self.challenges[challenge_number].submitters,
                             set(self.get_submitters(challenge_number)))

        else:
            with reverts():
                tx = self.competition.submitNewPredictions(bytes32, {"from": participant})

    def rule_updateSubmission(self, participant, bytes32_non_zero):
        current_stake = self.stakes[participant]
        challenge_number = self.competition.getLatestChallengeNumber()
        phase = self.competition.getPhase(challenge_number)
        submission_hash = self.competition.getSubmission(challenge_number, participant)
        submission = int(submission_hash.hex(), 16)
        stake_threshold = self.competition.getStakeThreshold()

        if phase == 1 and submission != 0 and current_stake >= stake_threshold and submission_hash != '0x' + bytes32_non_zero.hex():
            tx = self.competition.updateSubmission(submission_hash, bytes32_non_zero, {'from': participant})
            self.challenges[challenge_number].submitter_info[participant].submission = '0x' + bytes32_non_zero.hex()
            self.verifyEvent(tx, 'SubmissionUpdated',
                             {'challengeNumber': challenge_number,
                              'participantAddress': participant,
                              'newSubmissionHash': '0x'+bytes32_non_zero.hex()})
            self.verifyValue('Updated submission',
                             '0x'+bytes32_non_zero.hex(),
                             self.competition.getSubmission(challenge_number, participant))
        else:
            with reverts():
                tx = self.competition.updateSubmission(submission_hash, bytes32_non_zero, {'from': participant})

    def rule_withdrawSubmission(self, participant):
        bytes32 = bytes([0]*32)
        current_stake = self.stakes[participant]
        challenge_number = self.competition.getLatestChallengeNumber()
        phase = self.competition.getPhase(challenge_number)
        submission_hash = self.competition.getSubmission(challenge_number, participant)
        submission = int(submission_hash.hex(), 16)
        stake_threshold = self.competition.getStakeThreshold()

        if phase == 1 and submission != 0 and current_stake >= stake_threshold and submission_hash != '0x' + bytes32.hex():
            tx = self.competition.updateSubmission(submission_hash, bytes32, {'from': participant})
            self.challenges[challenge_number].submitter_info[participant].submission = '0x' + bytes32.hex()
            self.challenges[challenge_number].submitters.remove(participant)
            self.challenges[challenge_number].submitter_info[participant].staked_amount = 0
            self.verifyEvent(tx, 'SubmissionUpdated',
                             {'challengeNumber': challenge_number,
                              'participantAddress': participant,
                              'newSubmissionHash': '0x' + bytes32.hex()})
            self.verifyValue('Updated submission',
                             '0x' + bytes32.hex(),
                             self.competition.getSubmission(challenge_number, participant))
            self.verifyValue('Individual staked amount for challenge',
                             0,
                             self.competition.getStakedAmountForChallenge(challenge_number, participant))
            self.verifyValue('Current submitters', self.challenges[challenge_number].submitters,
                             set(self.get_submitters(challenge_number)))
        else:
            with reverts():
                tx = self.competition.updateSubmission(submission_hash, bytes32, {'from': participant})

    def rule_moveRemainderToPool(self):
        challenge_number = self.competition.getLatestChallengeNumber()
        phase = self.competition.getPhase(challenge_number)
        remainder = self.competition.getRemainder()
        pool = self.competition.getCompetitionPool()

        if phase == 4 and remainder > 0:
            tx = self.competition.moveRemainderToPool({'from': self.admin})
            self.verifyEvent(tx, 'RemainderMovedToPool',
                             {'remainder': remainder})
            self.verifyValue('Remainder Moved',
                             0, self.competition.getRemainder())
            self.verifyValue('Pool received remainder',
                             pool + remainder
                             , self.competition.getCompetitionPool())
        else:
            with reverts():
                tx = self.competition.moveRemainderToPool({'from': self.admin})

    def rule_sponsor(self, participant, amount):
        challenge_number = self.competition.getLatestChallengeNumber()
        phase = self.competition.getPhase(challenge_number)
        pool = self.competition.getCompetitionPool()
        current_bal = self.balances[participant]
        self.rule_increaseAllowance(participant, self.competition.address, amount)

        if phase == 4 and amount <= current_bal:
            tx = self.competition.sponsor(amount, {'from': participant})
            self.verifyAllowance(participant, self.competition.address, -amount)

            self.verifyEvent(tx, 'Sponsor',
                             {'sponsorAddress': participant,
                              'sponsorAmount': amount,
                            'poolTotal': pool + amount})
            self.verifyTransfer(participant, self.competition.address, amount)
            self.verifyValue('Sponsor competition pool', pool + amount, self.competition.getCompetitionPool())
        else:
            with reverts():
                tx = self.competition.sponsor(amount, {'from': participant})

    def rule_openChallenge(self, bytes32, bytes32_2, amount, amount_2):
        challenge_number = self.competition.getLatestChallengeNumber()
        pool = self.competition.getCompetitionPool()
        phase = self.competition.getPhase(challenge_number)

        if phase == 4 and self.competition.getCompetitionPool() >= self.competition.getRewardsThreshold():
            tx = self.competition.openChallenge(bytes32, bytes32_2, amount, amount_2, {'from': self.admin})
            new_challenge_number = challenge_number + 1
            self.challenges[new_challenge_number].dataset = '0x' + bytes32.hex()
            self.challenges[new_challenge_number].public_key = '0x' + bytes32_2.hex()
            self.challenges[new_challenge_number].deadlines[0] = amount
            self.challenges[new_challenge_number].deadlines[1] = amount_2
            self.challenges[new_challenge_number].phase = 1
            self.challenge_counter = new_challenge_number

            self.verifyEvent(tx, 'ChallengeOpened',
                             {'challengeNumber': new_challenge_number})
            new_phase = self.competition.getPhase(new_challenge_number)
            self.verifyValue('openChallenge Phase', 1, new_phase)
            self.verifyValue('openChallenge Challenge Number', self.competition.getLatestChallengeNumber(), new_challenge_number)
            self.verifyValue('openChallenge dataset', self.competition.getDatasetHash(new_challenge_number), '0x'+bytes32.hex())
            self.verifyValue('openChallenge key', self.competition.getKeyHash(new_challenge_number), '0x'+bytes32_2.hex())
            self.verifyValue('currentChallengeRewardsBudget', self.competition.getCurrentChallengeRewardsBudget(),
                             (Decimal(pool) * Decimal(self.competition.getChallengeRewardsPercentageInWei())) // Decimal("1e18"))
            self.verifyValue('currentTournamentRewardsBudget', self.competition.getCurrentTournamentRewardsBudget(),
                             (Decimal(pool) * Decimal(self.competition.getTournamentRewardsPercentageInWei())) // Decimal("1e18"))
            self.verifyValue('currentStakingRewardsBudget', self.competition.getCurrentStakingRewardsBudget(),
                             pool - self.competition.getCurrentChallengeRewardsBudget()
                             - self.competition.getCurrentTournamentRewardsBudget())
            self.verifyValue('deadline 0', self.competition.getDeadlines(new_challenge_number, 0), amount)
            self.verifyValue('deadline 1', self.competition.getDeadlines(new_challenge_number, 1), amount_2)
        else:
            with reverts():
                tx = self.competition.openChallenge(bytes32, bytes32_2, amount, amount_2, {'from': self.admin})

    def rule_updateDataset(self, bytes32):
        challenge_number = self.competition.getLatestChallengeNumber()
        phase = self.competition.getPhase(challenge_number)
        old_hash = self.competition.getDatasetHash(challenge_number)

        if phase == 1 and int(old_hash.hex(),16) != 0 and old_hash != '0x'+bytes32.hex():
            with reverts():
                tx = self.competition.updateDataset(bytes32, old_hash, {'from': self.admin})

            tx = self.competition.updateDataset(old_hash, bytes32, {'from': self.admin})
            self.challenges[challenge_number].dataset = '0x' + bytes32.hex()
            self.verifyEvent(tx, 'DatasetUpdated',
                             {'challengeNumber': challenge_number,
                              'oldDatasetHash': old_hash,
                              'newDatasetHash': '0x'+bytes32.hex()})
            self.verifyValue('Updated Dataset', self.competition.getDatasetHash(challenge_number), '0x'+bytes32.hex())
        else:
            with reverts():
                tx = self.competition.updateDataset(old_hash, bytes32, {'from': self.admin})

    def rule_updateKey(self, bytes32):
        challenge_number = self.competition.getLatestChallengeNumber()
        phase = self.competition.getPhase(challenge_number)
        old_hash = self.competition.getKeyHash(challenge_number)

        if phase == 1 and int(old_hash.hex(),16) != 0 and old_hash != '0x'+bytes32.hex():
            with reverts():
                tx = self.competition.updateKey(bytes32, old_hash, {'from': self.admin})

            tx = self.competition.updateKey(old_hash, bytes32, {'from': self.admin})
            self.challenges[challenge_number].public_key = '0x' + bytes32.hex()
            self.verifyEvent(tx, 'KeyUpdated',
                             {'challengeNumber': challenge_number,
                              'oldKeyHash': old_hash,
                              'newKeyHash': '0x'+bytes32.hex()})
            self.verifyValue('Updated Key', self.competition.getKeyHash(challenge_number), '0x'+bytes32.hex())
        else:
            with reverts():
                tx = self.competition.updateKey(old_hash, bytes32, {'from': self.admin})

    def rule_updatePrivateKey(self, bytes32):
        challenge_number = self.competition.getLatestChallengeNumber()
        tx = self.competition.updatePrivateKey(challenge_number, bytes32, {'from': self.admin})
        self.challenges[challenge_number].private_key = '0x' + bytes32.hex()

    def rule_closeSubmission(self):
        challenge_number = self.competition.getLatestChallengeNumber()
        phase = self.competition.getPhase(challenge_number)
        if phase == 1:
            tx = self.competition.closeSubmission({'from': self.admin})
            self.challenges[challenge_number].phase = 2
            self.verifyEvent(tx, 'SubmissionClosed',
                             {'challengeNumber': challenge_number})
        else:
            with reverts():
                tx = self.competition.closeSubmission({'from': self.admin})

    def rule_submitResults(self, bytes32):
        challenge_number = self.competition.getLatestChallengeNumber()
        phase = self.competition.getPhase(challenge_number)
        old_hash = self.competition.getResultsHash(challenge_number)

        if phase >= 3 and int(old_hash.hex(),16) == 0:
            with reverts():
                self.competition.submitResults(bytes([0]*32).hex(), {'from': self.admin})

            tx = self.competition.submitResults(bytes32, {'from': self.admin})
            self.challenges[challenge_number].result = '0x' + bytes32.hex()
            self.verifyEvent(tx, 'ResultsUpdated',
                             {'challengeNumber': challenge_number,
                              'oldResultsHash': '0x0000000000000000000000000000000000000000000000000000000000000000',
                              'newResultsHash': '0x'+bytes32.hex()})
            self.verifyValue('Submitted Results', self.competition.getResultsHash(challenge_number), '0x'+bytes32.hex())
        else:
            with reverts():
                tx = self.competition.submitResults(bytes32, {'from': self.admin})

    def rule_updateResults(self, bytes32):
        challenge_number = self.competition.getLatestChallengeNumber()
        phase = self.competition.getPhase(challenge_number)
        old_hash = self.competition.getResultsHash(challenge_number)
        with reverts():
            tx = self.competition.updateResults(bytes32, old_hash, {'from': self.admin})

        if phase >= 3 and int(old_hash.hex(), 16) != 0 and old_hash != '0x' + bytes32.hex():
            with reverts():
                tx = self.competition.updateResults(bytes32, old_hash, {'from': self.admin})

            tx = self.competition.updateResults(old_hash, bytes32, {'from': self.admin})
            self.challenges[challenge_number].result = '0x' + bytes32.hex()
            self.verifyEvent(tx, 'ResultsUpdated',
                             {'challengeNumber': challenge_number,
                              'oldResultsHash': old_hash,
                              'newResultsHash': '0x' + bytes32.hex()})
            self.verifyValue('Updated Results', self.competition.getResultsHash(challenge_number), '0x' + bytes32.hex())
        else:
            with reverts():
                tx = self.competition.updateResults(old_hash, bytes32, {'from': self.admin})

    def rule_payRewards(self):
        challenge_number = self.competition.getLatestChallengeNumber()
        phase = self.competition.getPhase(challenge_number)
        submitters = self.get_submitters(challenge_number)
        submitters_len = len(submitters)
        challenge_budget = self.competition.getCurrentChallengeRewardsBudget()
        challenge_each = challenge_budget // len(submitters)
        tournament_budget = self.competition.getCurrentTournamentRewardsBudget()
        tournament_each = tournament_budget // len(submitters)

        #Staking rewards
        stakes = []
        for s in submitters:
            stakes.append(self.competition.getStake(s))

        total_stakes = sum(stakes)
        assert total_stakes <= self.competition.getCurrentTotalStaked(), "Error in total stakes calculation!"

        staking_rewards = []
        staking_budget = self.competition.getCurrentStakingRewardsBudget()
        for i in range(submitters_len):
            staking_rewards.append(staking_budget * stakes[i] // total_stakes)

        # Challenge and Tournament Rewards
        challenge_rewards = [challenge_each] * submitters_len
        tournament_rewards = [tournament_each] * submitters_len

        if phase >= 3 and sum(staking_rewards) <= staking_budget and sum(challenge_rewards) <= challenge_budget and sum(tournament_rewards) <= tournament_budget:
            tx = self.competition.payRewards(
                submitters, staking_rewards, challenge_rewards, tournament_rewards, {'from': self.admin})

            for i in range(submitters_len):
                s = submitters[i]
                sr = staking_rewards[i]
                cr = challenge_rewards[i]
                tr = tournament_rewards[i]
                self.stakes[s] += cr + tr + sr
                self.verifyStake(s)

                self.challenges[challenge_number].submitter_info[s].staking_rewards += sr
                self.challenges[challenge_number].submitter_info[s].challenge_rewards += cr
                self.challenges[challenge_number].submitter_info[s].tournament_rewards += tr

                self.verifyEvent(tx, 'RewardsPayment',
                                 {'challengeNumber': challenge_number,
                                  'submitter': s,
                                  'stakingReward': sr,
                                  'challengeReward': cr,
                                  'tournamentReward': tr})
            self.verifyEvent(tx, 'TotalRewardsPaid',
                             {'challengeNumber': challenge_number,
                              'totalStakingAmount': sum(staking_rewards),
                              'totalChallengeAmount': sum(challenge_rewards),
                              'totalTournamentAmount': sum(tournament_rewards)})

        else:
            with reverts():
                tx = self.competition.payRewards(
                    submitters, staking_rewards, challenge_rewards, tournament_rewards, {'from': self.admin})

    def rule_updateChallengeAndTournamentScores(self, challenge):
        challenge_number = self.competition.getLatestChallengeNumber()
        phase = self.competition.getPhase(challenge_number)
        submitters = self.get_submitters(challenge_number)

        c_scores = []
        t_scores = []

        for s in submitters:
            c_scores.append(int(Decimal('33e16')))
            t_scores.append(int(Decimal('56e16')))

        if phase >= 3:
            tx = self.competition.updateChallengeAndTournamentScores(
                challenge_number, submitters, c_scores, t_scores, {'from': self.admin})
            self.verifyEvent(tx, 'ChallengeAndTournamentScoresUpdated',
                             {'challengeNumber': challenge_number})

            for i in range(len(submitters)):
                self.verifyValue('Challenge Score Update', c_scores[i],
                                 self.competition.getChallengeScores(challenge_number, submitters[i]))
                self.challenges[challenge_number].submitter_info[submitters[i]].challenge_scores = c_scores[i]
                self.verifyValue('Tournament Score Update', t_scores[i],
                                 self.competition.getTournamentScores(challenge_number, submitters[i]))
                self.challenges[challenge_number].submitter_info[submitters[i]].tournament_scores = t_scores[i]

        else:
            with reverts():
                tx = self.competition.updateChallengeAndTournamentScores(
                    challenge_number, submitters, c_scores, t_scores, {'from': self.admin})

    def rule_advance_to_phase(self, phase):
        challenge_number = self.competition.getLatestChallengeNumber()
        current_phase = self.competition.getPhase(challenge_number)

        if (2 < phase < 5) and (current_phase == (phase - 1)):
            tx = self.competition.advanceToPhase(phase, {'from': self.admin})
            self.challenges[challenge_number].phase = phase
        else:
            with reverts():
                tx = self.competition.advanceToPhase(phase, {'from': self.admin})

    def rule_update_deadlines(self, amount, amount_2, challenge):
        self.competition.updateDeadlines(challenge, amount_2, amount)
        self.challenges[challenge].deadlines[amount_2] = amount

    def rule_update_info_batch(self, participant, non_admin, amount, amount_2, bytes32):
        challenge_number = self.competition.getLatestChallengeNumber()
        current_phase = self.competition.getPhase(challenge_number)
        item_num = int(bytes32.hex(), 16)
        if current_phase >= 3:
            tx = self.competition.updateInformationBatch(challenge_number, [participant, non_admin], item_num,
                                                    [amount, amount_2], {'from': self.admin})
            self.challenges[challenge_number].submitter_info[participant].info_map[item_num] = amount
            self.challenges[challenge_number].submitter_info[non_admin].info_map[item_num] = amount_2
            self.verifyEvent(tx, 'BatchInformationUpdated',
                             {'challengeNumber': challenge_number,
                              'itemNumber': item_num})
        else:
            with reverts():
                tx = self.competition.updateInformationBatch(challenge_number, [participant, non_admin], item_num,
                                                    [amount, amount_2], {'from': self.admin})

    def rule_update_comp_info(self, amount, amount_2, bytes32_non_zero, bytes32_non_zero_2, bytes32):

        tx = self.competition.updateChallengeRewardsPercentageInWei(amount, {'from': self.admin})
        self.verifyEvent(tx, 'ChallengeRewardsPercentageInWeiUpdated',
                         {'newPercentage': amount})
        tx = self.competition.updateTournamentRewardsPercentageInWei(amount_2, {'from': self.admin})
        self.verifyEvent(tx, 'TournamentRewardsPercentageInWeiUpdated',
                         {'newPercentage': amount_2})
        tx = self.competition.updateStakeThreshold(int(bytes32_non_zero.hex(), 16), {'from': self.admin})
        self.verifyEvent(tx, 'StakeThresholdUpdated',
                         {'newStakeThreshold': int(bytes32_non_zero.hex(), 16)})
        tx = self.competition.updateRewardsThreshold(int(bytes32_non_zero_2.hex(), 16), {'from': self.admin})
        self.verifyEvent(tx, 'RewardsThresholdUpdated',
                         {'newRewardsThreshold': int(bytes32_non_zero_2.hex(), 16)})
        tx = self.competition.updateMessage(bytes32.hex(), {'from': self.admin})
        self.verifyEvent(tx, 'MessageUpdated', {})

        self.cr_percentage = amount
        self.tr_percentage = amount_2
        self.stake_threshold = int(bytes32_non_zero.hex(), 16)
        self.rewards_threshold = int(bytes32_non_zero_2.hex(), 16)
        self.message = bytes32.hex()

    def single_challenge_run(self, participant, amount, amount_2, bytes32, bytes32_2, bytes32_non_zero, bytes32_non_zero_2, non_admin):
        self.rule_increaseAllowance(self.admin, self.competition.address, int(Decimal('1000e18')))
        self.rule_sponsor(self.admin, int(Decimal('1000e18')))
        self.rule_openChallenge(bytes32, bytes32_2, amount, amount_2)
        self.rule_updateDataset(bytes32_2)
        self.rule_updateKey(bytes32)
        challenge_number = self.competition.getLatestChallengeNumber()
        self.rule_transfer(self.admin, participant, self.competition.getStakeThreshold())
        self.rule_increaseStake(participant, self.competition.getStakeThreshold() * 2)
        self.rule_decreaseStake(participant, self.competition.getStakeThreshold() // 3)
        self.rule_submitNewPredictions(participant, bytes32_non_zero)
        self.rule_updateSubmission(participant, bytes32)
        self.rule_withdrawSubmission(participant)
        self.rule_submitNewPredictions(participant, bytes32_non_zero)
        self.rule_updateSubmission(participant, bytes32)
        self.rule_closeSubmission()
        self.rule_advance_to_phase(3)
        self.rule_submitResults(bytes32)
        self.rule_updateResults(bytes32)
        self.rule_updateChallengeAndTournamentScores(challenge_number)
        self.rule_payRewards()
        self.rule_updatePrivateKey(bytes32_2)
        self.rule_advance_to_phase(4)
        self.rule_updatePrivateKey(bytes32)
        self.rule_updateChallengeAndTournamentScores(challenge_number)
        self.rule_update_info_batch(participant, non_admin, amount, amount_2, bytes32)
        self.rule_update_comp_info(amount, amount_2, bytes32_non_zero, bytes32_non_zero_2, bytes32)
        self.rule_transfer(self.admin, self.competition.address, amount)
        self.rule_moveRemainderToPool()

    # Verification Functions
    def verifyStake(self, staker):
        self.verifyValue(
            "getStake({})".format(staker),
            self.stakes[staker],
            self.competition.getStake(staker),
        )

    def verifySetStake(self, staker, amount):
        self.stakes[staker] += amount
        self.verifyTransfer(staker, self.competition.address, amount)
        self.verifyStake(staker)
        self.verifyBalance(staker)

def test_stateful_competition(state_machine, Token, Competition, accounts):
    state_machine(CompetitionStateMachine, accounts, Token, Competition)