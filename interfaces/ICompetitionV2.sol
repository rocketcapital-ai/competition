pragma solidity ^0.8.4;

// SPDX-License-Identifier: MIT

interface ICompetitionV2{

    /**
    EVENTS
    **/

    event BackedParticipantUpdated(uint32 indexed challengeNumber,
        address indexed backer, address indexed backedParticipant);
    event MigrationCompleted(uint256 indexed blockNumber);
    event BurnedMoved(address indexed recipient, uint256 indexed amount);
    event BurnRecipientUpdated(address indexed newBurnRecipient);
    event BurnMaxUpdated(uint32 indexed challengeNumber,
        uint256 maxBurnMin, uint256 maxBurnCap, uint256 maxBurnPercentage);
    event VaultUpdated(address indexed vault);
    event Burned(uint32 indexed challengeNumber, address indexed submitter, uint256 indexed burnAmount);

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

    /**
    * @dev Called by admin to move the existing burned amount to the competition pool.
    * @param amount Amount to move. Must be <= to the amount burned that has not been moved to
    * @dev the competition pool or moved out of the competition contract.
    * @return success True if the operation completed successfully.
    **/
    function moveBurnedToPool(uint256 amount)
    external returns (bool success);

    /**
    * @dev Called by admin to move the existing burned amount out of the competition contract, to the burn recipient.
    * @param amount Amount to move. Must be <= to the amount burned that has not been moved to
    * @dev the competition pool or moved out of the competition contract.
    * @return success True if the operation completed successfully.
    **/
    function moveBurnedOut(uint256 amount)
    external returns (bool success);

    /**
    * @dev Called by admin to update the recipient of moveBurnedOut.
    * @param newBurnRecipient New burn recipient.
    * @return success True if the operation completed successfully.
    **/
    function updateBurnRecipient(address newBurnRecipient)
    external returns (bool success);

    /**
    * @dev Called by admin to update the vault linked to this competition. For info only and does not affect
    * @dev the competition contract logic.
    * @param vault New vault address.
    * @return success True if the operation completed successfully.
    **/
    function updateVault(address vault)
    external returns (bool success);

    /**
    * @dev Called by admin to decrement participant stakes based on challenge performance.
    * @param submitters List of addresses of participants to decrement stakes of.
    * @param slashAmounts List of amounts to decrement stakes by.
    * @return success True if the operation completed successfully.
    **/
    function burn(address[] calldata submitters, uint256[] calldata slashAmounts)
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
    external view returns (address[] memory);

    /**
    * @dev Get the full list of addresses that had a staked amount > 0 for a past challenge.
    * @param challengeNumber Challenge number to get full list of stakers of.
    * @return Full list of addresses that had a staked amount > 0 for a past challenge.
    **/
    function getHistoricalStakers(uint32 challengeNumber)
    external view returns (address[] memory);

    /**
    * @dev Get the staked amounts of specified addresses for a past challenge.
    * @param challengeNumber Challenge number to get list of staked amounts of.
    * @return List of staked amounts of specified addresses for a past challenge.
    **/
    function getHistoricalStakeAmounts(uint32 challengeNumber, address[] calldata stakers)
    external view returns (uint256[] memory);

    /**
    * @dev Get the number of addresses that currently have a staked amount > 0.
    * @return stakersCounter Number of addresses that currently have a staked amount > 0.
    **/
    function getStakersCounter()
    external view returns (uint256 stakersCounter);

    /**
    * @dev Get the partial list of addresses that currently have a staked amount > 0.
    * @param startIndex Starting index of list to retrieve.
    * @param endIndex Ending index of list to retrieve.
    * @return List of addresses that currently have a staked amount > 0.
    **/
    function getStakers(uint256 startIndex, uint256 endIndex)
    external view returns (address[] memory);

    /**
    * @dev Get the full list of addresses that currently have a staked amount > 0.
    * @return Full list of addresses that currently have a staked amount > 0.
    **/
    function getAllStakers()
    external view returns (address[] memory);

    /**
    * @dev Get address of the burn recipient that can receive tokens from moveBurnedOut.
    * @return burnRecipient Address of the burn recipient.
    **/
    function getBurnRecipient()
    external view returns (address burnRecipient);

    /**
    * @dev Get the total amount of tokens burned that have not been moved out or to the competition pool.
    * @return burnedAmount Total amount of tokens burned that have not been moved out or to the competition pool.
    **/
    function getTotalBurnedAmount()
    external view returns (uint256 burnedAmount);

    /**
    * @dev Get the amount of tokens burned for a participant at a particular challenge.
    * @param challengeNumber Challenge number to get burned amount of.
    * @param participant Address of participant to get burned amount of.
    * @return burnedAmount Amount of tokens burned for a participant at a particular challenge.
    **/
    function getBurnedAmount(uint32 challengeNumber, address participant)
    external view returns (uint256 burnedAmount);

    /**
    * @dev Get the total amount of tokens staked for a particular challenge.
    * @param challengeNumber Challenge number to get total staked amount of.
    * @return historicalTotalStakedAmt Total amount of tokens staked for a particular challenge.
    **/
    function getHistoricalTotalStaked(uint32 challengeNumber)
    external view returns (uint256 historicalTotalStakedAmt);

    /**
    * @dev Get the address of the vault linked to this challenge. For info only.
    * @return vaultAddress Address of the vault linked to this challenge.
    **/
    function getVault()
    external view returns (address vaultAddress);

    /**
    * @dev Get the number of addresses that had a staked amount > 0 for a past challenge.
    * @param challengeNumber Challenge number to get number of stakers of.
    * @return stakersCounter Number of addresses that had a staked amount > 0 for a past challenge.
    **/
    function getHistoricalStakersCounter(uint32 challengeNumber)
    external view returns (uint256 stakersCounter);

    /**
    * @dev Get the partial list of addresses that had a staked amount > 0 for a past challenge.
    * @param challengeNumber Challenge number to get partial list of stakers of.
    * @param startIndex Starting index of list to retrieve.
    * @param endIndex Ending index of list to retrieve.
    * @return List of addresses that had a staked amount > 0 for a past challenge.
    **/
    function getHistoricalStakersPartial(uint32 challengeNumber, uint256 startIndex, uint256 endIndex)
    external view returns (address[] memory);

}