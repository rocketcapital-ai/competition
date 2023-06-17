// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;


import "./Token.sol";

contract ChildToken is Token  {
    using Address for address;

    address internal _fxManager;
    address internal _connectedToken;

    constructor()
    Token()
    {}

    function setFxManager(address fxManager_)
    external
    onlyRole(RCI_CHILD_ADMIN)
    {
        require(fxManager_.isContract(), "Invalid address.");
        _fxManager = fxManager_;
    }

    function setConnectedToken(address connectedToken_)
    external
    onlyRole(RCI_CHILD_ADMIN)
    {
        require(connectedToken_.isContract(), "Invalid address.");
        _connectedToken = connectedToken_;
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

    function fxManager()
    public view
    returns (address)
    {
        return _fxManager;
    }

    function connectedToken()
    public view
    returns (address)
    {
        return _connectedToken;
    }
}