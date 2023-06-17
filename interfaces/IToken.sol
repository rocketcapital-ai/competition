pragma solidity ^0.8.4;

// SPDX-License-Identifier: MIT

/**
 * @dev Interface for interacting with Token.sol.
 */
interface IToken {

    function transfer(address recipient, uint256 amount) external returns (bool);

    function increaseAllowance(address spender, uint256 addedValue) external returns (bool);

    function decreaseAllowance(address spender, uint256 subtractedValue) external returns (bool);

    function increaseStake(address target, uint256 amountToken) external returns (bool success);

    function decreaseStake(address target, uint256 amountToken) external returns (bool success);

    function setStake(address target, uint256 amountToken) external returns (bool success);

    function authorizeCompetition(address competitionAddress) external;

    function revokeCompetition(address competitionAddress) external;

    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);

    function allowance(address owner, address spender) external view returns (uint256);

     function totalSupply() external view returns (uint256);

    function balanceOf(address account) external view returns (uint256);

    function getStake(address target, address staker) external view returns (uint256 stake);

    function competitionIsAuthorized(address competitionAddress) external view returns (bool authorized);
}