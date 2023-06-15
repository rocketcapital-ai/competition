pragma solidity ^0.8.4;

// SPDX-License-Identifier: MIT

import './../interfaces/ICompetition.sol';
import './../interfaces/ICompetitionV2.sol';
import './../interfaces/IToken.sol';
import './CompetitionStorage.sol';
import './AccessControlRci.sol';
import "OpenZeppelin/openzeppelin-contracts@4.8.0/contracts/proxy/utils/Initializable.sol";
import './UniqueMappings.sol';

/**
 * @title RCI Tournament(Competition) Contract
 * @author Rocket Capital Investment Pte Ltd
 * @dev This contract manages registration and reward payouts for the RCI Tournament.
 * @dev IPFS hash format: Hash Identifier (2 bytes), Actual Hash (May eventually take on other formats but currently 32 bytes)
 *
 */
contract Competition is AccessControlRci, ICompetition, CompetitionStorage, Initializable, ICompetitionV2, UniqueMappings {

    function initialize(uint256 stakeThreshold_, uint256 rewardsThreshold_, address tokenAddress_)
    external
    initializer
    {
        require(tokenAddress_ != address(0), "No token address found.");
        _initializeRciAdmin(msg.sender);
        _stakeThreshold = stakeThreshold_;
        _rewardsThreshold = rewardsThreshold_;
        _token = IToken(tokenAddress_);
        _challengeCounter = 0;
        _challenges[_challengeCounter].phase = 4;
    }

    /**
    PARTICIPANT WRITE METHODS
    **/

    function increaseStake(address staker, uint256 amountToken)
    external override
    returns (bool success)
    {
        uint32 challengeNumber = _challengeCounter;
        require(msg.sender == address(_token), "TKCL");
        require(_challenges[challengeNumber].phase == 1, "STUK");
        // allow for amountToken = 0 so that `stakeAndSubmit` can be called with the same stake.
        // users might want to set their stakes to the same amount while changing their submission.

        uint256 currentBal = _stakes[staker];

        _stakes[staker] = currentBal + amountToken;
        _currentTotalStaked += amountToken;

        EnumerableSet.add(stakerSet, staker);

        require(((currentBal + amountToken) >= _stakeThreshold), "MIN");

        success = true;

        emit StakeIncreased(staker, amountToken);
    }

    function decreaseStake(address staker, uint256 amountToken)
    external override
    returns (bool success)
    {
        uint32 challengeNumber = _challengeCounter;
        require(msg.sender == address(_token), "TKCL");
        require(_challenges[_challengeCounter].phase == 1, "STUK");
        // allow for amountToken = 0 so that `stakeAndSubmit` can be called with the same stake.
        // users might want to set their stakes to the same amount while changing their submission.

        uint256 currentBal = _stakes[staker];
        require(amountToken <= currentBal, "Insufficient funds.");

        require(((currentBal - amountToken) == 0) ||
            ((currentBal - amountToken) >= _stakeThreshold), "MIN");

        bool submissionExists = _challenges[challengeNumber].submitterInfo[staker].submission != bytes32(0);

        if ((currentBal - amountToken) == 0){
            require(!submissionExists, "SBBK");
            EnumerableSet.remove(stakerSet, staker);
        }

        _stakes[staker] = currentBal - amountToken;
        _currentTotalStaked -= amountToken;
        success = _token.transfer(staker, amountToken);

        emit StakeDecreased(staker, amountToken);
    }

    function submit(address staker, bytes32 submissionHash)
    external override
    returns (uint32 challengeNumber)
    {
        require(msg.sender == address(_token), "TKCL");
        challengeNumber = _updateSubmission(staker, submissionHash);

        if (submissionHash == bytes32(0)){
            EnumerableSet.remove(_challenges[challengeNumber].submitters, staker);
        } else {
            EnumerableSet.add(_challenges[challengeNumber].submitters, staker);
        }
    }

    function _updateSubmission(address staker, bytes32 newSubmissionHash)
    private
    returns (uint32 challengeNumber)
    {
        challengeNumber = _challengeCounter;
        require(_challenges[challengeNumber].phase == 1, "WGPH");
        _challenges[challengeNumber].submitterInfo[staker].submission = newSubmissionHash;

        emit SubmissionUpdated(challengeNumber, staker, newSubmissionHash);
    }

    /**
    ADMIN WRITE METHODS
    **/
    function updateVault(address vault)
    external override onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        _vault = vault;
        success = true;

        emit VaultUpdated(vault);
    }

    function updateMessage(string calldata newMessage)
    external override onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        _message = newMessage;
        success = true;

        emit MessageUpdated();
    }

    function updateDeadlines(uint32 challengeNumber, uint256 index, uint256 timestamp)
    external override onlyRole(RCI_CHILD_ADMIN)
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
    external override onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        _rewardsThreshold = newThreshold;
        success = true;

        emit RewardsThresholdUpdated(newThreshold);
    }

    function updateStakeThreshold(uint256 newStakeThreshold)
    external override onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        _stakeThreshold = newStakeThreshold;
        success = true;

        emit StakeThresholdUpdated(newStakeThreshold);
    }

    function updatePrivateKey(uint32 challengeNumber, bytes32 newKeyHash)
    external override onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        _challenges[challengeNumber].privateKey = newKeyHash;
        success = true;

        emit PrivateKeyUpdated(newKeyHash);
    }

    function openChallenge(bytes32 datasetHash, bytes32 keyHash, uint256 submissionCloseDeadline, uint256 nextChallengeDeadline)
    external override onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        uint32 challengeNumber = _challengeCounter;
        require(_challenges[challengeNumber].phase == 4, "WGPH");
        require(_competitionPool >= _rewardsThreshold, "NORW");

        challengeNumber++;

        _challenges[challengeNumber].phase = 1;
        _challengeCounter = challengeNumber;

        _updateDataset(challengeNumber, datasetHash);
        _updateKey(challengeNumber, keyHash);

        _updateDeadlines(challengeNumber, 0, submissionCloseDeadline);
        _updateDeadlines(challengeNumber, 1, nextChallengeDeadline);

        challengeOpenedBlockNumbers[challengeNumber] = block.number;
        success = true;
        emit ChallengeOpened(challengeNumber);
    }

    function updateDataset(bytes32 newDatasetHash)
    external override onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        uint32 challengeNumber = _challengeCounter;
        success = _updateDataset(challengeNumber, newDatasetHash);
    }

    function updateKey(bytes32 newKeyHash)
    external override onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        uint32 challengeNumber = _challengeCounter;
        success = _updateKey(challengeNumber, newKeyHash);
    }

    function _updateDataset(uint32 challengeNumber, bytes32 newDatasetHash)
    private
    returns (bool success)
    {
        bytes32 oldDatasetHash = _challenges[challengeNumber].dataset;
        require(_challenges[challengeNumber].phase == 1, "WGPH");
        require(oldDatasetHash != newDatasetHash, "HHST");
        require(!_datasetHashes[newDatasetHash], "DTST");
        _challenges[challengeNumber].dataset = newDatasetHash;
        _datasetHashes[newDatasetHash] = true;
        success = true;

        emit DatasetUpdated(challengeNumber, oldDatasetHash, newDatasetHash);
    }

    function _updateKey(uint32 challengeNumber, bytes32 newKeyHash)
    private
    returns (bool success)
    {
        bytes32 oldKeyHash = _challenges[challengeNumber].key;
        require(_challenges[challengeNumber].phase == 1, "WGPH");
        require(oldKeyHash != newKeyHash, "HHST");
        require(!_publicKeyHashes[newKeyHash], "PBKY");
        _challenges[challengeNumber].key = newKeyHash;
        _publicKeyHashes[newKeyHash] = true;
        success = true;

        emit KeyUpdated(challengeNumber, oldKeyHash, newKeyHash);
    }

    function closeSubmission()
    external override onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        uint32 challengeNumber = _challengeCounter;
        require(_challenges[challengeNumber].phase == 1, "PH1");
        _challenges[challengeNumber].phase = 2;
        submissionClosedBlockNumbers[challengeNumber] = block.number;
        success = true;

        emit SubmissionClosed(challengeNumber);
    }

    function submitResults(bytes32 resultsHash)
    external override onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        success = _updateResults(bytes32(0), resultsHash);
    }

    function updateResults(bytes32 oldResultsHash, bytes32 newResultsHash)
    external override onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        require(oldResultsHash != bytes32(0), "NORS");
        success = _updateResults(oldResultsHash, newResultsHash);
    }

    function _updateResults(bytes32 oldResultsHash, bytes32 newResultsHash)
    private
    returns (bool success)
    {
        require(oldResultsHash != newResultsHash, "HHST");
        uint32 challengeNumber = _challengeCounter;
        require(_challenges[challengeNumber].phase >= 3, "WGPH");
        require(_challenges[challengeNumber].results == oldResultsHash, "HHER");
        _challenges[challengeNumber].results = newResultsHash;
        success = true;

        emit ResultsUpdated(challengeNumber, oldResultsHash, newResultsHash);
    }

    function payRewards(address[] calldata submitters, uint256[] calldata stakingRewards,
                        uint256[] calldata challengeRewards, uint256[] calldata tournamentRewards)
    external override onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        success = _payRewards(_challengeCounter, submitters, stakingRewards, challengeRewards, tournamentRewards);
    }

    function burn(address[] calldata submitters, uint256[] calldata burnAmounts)
    external override onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        success = _burn(_challengeCounter, submitters, burnAmounts);
    }

    function _payRewards(uint32 challengeNumber, address[] calldata submitters, uint256[] calldata stakingRewards,
                            uint256[] calldata challengeRewards, uint256[] calldata tournamentRewards)
    private
    returns (bool success)
    {
        require(_challenges[challengeNumber].phase == 3, "WGPH");
        require((submitters.length == stakingRewards.length) &&
            (submitters.length == challengeRewards.length) &&
            (submitters.length == tournamentRewards.length),
            "ARER");

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

        _competitionPool -= totalStakingAmount + totalChallengeAmount + totalTournamentAmount;
        _currentTotalStaked += totalStakingAmount + totalChallengeAmount + totalTournamentAmount;
        challengePayments[challengeNumber] += totalStakingAmount + totalChallengeAmount + totalTournamentAmount;
        success = true;

        _logRewardsPaid(challengeNumber, totalStakingAmount, totalChallengeAmount, totalTournamentAmount);
    }

    function _burn(uint32 challengeNumber, address[] calldata submitters, uint256[] calldata burnAmounts)
    private
    returns (bool success)
    {
        require(_challenges[challengeNumber].phase == 3, "WGPH");
        require((submitters.length == burnAmounts.length), "WGSL");

        uint256 totalBurnAmount;

        for (uint i = 0; i < submitters.length; i++)
        {
            // read directly from the list since the list is already in memory(calldata), and to avoid stack too deep errors.
            totalBurnAmount += burnAmounts[i];
            _burnSingleAddress(challengeNumber, submitters[i], burnAmounts[i]);
        }

        // allow for reverting on underflow
        _burnedAmount += totalBurnAmount;
        _currentTotalStaked -= totalBurnAmount;
        challengeBurns[challengeNumber] += totalBurnAmount;
        success = true;
    }

    function _paySingleAddress(uint32 challengeNumber, address submitter, uint256 stakingReward,
                                uint256 challengeReward, uint256 tournamentReward)
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


    function _burnSingleAddress(uint32 challengeNumber, address submitter, uint256 burnAmount)
    private
    {
        _stakes[submitter] -= burnAmount;
        uint256 alreadyBurned = _challenges[challengeNumber].submitterInfo[submitter].tokensBurned;
        if (burnAmount > 0){
            _challenges[challengeNumber].submitterInfo[submitter].tokensBurned = burnAmount + alreadyBurned;
        }

        emit Burned(challengeNumber, submitter, burnAmount);
    }

    function _logRewardsPaid(uint32 challengeNumber, uint256 totalStakingAmount, uint256 totalChallengeAmount, uint256 totalTournamentAmount)
    private
    {
        emit TotalRewardsPaid(challengeNumber, totalStakingAmount, totalChallengeAmount, totalTournamentAmount);
    }

    function updateChallengeAndTournamentScores(uint32 challengeNumber, address[] calldata participants, uint256[] calldata challengeScores, uint256[] calldata tournamentScores)
    external override onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        require(_challenges[challengeNumber].phase >= 3, "WGPH");
        require((participants.length == challengeScores.length) && (participants.length == tournamentScores.length),
            "ARER");

        for (uint i = 0; i < participants.length; i++)
        {
        // read directly from the list since the list is already in memory(calldata), and to avoid stack too deep errors.

            _challenges[challengeNumber].submitterInfo[participants[i]].challengeScores = challengeScores[i];
            _challenges[challengeNumber].submitterInfo[participants[i]].tournamentScores = tournamentScores[i];
        }

        success = true;

        emit ChallengeAndTournamentScoresUpdated(challengeNumber);
    }

    function updateInformationBatch(uint32 challengeNumber, address[] calldata participants,
                                    uint256 itemNumber, uint[] calldata values)
    external override onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        require(_challenges[challengeNumber].phase >= 3, "WGPH");
        require(participants.length == values.length, "ARER");

        for (uint i = 0; i < participants.length; i++)
        {
            _challenges[challengeNumber].submitterInfo[participants[i]].info[itemNumber] = values[i];
        }
        success = true;

        emit BatchInformationUpdated(challengeNumber, itemNumber);
    }

    function advanceToPhase(uint8 phase)
    external override onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        uint32 challengeNumber = _challengeCounter;
        require((2 < phase) && (phase < 5)
                    && ((phase-1) == _challenges[challengeNumber].phase),
            "WGPH" );
        if (phase == 4){
            require((challengePayments[challengeNumber] > 0) && (challengeBurns[challengeNumber] > 0), "PYBN");
        }
        _challenges[challengeNumber].phase = phase;

        success = true;
    }

    function retreatToPhase(uint8 phase)
    external override onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        uint32 challengeNumber = _challengeCounter;
        require((0 < phase) && (phase < 4)
                    && ((phase + 1) == _challenges[challengeNumber].phase),
            "WGPH" );
        _challenges[challengeNumber].phase = phase;

        success = true;
    }

    function moveRemainderToPool()
    external override onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        require(_challenges[_challengeCounter].phase == 4, "WGPH");
        uint256 remainder = getRemainder();
        require(remainder > 0, "No remainder.");
        _competitionPool += remainder;
        success = true;

        emit RemainderMovedToPool(remainder);
    }

    function recordStakes(uint256 startIndex, uint256 endIndex)
    external override onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        uint32 challengeNumber = _challengeCounter;
        require(_challenges[challengeNumber].phase >= 2, "WGPH");
        for (uint i = startIndex; i < endIndex; i++){
            address staker = (EnumerableSet.at(stakerSet, i));
            uint256 stakeAmt = _stakes[staker];
            if (!EnumerableSet.contains(_historicalStakerSet[challengeNumber], staker)) {
                EnumerableSet.add(_historicalStakerSet[challengeNumber], staker);
                _historicalTotalStake[_challengeCounter] += stakeAmt;
            }
            _historicalStakeAmounts[challengeNumber][staker] = stakeAmt;
        }
        success = true;
    }

    function moveBurnedToPool(uint256 amount)
    external override onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        require(_challenges[_challengeCounter].phase == 4, "WGPH");
        require(amount <= _burnedAmount, "Not enough.");
        _burnedAmount -= amount;
        _competitionPool += amount;
        success = true;

        emit BurnedMoved(address(this), amount);
    }

    function moveBurnedOut(uint256 amount)
    external override onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        require(_challenges[_challengeCounter].phase == 4, "WGPH");
        require(amount <= _burnedAmount, "Not enough.");
        _burnedAmount -= amount;
        _token.transfer(_burnRecipient, amount);
        success = true;

        emit BurnedMoved(_burnRecipient, amount);
    }

    function updateBurnRecipient(address newBurnRecipient)
    external override onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        require(newBurnRecipient != address(this), "MBTP");
        _burnRecipient = newBurnRecipient;
        emit BurnRecipientUpdated(newBurnRecipient);
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

    function getStakedAmountForChallenge(uint32 challengeNumber, address participant)
    view external override
    returns (uint256 staked)
    {
        staked = _historicalStakeAmounts[challengeNumber][participant];
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
        remainder = _token.balanceOf(address(this)) - _currentTotalStaked - _competitionPool - _burnedAmount;
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


    function getBurnRecipient()
    view external override
    returns (address burnRecipient)
    {
        burnRecipient = _burnRecipient;
    }

    function getTotalBurnedAmount()
    view external override
    returns (uint256 burnedAmount)
    {
        burnedAmount = _burnedAmount;
    }

    function getBurnedAmount(uint32 challengeNumber, address participant)
    view external override
    returns (uint256 burnedAmount)
    {
        burnedAmount = _challenges[challengeNumber].submitterInfo[participant].tokensBurned;
    }

    function getHistoricalTotalStaked(uint32 challengeNumber)
    view external override
    returns (uint256 historicalTotalStakedAmt)
    {
        historicalTotalStakedAmt = _historicalTotalStake[challengeNumber];
    }

    function getVault()
    view external override
    returns (address vaultAddress)
    {
        vaultAddress = _vault;
    }

    /**
    METHODS CALLABLE BY BOTH ADMIN AND PARTICIPANTS.
    **/

    function sponsor(uint256 amountToken)
    external override
    returns (bool success)
    {
        uint256 currentCompPoolAmt = _competitionPool;
        _competitionPool = currentCompPoolAmt + amountToken;
        success = _token.transferFrom(msg.sender, address(this), amountToken);

        emit Sponsor(msg.sender, amountToken, currentCompPoolAmt + amountToken);
    }
}