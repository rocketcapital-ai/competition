pragma solidity ^0.8.4;

// SPDX-License-Identifier: MIT

interface ICompetitionV2{


    /**
    PARTICIPANT WRITE METHODS
    **/

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

    // TODO: Complete Descriptions
    /**
    **/
    function getBurnRecipient()
    view external returns (address burnRecipient);

    /**
    **/
    function getTotalBurnedAmount()
    view external returns (uint256 burnedAmount);

    /**
    **/
    function getBurnedAmount(uint32 challengeNumber, address participant)
    view external returns (uint256 burnedAmount);

    /**
    **/
    function getHistoricalTotalStaked(uint32 challengeNumber)
    view external returns (uint256 historicalTotalStakedAmt);

    /**
    **/
    function getVault()
    view external returns (address vaultAddress);

    /**
    ADMIN WRITE METHODS
    **/

    /**
    * @dev Called by admin to record a snapshot of the stakes and backed participants for the challenge.
    * @dev A start and end index must be specified. This allows for partial recording in cases where the
    * @dev block gas limit is insufficient for recording all stakers and their staked amounts in one transaction.
    * @param startIndex Starting index to record.
    * @param endIndex Ending index to record, exclusive.
    * @return success True if the operation completed successfully.
    **/
    function recordStakes(uint256 startIndex, uint256 endIndex)
    external returns (bool success);

    // TODO: Complete descriptions
    /**
    **/
    function moveBurnedToPool(uint256 amount)
    external returns (bool success);

    /**
    **/
    function moveBurnedOut(uint256 amount)
    external returns (bool success);

    /**
    **/
    function updateBurnRecipient(address newBurnRecipient)
    external returns (bool success);

    /**
    **/
    function updateVault(address vault)
    external returns (bool success);

    /**
    **/

    function burn(address[] calldata submitters, uint256[] calldata slashAmounts)
    external returns (bool success);

    /**
    EVENTS
    **/

    event BackedParticipantUpdated(uint32 indexed challengeNumber, address indexed backer, address indexed backedParticipant);
    event MigrationCompleted(uint256 indexed blockNumber);
    event BurnedMoved(address indexed recipient, uint256 indexed amount);
    event BurnRecipientUpdated(address indexed newBurnRecipient);
    event BurnMaxUpdated(uint32 indexed challengeNumber, uint256 maxBurnMin, uint256 maxBurnCap, uint256 maxBurnPercentage);
    event VaultUpdated(address indexed vault);
    event Burned(uint32 indexed challengeNumber, address indexed submitter, uint256 indexed burnAmount);

}