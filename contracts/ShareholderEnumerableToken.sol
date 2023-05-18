// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;
import "OpenZeppelin/openzeppelin-contracts@4.8.0/contracts/utils/structs/EnumerableSet.sol";
import "OpenZeppelin/openzeppelin-contracts@4.8.0/contracts/token/ERC20/presets/ERC20PresetFixedSupply.sol";

abstract contract ShareholderEnumerableToken is ERC20PresetFixedSupply {
    // the following are slots for storage variables for use in TransparentUpgradeableProxy contracts that may
    // need additional variables for updated contracts inherited "in the middle".
    mapping (string => uint256) internal _storageUint;
    mapping (string => address) internal _storageAddress;
    mapping (string => bytes32) internal _storageBytes32;
    mapping (string => bool) internal _storageBool;

    using EnumerableSet for EnumerableSet.AddressSet;
    EnumerableSet.AddressSet private shareHolders;

    constructor(
        string memory name_,
        string memory symbol_,
        uint256 initialSupply_,
        address recipient_
    ) ERC20PresetFixedSupply(name_, symbol_, initialSupply_, recipient_) {}

    function numberOfShareHolders()
    public view
    returns (uint256 holdersCount)
    {
        holdersCount = shareHolders.length();
    }

    function updateShareHolders(address userAddress)
    internal
    {
        if (balanceOf(userAddress) > 0) {
            shareHolders.add(userAddress);
        } else {
            shareHolders.remove(userAddress);
        }
    }

    function getShareHolders(uint256 startIndex, uint256 endIndex)
    external view
    returns (address[] memory shareHoldersList)
    {
        shareHoldersList = getListFromSet(shareHolders, startIndex, endIndex);
    }


    function getListFromSet(EnumerableSet.AddressSet storage setOfData, uint256 startIndex, uint256 endIndex)
    internal view
    returns (address[] memory listOfData)
    {
        listOfData = new address[](endIndex - startIndex);
        for (uint i = startIndex; i < endIndex; i++){
            listOfData[i - startIndex] = setOfData.at(i);
        }
    }
}
