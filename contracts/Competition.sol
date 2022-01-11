pragma solidity 0.8.4;

// SPDX-License-Identifier: MIT

import './../interfaces/ICompetition.sol';
import './../interfaces/ICompetitionV2.sol';
import './../interfaces/IToken.sol';
import './CompetitionStorage.sol';
import './CompetitionStorageV2.sol';
import './AccessControlRci.sol';
import './standard/proxy/utils/Initializable.sol';

/**
 * @title RCI Tournament(Competition) Contract
 * @author Rocket Capital Investment Pte Ltd
 * @dev This contract manages registration and reward payouts for the RCI Tournament.
 * @dev IPFS hash format: Hash Identifier (2 bytes), Actual Hash (May eventually take on other formats but currently 32 bytes)
 *
 */
contract Competition is AccessControlRci, ICompetition, CompetitionStorage, Initializable, ICompetitionV2, CompetitionStorageV2 {

    constructor(){}

    function initialize(uint256 stakeThreshold_, uint256 rewardsThreshold_, address tokenAddress_)
    external
    initializer
    {
        require(tokenAddress_ != address(0), "No token address found.");
        _initializeRciAdmin();
        _stakeThreshold = stakeThreshold_;
        _rewardsThreshold = rewardsThreshold_;
        _token = IToken(tokenAddress_);
        _challengeCounter = 0;
        _challenges[_challengeCounter].phase = 4;
        _challengeRewardsPercentageInWei = 20e16;
        _tournamentRewardsPercentageInWei = 60e16;
    }

    /**
    PARTICIPANT WRITE METHODS
    **/

    function increaseStake(address staker, uint256 amountToken)
    external override
    returns (bool success)
    {
        uint32 challengeNumber = _challengeCounter;
        require(msg.sender == address(_token), "Competition - increaseStake: Please call this function via the token contract.");
        require(_challenges[challengeNumber].phase == 1, "Competition - increaseStake: Please wait for the staking period to unlock before modifying your stake.");
        require(amountToken > 0, "Competition - increaseStake: Amount to increase by must be greater than 0");

        uint256 currentBal = _stakes[staker];

        _stakes[staker] = currentBal + amountToken;
        _currentTotalStaked += amountToken;

        EnumerableSet.add(stakerSet, staker);

        if (_backed[staker] == address(0)) {
            _updateBackedParticipant(staker, staker, address(0));
        }

        require(((currentBal + amountToken) >= _stakeThreshold), "Competition - increaseStake: Your final balance must be either 0 or at least the stake threshold.");

        success = true;

        emit StakeIncreased(staker, amountToken);
    }

    function decreaseStake(address staker, uint256 amountToken)
    external override
    returns (bool success)
    {
        uint32 challengeNumber = _challengeCounter;
        require(msg.sender == address(_token), "Competition - decreaseStake: Please call this function via the token contract.");
        require(_challenges[_challengeCounter].phase == 1, "Competition - decreaseStake: Please wait for the staking period to unlock before modifying your stake.");
        require(amountToken > 0, "Competition - increaseStake: Amount to decrease by must be greater than 0");

        uint256 currentBal = _stakes[staker];
        require(amountToken <= currentBal, "Competition - decreaseStake: Insufficient funds for withdrawal.");

        require(((currentBal - amountToken) == 0) ||
            ((currentBal - amountToken) >= _stakeThreshold), "Competition - decreaseStake: Your final balance must be either 0 or at least the stake threshold.");

        address oldBackedParticipant = _backed[staker];
        bool submissionExists = _challenges[challengeNumber].submitterInfo[staker].submission != bytes32(0);
        bool backingOthers = (oldBackedParticipant != staker) && (oldBackedParticipant != address(0));

        if (currentBal == amountToken){
            require(!(submissionExists || backingOthers), "Competition - decreaseStake: You may not lower your stake below the threshold while you have an existing submission or are backing other participants.");
            EnumerableSet.remove(stakerSet, staker);
            if (oldBackedParticipant != address(0)){
                _updateBackedParticipant(address(0), staker, oldBackedParticipant);
            }
        }

        _stakes[staker] = currentBal - amountToken;
        _currentTotalStaked -= amountToken;
        success = _token.transfer(staker, amountToken);

        emit StakeDecreased(staker, amountToken);
    }

    function updateBackedParticipant(address backedParticipant)
    external override
    returns (bool success)
    {
        require(backedParticipant != address(0), "Competition - updateBackedParticipant: Not allowed to back the 0 address.");
        require(_challenges[_challengeCounter].phase == 1, "Competition - updateBackedParticipant: You may only modify your backing details when the submission window is open.");
        address oldBackedParticipant = _backed[msg.sender];
        success = _updateBackedParticipant(backedParticipant, msg.sender, oldBackedParticipant);
    }

    function
    _updateBackedParticipant(address backedParticipant, address backer, address oldBackedParticipant)
    private
    returns (bool success)
    {
        uint32 challengeNumber = _challengeCounter;
        require(_stakes[backer] >= _stakeThreshold, "Competition - updateBackedParticipant: Please stake at least the backing minimum amount before selecting a participant to back.");
        require(oldBackedParticipant != backedParticipant, "Competition - updateBackedParticipant: You are already backing this participant.");

        // Set the backer's backed participant to be `backedParticipant`.
        _backed[backer] = backedParticipant;

        // If the backer is already backing a participant, remove the backer from the old backedParticipant's set of backers.
        EnumerableSet.remove(_backers[oldBackedParticipant], backer);

        // Add the backer to the new backedParticipant's set of backers.
        if (backedParticipant != address(0)){
            EnumerableSet.add(_backers[backedParticipant], backer);
        }

        success = true;
        emit BackedParticipantUpdated(challengeNumber, backer, backedParticipant);
    }

    function submitNewPredictions(bytes32 submissionHash)
    external override
    returns (uint32 challengeNumber)
    {
        uint256 currentBal = _stakes[msg.sender];
        require(currentBal >= _stakeThreshold, "Competition - submitNewPredictions: Stake is below threshold.");
        challengeNumber = _updateSubmission(bytes32(0), submissionHash);
        EnumerableSet.add(_challenges[challengeNumber].submitters, msg.sender);
    }

    function updateSubmission(bytes32 oldSubmissionHash, bytes32 newSubmissionHash)
    external override
    returns (uint32 challengeNumber)
    {
        require(oldSubmissionHash != bytes32(0), "Competition - updateSubmission: Must have pre-existing submission.");
        challengeNumber = _updateSubmission(oldSubmissionHash, newSubmissionHash);

        if (newSubmissionHash == bytes32(0)){
            EnumerableSet.remove(_challenges[challengeNumber].submitters, msg.sender);
        }
    }

    function _updateSubmission(bytes32 oldSubmissionHash, bytes32 newSubmissionHash)
    private
    returns (uint32 challengeNumber)
    {
        challengeNumber = _challengeCounter;
        require(_challenges[challengeNumber].phase == 1, "Competition - updateSubmission: Not available for submissions.");
        require(oldSubmissionHash != newSubmissionHash, "Competition - updateSubmission: Cannot update with the same hash as before.");
        require(_challenges[challengeNumber].submitterInfo[msg.sender].submission == oldSubmissionHash,
                "Competition - updateSubmission: Clash in existing submission hash.");
        _challenges[challengeNumber].submitterInfo[msg.sender].submission = newSubmissionHash;

        emit SubmissionUpdated(challengeNumber, msg.sender, newSubmissionHash);
    }

    /**
    ORGANIZER WRITE METHODS
    **/
    function updateMessage(string calldata newMessage)
    external override onlyAdmin
    returns (bool success)
    {
        _message = newMessage;
        success = true;

        emit MessageUpdated();
    }

    function updateDeadlines(uint32 challengeNumber, uint256 index, uint256 timestamp)
    external override onlyAdmin
    returns (bool success)
    {
        success = _updateDeadlines(challengeNumber, index, timestamp);
    }

    function _updateDeadlines(uint32 challengeNumber, uint256 index, uint256 timestamp)
    private
    returns (bool success)
    {
        _challenges[challengeNumber].deadlines[index] = timestamp;
        success = true;
    }

    function updateRewardsThreshold(uint256 newThreshold)
    external override onlyAdmin
    returns (bool success)
    {
        _rewardsThreshold = newThreshold;
        success = true;

        emit RewardsThresholdUpdated(newThreshold);
    }

    function updateStakeThreshold(uint256 newStakeThreshold)
    external override onlyAdmin
    returns (bool success)
    {
        _stakeThreshold = newStakeThreshold;
        success = true;

        emit StakeThresholdUpdated(newStakeThreshold);
    }

    function updateChallengeRewardsPercentageInWei(uint256 newPercentage)
    external override onlyAdmin
    returns (bool success)
    {
        _challengeRewardsPercentageInWei = newPercentage;
        success = true;

        emit ChallengeRewardsPercentageInWeiUpdated(newPercentage);
    }

    function updateTournamentRewardsPercentageInWei(uint256 newPercentage)
    external override onlyAdmin
    returns (bool success)
    {
        _tournamentRewardsPercentageInWei = newPercentage;
        success = true;

        emit TournamentRewardsPercentageInWeiUpdated(newPercentage);
    }


    function updatePrivateKey(uint32 challengeNumber, bytes32 newKeyHash)
    external override onlyAdmin
    returns (bool success)
    {
        _challenges[challengeNumber].privateKey = newKeyHash;
        success = true;

        emit PrivateKeyUpdated(newKeyHash);
    }

    function openChallenge(bytes32 datasetHash, bytes32 keyHash, uint256 submissionCloseDeadline, uint256 nextChallengeDeadline)
    external override onlyAdmin
    returns (bool success)
    {
        uint32 challengeNumber = _challengeCounter;
        require(_challenges[challengeNumber].phase == 4, "Competition - openChallenge: Previous phase is incomplete.");
        require(_competitionPool >= _rewardsThreshold, "Competiton - openChallenge: Not enough rewards.");

        challengeNumber++;

        _challenges[challengeNumber].phase = 1;
        _challengeCounter = challengeNumber;

        _updateDataset(challengeNumber, bytes32(0), datasetHash);
        _updateKey(challengeNumber, bytes32(0), keyHash);

        _currentChallengeRewardsBudget = _competitionPool * _challengeRewardsPercentageInWei/(1e18);
        _currentTournamentRewardsBudget = _competitionPool * _tournamentRewardsPercentageInWei/(1e18);
        _currentStakingRewardsBudget = _competitionPool - _currentChallengeRewardsBudget - _currentTournamentRewardsBudget;

        _updateDeadlines(challengeNumber, 0, submissionCloseDeadline);
        _updateDeadlines(challengeNumber, 1, nextChallengeDeadline);

        challengeOpenedBlockNumbers[challengeNumber] = block.number;

        success = true;

        emit ChallengeOpened(challengeNumber);
    }

    function updateDataset(bytes32 oldDatasetHash, bytes32 newDatasetHash)
    external override onlyAdmin
    returns (bool success)
    {
        uint32 challengeNumber = _challengeCounter;
        require(_challenges[challengeNumber].phase == 1, "Competition - updateDataset: Challenge is closed.");
        require(oldDatasetHash != bytes32(0), "Competition - updateDataset: Must have pre-existing dataset.");
        success = _updateDataset(challengeNumber, oldDatasetHash, newDatasetHash);
    }

    function updateKey(bytes32 oldKeyHash, bytes32 newKeyHash)
    external override onlyAdmin
    returns (bool success)
    {
        uint32 challengeNumber = _challengeCounter;
        require(_challenges[challengeNumber].phase == 1, "Competition - updateKey: Challenge is closed.");
        require(oldKeyHash != bytes32(0), "Competition - updateKey: Must have pre-existing key.");
        success = _updateKey(challengeNumber, oldKeyHash, newKeyHash);
    }

    function _updateDataset(uint32 challengeNumber, bytes32 oldDatasetHash, bytes32 newDatasetHash)
    private
    returns (bool success)
    {
        require(oldDatasetHash != newDatasetHash, "Competition - updateDataset: Cannot update with the same hash as before.");
        require(_challenges[challengeNumber].dataset == oldDatasetHash, "Competition - updateDataset: Incorrect old dataset reference.");
        _challenges[challengeNumber].dataset = newDatasetHash;
        success = true;

        emit DatasetUpdated(challengeNumber, oldDatasetHash, newDatasetHash);
    }

    function _updateKey(uint32 challengeNumber, bytes32 oldKeyHash, bytes32 newKeyHash)
    private
    returns (bool success)
    {
        require(oldKeyHash != newKeyHash, "Competition - _updateKey: Cannot update with the same hash as before.");
        require(_challenges[challengeNumber].key == oldKeyHash, "Competition - _updateKey: Incorrect old key reference.");
        _challenges[challengeNumber].key = newKeyHash;
        success = true;

        emit KeyUpdated(challengeNumber, oldKeyHash, newKeyHash);
    }

    function closeSubmission()
    external override onlyAdmin
    returns (bool success)
    {
        uint32 challengeNumber = _challengeCounter;
        require(_challenges[challengeNumber].phase == 1, "Competition - closeSubmission: Challenge in unexpected state.");
        _challenges[challengeNumber].phase = 2;
        submissionClosedBlockNumbers[challengeNumber] = block.number;
        success = true;

        emit SubmissionClosed(challengeNumber);
    }

    function submitResults(bytes32 resultsHash)
    external override onlyAdmin
    returns (bool success)
    {
        success = _updateResults(bytes32(0), resultsHash);
    }

    function updateResults(bytes32 oldResultsHash, bytes32 newResultsHash)
    external override onlyAdmin
    returns (bool success)
    {
        require(oldResultsHash != bytes32(0), "Competition - updateResults: Must have pre-existing results.");
        success = _updateResults(oldResultsHash, newResultsHash);
    }

    function _updateResults(bytes32 oldResultsHash, bytes32 newResultsHash)
    private
    returns (bool success)
    {
        require(oldResultsHash != newResultsHash, "Competition - updateResults: Cannot update with the same hash as before.");
        uint32 challengeNumber = _challengeCounter;
        require(_challenges[challengeNumber].phase >= 3, "Competition - updateResults: Challenge in unexpected state.");
        require(_challenges[challengeNumber].results == oldResultsHash, "Competition - updateResults: Clash in existing results hash.");
        _challenges[challengeNumber].results = newResultsHash;
        success = true;

        emit ResultsUpdated(challengeNumber, oldResultsHash, newResultsHash);
    }

    function payRewards(address[] calldata submitters, uint256[] calldata stakingRewards, uint256[] calldata challengeRewards, uint256[] calldata tournamentRewards)
    external override onlyAdmin
    returns (bool success)
    {
        success = _payRewards(_challengeCounter, submitters, stakingRewards, challengeRewards, tournamentRewards);
    }

    function _payRewards(uint32 challengeNumber, address[] calldata submitters, uint256[] calldata stakingRewards, uint256[] calldata challengeRewards, uint256[] calldata tournamentRewards)
    private
    returns (bool success)
    {
        require(_challenges[challengeNumber].phase >= 3, "Competition - payRewards: Challenge is in unexpected state.");
        require((submitters.length == stakingRewards.length) &&
            (submitters.length == challengeRewards.length) &&
            (submitters.length == tournamentRewards.length),
            "Competition - payRewards: Number of submitters and rewards are different.");

        uint256 totalStakingAmount;
        uint256 totalChallengeAmount;
        uint256 totalTournamentAmount;

        for (uint i = 0; i < submitters.length; i++)
        {
            // read directly from the list since the list is already in memory(calldata), and to avoid stack too deep errors.
            totalStakingAmount += stakingRewards[i];
            totalChallengeAmount += challengeRewards[i];
            totalTournamentAmount += tournamentRewards[i];

            _paySingleAddress(challengeNumber, submitters[i], stakingRewards[i], challengeRewards[i], tournamentRewards[i]);
        }

        // allow for reverting on underflow
        _currentStakingRewardsBudget -= totalStakingAmount;
        _currentChallengeRewardsBudget -= totalChallengeAmount;
        _currentTournamentRewardsBudget -= totalTournamentAmount;

        _competitionPool -= totalStakingAmount + totalChallengeAmount + totalTournamentAmount;
        _currentTotalStaked += totalStakingAmount + totalChallengeAmount + totalTournamentAmount;
        success = true;

        _logRewardsPaid(challengeNumber, totalStakingAmount, totalChallengeAmount, totalTournamentAmount);
    }

    function _paySingleAddress(uint32 challengeNumber, address submitter, uint256 stakingReward, uint256 challengeReward, uint256 tournamentReward)
    private
    {
        _stakes[submitter] += stakingReward + challengeReward + tournamentReward;

        if (stakingReward > 0){
            _challenges[challengeNumber].submitterInfo[submitter].stakingRewards += stakingReward;
        }

        if (challengeReward > 0){
            _challenges[challengeNumber].submitterInfo[submitter].challengeRewards += challengeReward;
        }

        if (tournamentReward > 0){
            _challenges[challengeNumber].submitterInfo[submitter].tournamentRewards += tournamentReward;
        }

        emit RewardsPayment(challengeNumber, submitter, stakingReward, challengeReward, tournamentReward);
    }

    function _logRewardsPaid(uint32 challengeNumber, uint256 totalStakingAmount, uint256 totalChallengeAmount, uint256 totalTournamentAmount)
    private
    {
        emit TotalRewardsPaid(challengeNumber, totalStakingAmount, totalChallengeAmount, totalTournamentAmount);
    }

    function updateChallengeAndTournamentScores(uint32 challengeNumber, address[] calldata participants, uint256[] calldata challengeScores, uint256[] calldata tournamentScores)
    external override onlyAdmin
    returns (bool success)
    {
        require(_challenges[challengeNumber].phase >= 3, "Competition - updateChallengeAndTournamentScores: Challenge is in unexpected state.");
        require((participants.length == challengeScores.length) && (participants.length == tournamentScores.length), "Competition - updateChallengeAndTournamentScores: Number of participants and scores are different.");

        for (uint i = 0; i < participants.length; i++)
        {
        // read directly from the list since the list is already in memory(calldata), and to avoid stack too deep errors.

            _challenges[challengeNumber].submitterInfo[participants[i]].challengeScores = challengeScores[i];
            _challenges[challengeNumber].submitterInfo[participants[i]].tournamentScores = tournamentScores[i];
        }

        success = true;

        emit ChallengeAndTournamentScoresUpdated(challengeNumber);
    }

    function updateInformationBatch(uint32 challengeNumber, address[] calldata participants, uint256 itemNumber, uint[] calldata values)
    external override onlyAdmin
    returns (bool success)
    {
        require(_challenges[challengeNumber].phase >= 3, "Competition - updateInformationBatch: Challenge is in unexpected state.");
        require(participants.length == values.length, "Competition - updateInformationBatch: Number of participants and values are different.");

        for (uint i = 0; i < participants.length; i++)
        {
            _challenges[challengeNumber].submitterInfo[participants[i]].info[itemNumber] = values[i];
        }
        success = true;

        emit BatchInformationUpdated(challengeNumber, itemNumber);
    }

    function advanceToPhase(uint8 phase)
    external override onlyAdmin
    returns (bool success)
    {
        uint32 challengeNumber = _challengeCounter;
        require((2 < phase) && (phase < 5), "Competition - advanceToPhase: You may only use this method for advancing to phases 3 or 4." );
        require((phase-1) == _challenges[challengeNumber].phase, "Competition - advanceToPhase: You may only advance to the next phase.");
        _challenges[challengeNumber].phase = phase;

        success = true;
    }

    function moveRemainderToPool()
    external override onlyAdmin
    returns (bool success)
    {
        require(_challenges[_challengeCounter].phase == 4, "Competition - moveRemainderToPool: PLease wait for the challenge to complete before sponsoring.");
        uint256 remainder = getRemainder();
        require(remainder > 0, "Competition - moveRemainderToPool: No remainder to move.");
        _competitionPool += remainder;
        success = true;

        emit RemainderMovedToPool(remainder);
    }

    function updateChallengeOpenedBlockNumbers(uint32 challengeNumber, uint256 blockNumber)
    external override onlyAdmin
    returns (bool success)
    {
        challengeOpenedBlockNumbers[challengeNumber] = blockNumber;
        success = true;
    }

    function updateSubmissionClosedBlockNumbers(uint32 challengeNumber, uint256 blockNumber)
    external override onlyAdmin
    returns (bool success)
    {
        submissionClosedBlockNumbers[challengeNumber] = blockNumber;
        success = true;
    }

    function updateStakerSet(address[] calldata toRemove, address[] calldata toAdd)
    external override onlyAdmin
    returns (bool success)
    {
        for (uint i = 0; i < toRemove.length; i++){
            EnumerableSet.remove(stakerSet, toRemove[i]);
        }

        for (uint i = 0; i < toAdd.length; i++){
            EnumerableSet.add(stakerSet, toAdd[i]);
        }
        success = true;
    }

    function updateHistoricalStakedAmounts(uint32 historicalChallengeNumber, address[] calldata stakers, uint256[] calldata amounts)
    external override onlyAdmin
    returns (bool success)
    {
        require(_challenges[_challengeCounter].phase >= 2, "Competition - updateHistoricalStakedAmounts: Challenge is in unexpected state.");
        require((stakers.length == amounts.length), "Competition - updateHistoricalStakedAmounts: Number of submitters and rewards are different.");

        for (uint i = 0; i < stakers.length; i++){
            _historicalStakeAmounts[historicalChallengeNumber][stakers[i]] = amounts[i];
            if (amounts[i] > 0){
                EnumerableSet.add(_historicalStakerSet[historicalChallengeNumber], stakers[i]);
            } else {
                EnumerableSet.remove(_historicalStakerSet[historicalChallengeNumber], stakers[i]);
            }
        }

        emit HistoricalStakedAmountsUpdated(historicalChallengeNumber);
    }

    function recordStakes(uint256 startIndex, uint256 endIndex)
    external override onlyAdmin
    returns (bool success)
    {
        uint32 challengeNumber = _challengeCounter;
        require(_challenges[challengeNumber].phase >= 2, "Competition - closeSubmission: Challenge in unexpected state.");
        for (uint i = startIndex; i < endIndex; i++){
            address staker = (EnumerableSet.at(stakerSet, i));
            EnumerableSet.add(_historicalStakerSet[challengeNumber], staker);
            _historicalStakeAmounts[challengeNumber][staker] = _stakes[staker];
        }
        success = true;
    }

    function alignBacking(address[] calldata backers)
    external override onlyAdmin
    returns (bool success)
    {
        for (uint i = 0; i < backers.length; i++){
            address backedParticipant = _backed[backers[i]];
            uint256 stake = _stakes[backers[i]];
            if ((stake == 0) && (backedParticipant != address(0))){
                _updateBackedParticipant(address(0), backers[i], backedParticipant);
            }
            else if ((stake > 0) && (backedParticipant == address(0))){
                _updateBackedParticipant(backers[i], backers[i], backedParticipant);
            }
        }
        success = true;
    }

    /**
    READ METHODS
    **/

    function getCompetitionPool()
    view external override
    returns (uint256 competitionPool)
    {
        competitionPool = _competitionPool;
    }

    function getRewardsThreshold()
    view external override
    returns (uint256 rewardsThreshold)
    {
        rewardsThreshold = _rewardsThreshold;
    }

    function getCurrentTotalStaked()
    view external override
    returns (uint256 currentTotalStaked)
    {
        currentTotalStaked = _currentTotalStaked;
    }

    function getCurrentStakingRewardsBudget()
    view external override
    returns (uint256 currentStakingRewardsBudget)
    {
        currentStakingRewardsBudget = _currentStakingRewardsBudget;
    }

    function getCurrentChallengeRewardsBudget()
    view external override
    returns (uint256 currentChallengeRewardsBudget)
    {
        currentChallengeRewardsBudget = _currentChallengeRewardsBudget;
    }

    function getCurrentTournamentRewardsBudget()
    view external override
    returns (uint256 currentTournamentRewardsBudget)
    {
        currentTournamentRewardsBudget = _currentTournamentRewardsBudget;
    }

    function getChallengeRewardsPercentageInWei()
    view external override
    returns (uint256 challengeRewardsPercentageInWei)
    {
        challengeRewardsPercentageInWei = _challengeRewardsPercentageInWei;
    }

    function getTournamentRewardsPercentageInWei()
    view external override
    returns (uint256 tournamentRewardsPercentageInWei)
    {
        tournamentRewardsPercentageInWei = _tournamentRewardsPercentageInWei;
    }

    function getLatestChallengeNumber()
    view external override
    returns (uint32 latestChallengeNumber)
    {
        latestChallengeNumber = _challengeCounter;
    }

    function getDatasetHash(uint32 challengeNumber)
    view external override
    returns (bytes32 dataset)
    {
        dataset = _challenges[challengeNumber].dataset;
    }

    function getResultsHash(uint32 challengeNumber)
    view external override
    returns (bytes32 results)
    {
        results = _challenges[challengeNumber].results;
    }

    function getKeyHash(uint32 challengeNumber)
    view external override
    returns (bytes32 key)
    {
        key = _challenges[challengeNumber].key;
    }

    function getPrivateKeyHash(uint32 challengeNumber)
    view external override
    returns (bytes32 privateKey)
    {
        privateKey = _challenges[challengeNumber].privateKey;
    }

    function getSubmissionCounter(uint32 challengeNumber)
    view public override
    returns (uint256 submissionCounter)
    {
        submissionCounter = EnumerableSet.length(_challenges[challengeNumber].submitters);
    }

    function getSubmitters(uint32 challengeNumber, uint256 startIndex, uint256 endIndex)
    view public override
    returns (address[] memory)
    {
        EnumerableSet.AddressSet storage submittersSet = _challenges[challengeNumber].submitters;
        return _getListFromSet(submittersSet, startIndex, endIndex);
    }

    function getAllSubmitters(uint32 challengeNumber)
    view external override
    returns (address[] memory)
    {
        return getSubmitters(challengeNumber, 0, getSubmissionCounter(challengeNumber));
    }

    function getPhase(uint32 challengeNumber)
    view external override
    returns (uint8 phase)
    {
        phase = _challenges[challengeNumber].phase;
    }

    function getStakeThreshold()
    view external override
    returns (uint256 stakeThreshold)
    {
        stakeThreshold = _stakeThreshold;
    }

    function getStake(address participant)
    view external override
    returns (uint256 stake)
    {
        stake = _stakes[participant];
    }

    function getTokenAddress()
    view external override
    returns (address tokenAddress)
    {
        tokenAddress = address(_token);
    }

    function getSubmission(uint32 challengeNumber, address participant)
    view external override
    returns (bytes32 submissionHash)
    {
        submissionHash = _challenges[challengeNumber].submitterInfo[participant].submission;
    }

    // This is no longer in use. Keeping the function so that the data layout will be the same in ICompetition.
    function getStakedAmountForChallenge(uint32 challengeNumber, address participant)
    view external override
    returns (uint256 staked)
    {
//        staked = _challenges[challengeNumber].submitterInfo[participant].staked;
        staked = 0;
    }

    function getStakingRewards(uint32 challengeNumber, address participant)
    view external override
    returns (uint256 stakingRewards)
    {
        stakingRewards = _challenges[challengeNumber].submitterInfo[participant].stakingRewards;
    }

    function getChallengeRewards(uint32 challengeNumber, address participant)
    view external override
    returns (uint256 challengeRewards)
    {
        challengeRewards = _challenges[challengeNumber].submitterInfo[participant].challengeRewards;
    }

    function getTournamentRewards(uint32 challengeNumber, address participant)
    view external override
    returns (uint256 tournamentRewards)
    {
        tournamentRewards = _challenges[challengeNumber].submitterInfo[participant].tournamentRewards;
    }

    function getOverallRewards(uint32 challengeNumber, address participant)
    view external override
    returns (uint256 overallRewards)
    {
        overallRewards =
        _challenges[challengeNumber].submitterInfo[participant].stakingRewards
        + _challenges[challengeNumber].submitterInfo[participant].challengeRewards
        + _challenges[challengeNumber].submitterInfo[participant].tournamentRewards;
    }

    function getChallengeScores(uint32 challengeNumber, address participant)
    view external override
    returns (uint256 challengeScores)
    {
        challengeScores = _challenges[challengeNumber].submitterInfo[participant].challengeScores;
    }

    function getTournamentScores(uint32 challengeNumber, address participant)
    view external override
    returns (uint256 tournamentScores)
    {
        tournamentScores = _challenges[challengeNumber].submitterInfo[participant].tournamentScores;
    }

    function getInformation(uint32 challengeNumber, address participant, uint256 itemNumber)
    view external override
    returns (uint value)
    {
        value = _challenges[challengeNumber].submitterInfo[participant].info[itemNumber];
    }

    function getDeadlines(uint32 challengeNumber, uint256 index)
    view external override
    returns (uint256 deadline)
    {
        deadline = _challenges[challengeNumber].deadlines[index];
    }

    function getRemainder()
    view public override
    returns (uint256 remainder)
    {
        remainder = _token.balanceOf(address(this)) - _currentTotalStaked - _competitionPool;
    }

    function getMessage()
    view external override
    returns (string memory message)
    {
        message = _message;
    }

    function _getListFromSet(EnumerableSet.AddressSet storage setOfData, uint256 startIndex, uint256 endIndex)
    view internal
    returns (address[] memory)
    {
        address[] memory listOfData = new address[](endIndex - startIndex);
        for (uint i = startIndex; i < endIndex; i++){
            listOfData[i - startIndex] = (EnumerableSet.at(setOfData, i));
        }
        return listOfData;
    }

    function getHistoricalStakersCounter(uint32 challengeNumber)
    view public override
    returns (uint256 stakersCounter)
    {
        stakersCounter = EnumerableSet.length(_historicalStakerSet[challengeNumber]);
    }

    function getHistoricalStakersPartial(uint32 challengeNumber, uint256 startIndex, uint256 endIndex)
    view public override
    returns (address[] memory)
    {
        return _getListFromSet(_historicalStakerSet[challengeNumber], startIndex, endIndex);
    }

    function getHistoricalStakers(uint32 challengeNumber)
    view external override
    returns (address[] memory)
    {
        return getHistoricalStakersPartial(challengeNumber, 0, getHistoricalStakersCounter(challengeNumber));
    }

    function getHistoricalStakeAmounts(uint32 challengeNumber, address[] calldata stakers)
    view external override
    returns (uint256[] memory)
    {
        uint256[] memory stakeAmountList = new uint256[](stakers.length);
        for (uint i = 0; i < stakers.length; i++){
            stakeAmountList[i] = _historicalStakeAmounts[challengeNumber][stakers[i]];
        }
        return stakeAmountList;
    }

    function getBackedParticipant(address backer)
    view external override
    returns (address backedParticipant)
    {
        backedParticipant = _backed[backer];
    }

    function getBackersCounter(address backedParticipant)
    view public override
    returns (uint256 backersCounter)
    {
        backersCounter = EnumerableSet.length(_backers[backedParticipant]);
    }

    function getBackers(address backedParticipant, uint256 startIndex, uint256 endIndex)
    view public override
    returns (address[] memory)
    {
        EnumerableSet.AddressSet storage backersSet = _backers[backedParticipant];
        return _getListFromSet(backersSet, startIndex, endIndex);
    }

    function getAllBackers(address backedParticipant)
    view external override
    returns (address[] memory)
    {
        return getBackers(backedParticipant, 0, getBackersCounter(backedParticipant));
    }

    function getBackingTotal(address backedParticipant)
    view external override
    returns (uint256 totalAmount)
    {
        totalAmount = 0;
        EnumerableSet.AddressSet storage backersSet = _backers[backedParticipant];
        for (uint i = 0; i < getBackersCounter(backedParticipant); i++){
            totalAmount += _stakes[EnumerableSet.at(backersSet, i)];
        }
    }

    function getStakersCounter()
    view public override
    returns (uint256 stakersCounter)
    {
        stakersCounter = EnumerableSet.length(stakerSet);
    }

    function getStakers(uint256 startIndex, uint256 endIndex)
    view public override
    returns (address[] memory)
    {
        return _getListFromSet(stakerSet, startIndex, endIndex);
    }

    function getAllStakers()
    view external override
    returns (address[] memory)
    {
        return getStakers(0, getStakersCounter());
    }

    /**
    METHODS CALLABLE BY BOTH ADMIN AND PARTICIPANTS.
    **/

    function sponsor(uint256 amountToken)
    external override
    returns (bool success)
    {
        require(_challenges[_challengeCounter].phase == 4, "Competition - sponsor: PLease wait for the challenge to complete before sponsoring.");
        uint256 currentCompPoolAmt = _competitionPool;
        _competitionPool = currentCompPoolAmt + amountToken;
        success = _token.transferFrom(msg.sender, address(this), amountToken);

        emit Sponsor(msg.sender, amountToken, currentCompPoolAmt + amountToken);
    }
}