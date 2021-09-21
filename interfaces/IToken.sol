pragma solidity 0.8.4;

// SPDX-License-Identifier: MIT

/**
 * @dev Interface for interacting with Token.sol.
 */
interface IToken {

    function totalSupply() external view returns (uint256);

    function balanceOf(address account) external view returns (uint256);

    function transfer(address recipient, uint256 amount) external returns (bool);

    function allowance(address owner, address spender) external view returns (uint256);

    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);

    function increaseAllowance(address spender, uint256 addedValue) external returns (bool);

    function decreaseAllowance(address spender, uint256 subtractedValue) external returns (bool);

    function increaseStake(address target, uint256 amountToken) external returns (bool success);
    
    function decreaseStake(address target, uint256 amountToken) external returns (bool success);
    
    function setStake(address target, uint256 amountToken) external returns (bool success);

    function getStake(address target, address staker) external view returns (uint256 stake);

    function authorizeCompetition(address competitionAddress) external;

    function revokeCompetition(address competitionAddress) external;

    function competitionIsAuthorized(address competitionAddress) external view returns (bool authorized);
}