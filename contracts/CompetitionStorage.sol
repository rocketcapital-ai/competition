pragma solidity ^0.8.4;

// SPDX-License-Identifier: MIT

import '../interfaces/IToken.sol';
import "OpenZeppelin/openzeppelin-contracts@4.8.0/contracts/utils/structs/EnumerableSet.sol";


/**
 * @title RCI Tournament(Competition) Contract
 * @author Rocket Capital Investment Pte Ltd
**/

contract CompetitionStorage {

    struct Information{
        bytes32 submission;
        uint256 staked;
        uint256 stakingRewards;
        uint256 challengeRewards;
        uint256 tournamentRewards;
        uint256 challengeScores;
        uint256 tournamentScores;
        mapping(uint256 => uint) info;
        uint256 tokensBurned;
    }

    struct Challenge{
        bytes32 dataset;
        bytes32 results;
        bytes32 key;
        bytes32 privateKey;
        uint8 phase;
        mapping(address => Information) submitterInfo;
        mapping(uint256 => uint256) deadlines;
        EnumerableSet.AddressSet submitters;
    }

    IToken internal _token;
    uint32 internal _challengeCounter;
    uint256 internal _stakeThreshold;
    uint256 internal _competitionPool;
    uint256 internal _rewardsThreshold;
    uint256 internal _currentTotalStaked;
    uint256 internal _currentStakingRewardsBudget;
    uint256 internal _currentChallengeRewardsBudget;
    uint256 internal _currentTournamentRewardsBudget;
    string internal _message;
    mapping(address => uint256) internal _stakes;
    mapping(uint32 => Challenge) internal _challenges;

    address internal _burnRecipient;
    uint256 internal _burnedAmount;
    EnumerableSet.AddressSet stakerSet;
    mapping(uint32 => uint256) public challengeOpenedBlockNumbers;
    mapping(uint32 => uint256) public submissionClosedBlockNumbers;
    mapping(uint32 => EnumerableSet.AddressSet) internal _historicalStakerSet;
    mapping(uint32 => mapping(address => uint256)) internal _historicalStakeAmounts;
    mapping(uint32 => uint256) internal _historicalTotalStake;

    address internal _vault;



}