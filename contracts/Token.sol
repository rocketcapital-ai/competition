pragma solidity ^0.8.4;

// SPDX-License-Identifier: MIT

import "./../interfaces/ICompetition.sol";
import "./Registry.sol";
import "OpenZeppelin/openzeppelin-contracts@4.8.0/contracts/proxy/utils/Initializable.sol";

contract Token is Registry, Initializable
{
    uint8 private _decimals;
    string private _name;
    string private _symbol;

    constructor ()
    {}

    function initialize(string memory name_, string memory symbol_, uint256 initialSupply_, address admin_)
    external
    initializer
    {
        _decimals = 6;
        _name = name_;
        _symbol = symbol_;
        _mint(admin_, initialSupply_);
        _initializeRciAdmin(admin_);
    }

    function increaseStake(address target, uint256 amountToken)
    public
    returns (bool success)
    {
        require(getCompetitionActiveByAddress(target), "Competition inactive.");
        uint256 senderBal = balanceOf(msg.sender);
        uint256 senderStake = ICompetition(target).getStake(msg.sender);

        ICompetition(target).increaseStake(msg.sender, amountToken);
        transfer(target, amountToken);

        require((senderBal - balanceOf(msg.sender)) == amountToken, "Token - increaseStake: Sender final balance incorrect.");
        require((ICompetition(target).getStake(msg.sender) - senderStake) == amountToken, "Token - increaseStake: Sender final stake incorrect.");

        success = true;
    }

    function decreaseStake(address target, uint256 amountToken)
    public
    returns (bool success)
    {
        require(getCompetitionActiveByAddress(target), "Competition inactive.");
        uint256 senderBal = balanceOf(msg.sender);
        uint256 senderStake = ICompetition(target).getStake(msg.sender);

        ICompetition(target).decreaseStake(msg.sender, amountToken);

        require((balanceOf(msg.sender) - senderBal) == amountToken, "Token - decreaseStake: Sender final balance incorrect.");
        require(senderStake - (ICompetition(target).getStake(msg.sender)) == amountToken, "Token - decreaseStake: Sender final stake incorrect.");

        success = true;
    }

    function setStake(address target, uint256 amountToken)
    public
    returns (bool success)
    {
        require(getCompetitionActiveByAddress(target), "Competition inactive.");
        uint256 currentStake = ICompetition(target).getStake(msg.sender);
        if (amountToken > currentStake){
            increaseStake(target, amountToken - currentStake);
        } else{
            decreaseStake(target, currentStake - amountToken);
        }
        success = true;
    }

    function stakeAndSubmit(address target, uint256 amountToken, bytes32 hash)
    external
    returns (bool success)
    {
        ICompetition(target).submit(msg.sender, hash);
        require(setStake(target, amountToken), "Set stake unsuccessful."); // competition authorization checked via setStake callby
        success = true;
    }

    function getStake(address target, address staker)
    external view
    returns (uint256 stake)
    {
        require(getCompetitionActiveByAddress(target), "Competition inactive.");
        stake = ICompetition(target).getStake(staker);
    }

    function decimals() public view override returns (uint8) {
        return _decimals;
    }

    function name() public view override returns (string memory) {
        return _name;
    }

    function symbol() public view override returns (string memory) {
        return _symbol;
    }
}