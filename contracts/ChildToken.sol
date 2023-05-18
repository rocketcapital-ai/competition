// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;


import "./Token.sol";

contract ChildToken is Token  {
    address internal _fxManager;
    address internal _connectedToken;

    constructor()
    Token()
    {}

    function setFxManager(address fxManager_)
    external
    onlyRole(RCI_CHILD_ADMIN)
    {
        _fxManager = fxManager_;
    }

    function fxManager()
    public view
    returns (address)
    {
        return _fxManager;
    }

    function setConnectedToken(address connectedToken_)
    external
    onlyRole(RCI_CHILD_ADMIN)
    {
        _connectedToken = connectedToken_;
    }

    function connectedToken()
    public view
    returns (address)
    {
        return _connectedToken;
    }

    function mint(address user, uint256 amount)
    public
    {
        require(msg.sender == _fxManager, "Invalid sender");
        _mint(user, amount);
    }

    function burn(address user, uint256 amount)
    public
    {
        require(msg.sender == _fxManager, "Invalid sender");
        _burn(user, amount);
    }
}