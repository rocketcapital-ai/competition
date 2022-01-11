pragma solidity 0.8.4;

// SPDX-License-Identifier: MIT

import '../interfaces/IToken.sol';
import "./standard/utils/structs/EnumerableSet.sol";

contract CompetitionStorageV2{

    // Version 2 data structures added on.
    // "backers" will be used to refer to the set of users backing a participant.
    // "backed" will be used to refer to the participant that a user is backing.
    // one user (ie. one address) can only back one participant.
    EnumerableSet.AddressSet stakerSet;
    mapping(address => EnumerableSet.AddressSet) internal _backers;
    mapping(address => address) internal _backed;
    mapping(uint32 => uint256) public challengeOpenedBlockNumbers;
    mapping(uint32 => uint256) public submissionClosedBlockNumbers;
    mapping(uint32 => EnumerableSet.AddressSet) internal _historicalStakerSet;
    mapping(uint32 => mapping(address => uint256)) internal _historicalStakeAmounts;
}