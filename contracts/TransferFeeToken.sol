// SPDX-License-Identifier: MIT
pragma solidity ^0.8.4;

import "./../interfaces/IBlacklistPolicy.sol";
import "./../interfaces/IShareTaxPolicy.sol";
import "./AccessControlRci.sol";
import "./ShareholderEnumerableToken.sol";
import "OpenZeppelin/openzeppelin-contracts@4.8.0/contracts/utils/Address.sol";

abstract contract TransferFeeToken is AccessControlRci, ShareholderEnumerableToken
{
    using Address for address;

    IBlacklistPolicy public blacklistPolicy;
    IShareTaxPolicy public shareTaxPolicy;
    bool private recursionFlag;

    event BlacklistPolicyUpdated(address indexed oldAddress, address indexed newAddress);
    event ShareTaxPolicyUpdated(address indexed oldAddress, address indexed newAddress);

    constructor(
        string memory name_,
        string memory symbol_,
        uint256 initialSupply_,
        address admin_
    ) ShareholderEnumerableToken(name_, symbol_, initialSupply_, admin_)
    {}

    function updateBlacklistPolicyAddress(address newBlacklistPolicy)
    public onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        require(newBlacklistPolicy.isContract(), "blacklist update failed");
        emit BlacklistPolicyUpdated(address(blacklistPolicy), newBlacklistPolicy);
        blacklistPolicy = IBlacklistPolicy(newBlacklistPolicy);
        success = true;
    }

    function updateShareTaxPolicyAddress(address newShareTaxPolicy)
    public onlyRole(RCI_CHILD_ADMIN)
    returns (bool success)
    {
        if (newShareTaxPolicy != address(0)) {
            require(newShareTaxPolicy.isContract());
        }
        emit ShareTaxPolicyUpdated(address(shareTaxPolicy), newShareTaxPolicy);
        shareTaxPolicy = IShareTaxPolicy(newShareTaxPolicy);
        success = true;
    }

    function blacklistPolicyActive()
    public view
    returns (bool active)
    {
        active = address(blacklistPolicy) != address(0);
    }

    function transferFeeActive()
    public view
    returns (bool active)
    {
        active = address(shareTaxPolicy) != address(0);
    }

    function _beforeTokenTransfer(address from, address to, uint256 amount)
    internal override
    {
        // `to` is only allowed to be address(0) when it is a burn function.
        // Transfer and mint already prevent setting `to` to address(0).
        if (blacklistPolicyActive()) {
            require(blacklistPolicy.transferPolicy(from, to, amount), "Failed blacklist check.");
        }
    }

    function _afterTokenTransfer(address from, address to, uint256 amount)
    internal override
    {
         if (transferFeeActive()
            && (from != address(0)) // exclude tax when minting
            && (to != address(0)) // exclude tax when burning
         ) {
            if (!recursionFlag) {
                recursionFlag = true;
                IShareTaxPolicy.ShareTaxTransfers[] memory shareTaxTransfers =
                shareTaxPolicy.shareTaxActions(from, to, amount);
                for (uint i = 0; i < shareTaxTransfers.length; i++) {
                    _transfer(shareTaxTransfers[i].payer,
                        shareTaxTransfers[i].collector,
                        shareTaxTransfers[i].amount);
                    updateShareHolders(shareTaxTransfers[i].payer);
                    updateShareHolders(shareTaxTransfers[i].collector);
                }
                recursionFlag = false;
            }
        }
        updateShareHolders(from);
        updateShareHolders(to);
    }
}
