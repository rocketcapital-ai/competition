// SPDX-License-Identifier: MIT
pragma solidity ^0.8.15;

import "./../interfaces/IShareTaxPolicy.sol";
import "./AccessControlRci.sol";

contract ShareTaxPolicyVanilla is IShareTaxPolicy, AccessControlRci {

    mapping (address => bool) public vip; // vip: no taxes when sending.
    mapping (address => bool) public exempt; // exempt: no taxes when sending or receiving.
    address public federalTaxCollector;
    address public stateTaxCollector;
    uint256 public federalTaxPercentage;
    uint256 public stateTaxPercentage;
    uint256 public taxDecimals;
    uint256 public taxUnits;

    constructor(address federalTaxCollector_,
                address stateTaxCollector_,
                uint256 federalTaxPercentage_,
                uint256 stateTaxPercentage_,
                uint256 taxDecimals_
    ) {
        _initializeRciAdmin(msg.sender);
        federalTaxCollector = federalTaxCollector_;
        stateTaxCollector = stateTaxCollector_;
        federalTaxPercentage = federalTaxPercentage_;
        stateTaxPercentage = stateTaxPercentage_;
        taxDecimals = taxDecimals_;
        taxUnits = 10 ** taxDecimals_;
    }

    function updateVip(address newVipAddress, bool toAdd)
    external onlyRole(RCI_CHILD_ADMIN)
    returns (bool) // free to send
    {
        vip[newVipAddress] = toAdd;
        return true;
    }

    function updateExempt(address newExemptAddress, bool toAdd)
    external onlyRole(RCI_CHILD_ADMIN)
    returns (bool) // free to send and receive
    {
        exempt[newExemptAddress] = toAdd;
        return true;
    }

    function updateTaxPercentage(uint256 newPercentage)
    external onlyRole(RCI_CHILD_ADMIN)
    returns (bool)
    {
        federalTaxPercentage = newPercentage;
        return true;
    }

    function computeFederalTax(uint256 amount)
    public view
    returns (uint256)
    {
        return federalTaxPercentage * amount / taxUnits;
    }

    function computeStateTax(uint256 amount)
    public view
    returns (uint256)
    {
        return stateTaxPercentage * amount / taxUnits;
    }

    function shareTaxActions(address from, address to, uint256 amount)
    external view override
    returns (ShareTaxTransfers[] memory)
    {
        if (exempt[from] || exempt[to] || vip[from]) {
            return new ShareTaxTransfers[](0);
        }
        ShareTaxTransfers[] memory shareTaxTransfers = new ShareTaxTransfers[](2);

        shareTaxTransfers[0] = ShareTaxTransfers({
                                payer: from,
                                collector: federalTaxCollector,
                                amount: computeFederalTax(amount)
        });

        shareTaxTransfers[1] = ShareTaxTransfers({
                                payer: from,
                                collector: stateTaxCollector,
                                amount: computeStateTax(amount)
        });

        return shareTaxTransfers;
    }
}
