pragma solidity ^0.8.4;

// SPDX-License-Identifier: MIT

interface IRegistry{

    function registerNewExtension(string calldata extensionName,address extensionAddress, bytes32 informationLocation) external;

    function toggleExtensionActive(string calldata extensionName) external;

    function changeExtensionInfoLocation(string calldata extensionName, bytes32 newLocation) external;

    function getCompetitionList() view external returns (string[] memory competitionNames);

    function getExtensionList() view external returns (string[] memory extensionNames);

    function getCompetitionActive(string calldata competitionName) view external returns (bool active);

    function getCompetitionActiveByAddress(address competitionAddress) view external returns (bool active);

    function getCompetitionAddress(string calldata competitionName) view external returns (address competitionAddress);

    function getExtensionAddress(string calldata extensionName) view external returns (address extensionAddress);

    function getExtensionActive(string calldata extensionName) view external returns (bool active);

    function getExtensionInfoLocation(string calldata extensionName) view external returns (bytes32 informationLocation);

    event CompetitionAuthorized(address indexed competitionAddress, string indexed competitionName);
    event CompetitionUnauthorized(address indexed competitionAddress, string indexed competitionName);
    event TokenAddressChanged(address indexed newAddress);
    event NewExtensionRegistered(string indexed extensionName, address indexed extensionAddress, bytes32 indexed informationLocation);
    event ExtensionActiveToggled(string indexed extensionName);
    event ExtensionInfoLocationChanged(string indexed extensionName, bytes32 indexed newLocation);
}