pragma solidity ^0.8.4;

// SPDX-License-Identifier: MIT

/**
 * @title RCI Tournament(Competition) Contract
 * @author Rocket Capital Investment Pte Ltd
 Mappings to prevent repeated use of dataset and public keys.
**/

abstract contract UniqueMappings {
    mapping(bytes32 => bool) internal _datasetHashes;
    mapping(bytes32 => bool) internal _publicKeyHashes;
    mapping(uint32 => uint256) public challengePayments;
    mapping(uint32 => uint256) public challengeBurns;
}