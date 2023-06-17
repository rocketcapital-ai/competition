pragma solidity ^0.8.4;

// SPDX-License-Identifier: MIT

import './../interfaces/IRegistry.sol';
import "./TransferFeeToken.sol";


abstract contract Registry is IRegistry, TransferFeeToken{
    using EnumerableSet for EnumerableSet.AddressSet;

    struct Ext{
        bool active;
        address extensionAddress;
        bytes32 informationLocation;
    }

    EnumerableSet.AddressSet private _authorizedCompetitions;

    mapping(string => address) private _competitionNameAddressMap; // for compatibility with legacy read methods.
    mapping(address => string) private _competitionAddressNameMap; // for compatibility with legacy read methods.

    mapping(string => Ext) private _extension;
    string[] private _extensionNames;

    constructor()
    TransferFeeToken("RCI Template V1", "RCI Template V1", 0, msg.sender)
    {}

    function authorizeCompetition(address competitionAddress, string calldata competitionName)
    external
    onlyRole(RCI_CHILD_ADMIN)
    {
        require(competitionAddress != address(0), "Cannot authorize 0 address.");
        require(_competitionNameAddressMap[competitionName] == address(0), "Name taken");
        require(stringCompareNull(_competitionAddressNameMap[competitionAddress]), "Address taken");
        _authorizedCompetitions.add(competitionAddress);
        _competitionNameAddressMap[competitionName] = competitionAddress;
        _competitionAddressNameMap[competitionAddress] = competitionName;

        emit CompetitionAuthorized(competitionAddress, competitionName);
    }

    function unauthorizeCompetition(address competitionAddress, string calldata competitionName)
    external
    onlyRole(RCI_CHILD_ADMIN)
    {
        require(competitionAddress != address(0), "Cannot unauthorize 0 address.");
        require(_competitionNameAddressMap[competitionName] == competitionAddress, "No name with this address.");
        require(stringCompare(_competitionAddressNameMap[competitionAddress], competitionName),
            "No address with this name.");
         _authorizedCompetitions.remove(competitionAddress);
        _competitionNameAddressMap[competitionName] = address(0);
        _competitionAddressNameMap[competitionAddress] = "";

        emit CompetitionUnauthorized(competitionAddress, competitionName);
    }

    function registerNewExtension(string calldata extensionName,address extensionAddress, bytes32 informationLocation)
    external override onlyRole(RCI_CHILD_ADMIN)
    {
        require(extensionAddress != address(0), "Cannot register 0 address.");
        require(informationLocation != bytes32(0), "Cannot set information location to 0.");
        require(_extension[extensionName].extensionAddress == address(0), "Extension already exists.");
        _extension[extensionName] = Ext({active:true, extensionAddress:extensionAddress,
            informationLocation:informationLocation});
        _extensionNames.push(extensionName);

        emit NewExtensionRegistered(extensionName, extensionAddress, informationLocation);
    }
    
    function toggleExtensionActive(string calldata extensionName)
    external override onlyRole(RCI_CHILD_ADMIN)
    {
        require(_extension[extensionName].extensionAddress != address(0),
            "Extension does not exist. Use function 'registerNewExtension' instead.");
        _extension[extensionName].active = !_extension[extensionName].active;

        emit ExtensionActiveToggled(extensionName);
    }
    
    function changeExtensionInfoLocation(string calldata extensionName, bytes32 newLocation)
    external override onlyRole(RCI_CHILD_ADMIN)
    {
        require(_extension[extensionName].extensionAddress != address(0),
            "Extension does not exist. Use function 'registerNewExtension' instead.");
        require(newLocation != bytes32(0), "Cannot set information location to 0.");
        _extension[extensionName].informationLocation = newLocation;

        emit ExtensionInfoLocationChanged(extensionName, newLocation);
    }

    // convenience function for DAPP.
    function batchCall(address[] calldata addresses, bytes[] calldata data)
    external view
    returns (bytes[] memory)
    {
        bytes[] memory returnDataList = new bytes[](data.length);
        for (uint i = 0; i < data.length; i++){
            (bool success, bytes memory returnedData) = addresses[i].staticcall(data[i]);
            returnDataList[i] = returnedData;
        }
        return returnDataList;
    }

    /* READ METHODS */

    function getCompetitionList()
    external view override
    returns (string[] memory competitionNames)
    {
        address[] memory competitionAddresses = getListFromSet(_authorizedCompetitions, 0,
            _authorizedCompetitions.length());
        competitionNames = new string[](competitionAddresses.length);
        for (uint i = 0; i < competitionAddresses.length; i++){
            competitionNames[i] = _competitionAddressNameMap[competitionAddresses[i]];
        }
    }

    function getCompetitionActive(string calldata competitionName)
    external view override
    returns (bool active)
    {
        address competitionAddress = _competitionNameAddressMap[competitionName];
        active = getCompetitionActiveByAddress(competitionAddress);
    }

    function getCompetitionAddress(string calldata competitionName)
    external view override
    returns (address competitionAddress)
    {
        competitionAddress = _competitionNameAddressMap[competitionName];
    }

    function getExtensionList()
    external view override
    returns (string[] memory extensionNames)
    {
        extensionNames = _extensionNames;
    }

    function getExtensionAddress(string calldata extensionName)
    external view override
    returns (address extensionAddress)
    {
        extensionAddress = _extension[extensionName].extensionAddress;
    }

    function getExtensionActive(string calldata extensionName)
    external view override
    returns (bool active)
    {
        active = _extension[extensionName].active;
    }

    function getExtensionInfoLocation(string calldata extensionName)
    external view override
    returns (bytes32 informationLocation)
    {
        informationLocation = _extension[extensionName].informationLocation;
    }

    function getCompetitionActiveByAddress(address competitionAddress)
    public view override
    returns (bool active)
    {
        active = _authorizedCompetitions.contains(competitionAddress);
    }

    function stringCompare(string storage s1, string calldata s2)
    internal view
    returns (bool same)
    {
        same = keccak256(abi.encodePacked(s1)) == keccak256(abi.encodePacked(s2));
    }


    function stringCompareNull(string storage s1)
    internal view
    returns (bool same)
    {
        same = keccak256(abi.encodePacked(s1)) == keccak256(abi.encodePacked(""));
    }
}





