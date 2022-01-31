pragma solidity 0.8.4;

// SPDX-License-Identifier: MIT

interface ICompetitionV2{


    /**
    PARTICIPANT WRITE METHODS
    **/

    /**
    * @dev Called by participant to change the participant they are backing.
    * @param backedParticipant Address of the new participant that the message sender want to back.
    * @return success True if the operation completed successfully.
    **/
    function updateBackedParticipant(address backedParticipant)
    external returns (bool success);


    /**
    READ METHODS
    **/

    /**
    * @dev Get the full list of addresses that have made submission for the given challenge.
    * @param challengeNumber Challenge number to get list of submitters of.
    * @return Full list of addresses that have made submission for the given challenge.
    **/
    function getAllSubmitters(uint32 challengeNumber)
    view external returns (address[] memory);

    /**
    * @dev Get the number of addresses that had a staked amount > 0 for a past challenge.
    * @param challengeNumber Challenge number to get number of stakers of.
    * @return stakersCounter Number of addresses that had a staked amount > 0 for a past challenge.
    **/
    function getHistoricalStakersCounter(uint32 challengeNumber)
    view external returns (uint256 stakersCounter);

    /**
    * @dev Get the partial list of addresses that had a staked amount > 0 for a past challenge.
    * @param challengeNumber Challenge number to get partial list of stakers of.
    * @param startIndex Starting index of list to retrieve.
    * @param endIndex Ending index of list to retrieve.
    * @return List of addresses that had a staked amount > 0 for a past challenge.
    **/
    function getHistoricalStakersPartial(uint32 challengeNumber, uint256 startIndex, uint256 endIndex)
    view external returns (address[] memory);

    /**
    * @dev Get the full list of addresses that had a staked amount > 0 for a past challenge.
    * @param challengeNumber Challenge number to get full list of stakers of.
    * @return Full list of addresses that had a staked amount > 0 for a past challenge.
    **/
    function getHistoricalStakers(uint32 challengeNumber)
    view external returns (address[] memory);

    /**
    * @dev Get the staked amounts of specified addresses for a past challenge.
    * @param challengeNumber Challenge number to get list of staked amounts of.
    * @return List of staked amounts of specified addresses for a past challenge.
    **/
    function getHistoricalStakeAmounts(uint32 challengeNumber, address[] calldata stakers)
    view external returns (uint256[] memory);

    /**
    * @dev Get the participant that backer is backing.
    * @param backer Address to query backed participant of.
    * @return backedParticipant Address of participant that the backer is backing.
    **/
    function getBackedParticipant(address backer)
    view external returns (address backedParticipant);

    /**
    * @dev Get the number of addresses backing backedParticipant.
    * @param backedParticipant Address to get number of backers of.
    * @return backersCounter Number of addresses backing backedParticipant.
    **/
    function getBackersCounter(address backedParticipant)
    view external returns (uint256 backersCounter);

    /**
    * @dev Get the partial list of addresses backing backedParticipant
    * @param backedParticipant Address to get list of backers of.
    * @param startIndex Starting index of list to retrieve.
    * @param endIndex Ending index of list to retrieve.
    * @return List of addresses backing backedParticipant.
    **/
    function getBackers(address backedParticipant, uint256 startIndex, uint256 endIndex)
    view external returns (address[] memory);

    /**
    * @dev Get the full list of addresses backing backedParticipant.
    * @param backedParticipant Address to get list of backers of.
    * @return Full list of addresses backing backedParticipant.
    **/
    function getAllBackers(address backedParticipant)
    view external returns (address[] memory);

    /**
    * @dev Get total amount that backedParticipant is being backed by.
    * @param backedParticipant Participant to query total backed amount for.
    * @return totalAmount Total staked amount of addresses backing backedParticipant.
    **/
    function getBackingTotal(address backedParticipant)
    view external returns (uint256 totalAmount);

    /**
    * @dev Get the number of addresses that currently have a staked amount > 0.
    * @return stakersCounter Number of addresses that currently have a staked amount > 0.
    **/
    function getStakersCounter()
    view external returns (uint256 stakersCounter);

    /**
    * @dev Get the partial list of addresses that currently have a staked amount > 0.
    * @param startIndex Starting index of list to retrieve.
    * @param endIndex Ending index of list to retrieve.
    * @return List of addresses that currently have a staked amount > 0.
    **/
    function getStakers(uint256 startIndex, uint256 endIndex)
    view external returns (address[] memory);

    /**
    * @dev Get the full list of addresses that currently have a staked amount > 0.
    * @return Full list of addresses that currently have a staked amount > 0.
    **/
    function getAllStakers()
    view external returns (address[] memory);


    /**
    ADMIN WRITE METHODS
    **/

    /**
    * @dev Called by admin to record a snapshot of the stakes for the challenge.
    * @dev A start and end index must be specified. This allows for partial recording in cases where the
    * @dev block gas limit is insufficient for recording all stakers and their staked amounts in one transaction.
    * @param startIndex Starting index to record.
    * @param endIndex Ending index to record, exclusive.
    * @return success True if the operation completed successfully.
    **/
    function recordStakes(uint256 startIndex, uint256 endIndex)
    external returns (bool success);


    /**
    MIGRATION-ONLY ADMIN WRITE METHODS
    **/

    /**
    * @dev Method for admin to manually modify the block number where challenge was opened.
    * @param challengeNumber Challenge number of block number being modified.
    * @param blockNumber New block number to update to.
    * @return success True if the operation completed successfully.
    **/
    function alignChallengeOpenedBlockNumbers(uint32 challengeNumber, uint256 blockNumber)
    external returns (bool success);

    /**
    * @dev Method for admin to manually modify the block number where submission was closed.
    * @param challengeNumber Challenge number of block number being modified.
    * @param blockNumber New block number to update to.
    * @return success True if the operation completed successfully.
    **/
    function alignSubmissionClosedBlockNumbers(uint32 challengeNumber, uint256 blockNumber)
    external returns (bool success);


    /**
    * @dev Method for admin to manually modify the staker set.
    * @param toRemove List of staker addresses to remove.
    * @param toAdd List of staker addresses to add.
    * @return success True if the operation completed successfully.
    **/
    function alignStakerSet(address[] calldata toRemove, address[] calldata toAdd)
    external returns (bool success);

    /**
    * @dev Method for admin to manually modify the staked amounts.
    * @param historicalChallengeNumber Challenge number to modify historical staked amount record for.
    * @param stakers List of staker addresses.
    * @param amounts List of staked amounts to update to.
    * @return success True if the operation completed successfully.
    **/
    function alignHistoricalStakedAmounts(uint32 historicalChallengeNumber, address[] calldata stakers, uint256[] calldata amounts)
    external returns (bool success);

    /**
    * @dev Called by admin to set the current backedParticipant value of existing stakers.
    * @dev This is necessary after a contract upgrade, where the existing stakers will have their
    * @dev backedParticipants defaulted to the zero address, when it needs to be their own address instead.
    * @param backers List of backer addresses to set/reset.
    * @return success True if the operation completed successfully.
    **/
    function alignBacking(address[] calldata backers)
    external returns (bool success);

    /**
    * @dev Called by admin to set the migrationCompletedBlockNumber variable to indicate that the migration has completed.
    * @dev This locks in the migration and no further migration-only methods can be called henceforth.
    * @return success True if the operation completed successfully.
    **/
    function completeMigration()
    external returns (bool success);


    /**
    EVENTS
    **/

    event BackedParticipantUpdated(uint32 indexed challengeNumber, address indexed backer, address indexed backedParticipant);
    event MigrationCompleted(uint256 indexed blockNumber);
}