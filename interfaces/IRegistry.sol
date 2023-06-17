pragma solidity ^0.8.4;

// SPDX-License-Identifier: MIT

interface IRegistry{

    event CompetitionAuthorized(address indexed competitionAddress, string indexed competitionName);
    event CompetitionUnauthorized(address indexed competitionAddress, string indexed competitionName);
    event TokenAddressChanged(address indexed newAddress);
    event NewExtensionRegistered(string indexed extensionName, address indexed extensionAddress,
        bytes32 indexed informationLocation);
    event ExtensionActiveToggled(string indexed extensionName);
    event ExtensionInfoLocationChanged(string indexed extensionName, bytes32 indexed newLocation);

    function registerNewExtension(string calldata extensionName,address extensionAddress,
        bytes32 informationLocation) external;

    function toggleExtensionActive(string calldata extensionName) external;

    function changeExtensionInfoLocation(string calldata extensionName, bytes32 newLocation) external;

    function getCompetitionList() external view returns (string[] memory competitionNames);

    function getCompetitionActive(string calldata competitionName) external view returns (bool active);

    function getCompetitionAddress(string calldata competitionName) external view returns (address competitionAddress);

    function getExtensionList() external view returns (string[] memory extensionNames);

    function getExtensionAddress(string calldata extensionName) external view returns (address extensionAddress);

    function getExtensionActive(string calldata extensionName) external view returns (bool active);

    function getExtensionInfoLocation(string calldata extensionName) external view returns
    (bytes32 informationLocation);

    function getCompetitionActiveByAddress(address competitionAddress) external view returns (bool active);
}