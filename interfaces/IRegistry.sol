pragma solidity 0.8.4;

// SPDX-License-Identifier: MIT

interface IRegistry{

    function registerNewCompetition(string calldata competitionName, address competitionAddress, bytes32 rulesLocation) external;
    
    function toggleCompetitionActive(string calldata competitionName) external;

    function changeCompetitionRulesLocation(string calldata competitionName, bytes32 newLocation) external;
    
    function changeTokenAddress(address newAddress) external;

    function registerNewExtension(string calldata extensionName,address extensionAddress, bytes32 informationLocation) external;

    function toggleExtensionActive(string calldata extensionName) external;

    function changeExtensionInfoLocation(string calldata extensionName, bytes32 newLocation) external;

    function getCompetitionList() view external returns (string[] memory competitionNames);

    function getExtensionList() view external returns (string[] memory extensionNames);

    function getCompetitionActive(string calldata competitionName) view external returns (bool active);

    function getCompetitionAddress(string calldata competitionName) view external returns (address competitionAddress);

    function getCompetitionRulesLocation(string calldata competitionName) view external returns (bytes32 rulesLocation);

    function getTokenAddress() view external returns (address token);

    function getExtensionAddress(string calldata extensionName) view external returns (address extensionAddress);

    function getExtensionActive(string calldata extensionName) view external returns (bool active);

    function getExtensionInfoLocation(string calldata extensionName) view external returns (bytes32 informationLocation);

    event NewCompetitionRegistered(string indexed competitionName, address indexed competitionAddress, bytes32 rulesLocation);
    event CompetitionActiveToggled(string indexed competitionName);
    event CompetitionRulesLocationChanged(string indexed competitionName, bytes32 indexed newLocation);
    event TokenAddressChanged(address indexed newAddress);
    event NewExtensionRegistered(string indexed extensionName, address indexed extensionAddress, bytes32 indexed informationLocation);
    event ExtensionActiveToggled(string indexed extensionName);
    event ExtensionInfoLocationChanged(string indexed extensionName, bytes32 indexed newLocation);
}