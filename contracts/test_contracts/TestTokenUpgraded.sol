// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.0;

import "../ChildToken.sol";

contract TestTokenUpgraded is ChildToken {
    constructor(){
    }

    function setUint(string memory key, uint256 value)
    external
    {
        _storageUint[key] = value;
    }

    function getUint(string memory key)
    external view
    returns (uint256)
    {
        return _storageUint[key];
    }
}
