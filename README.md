# Upgradeability

The Token and Competition contracts have been made upgradeable to support a roadmap for deployment before audit.
(Deployments were made on 15 May 2023).

Once audit and contract revisions have been made, contracts will be upgraded and upgradeability will be locked, for example via renouncing of admin roles for upgrading. The contracts will not be upgradeable after that.

# Usage
## Install Brownie
`pipx install eth-brownie`
or
`pip install eth-brownie`

If you face installation issues, please refer to the Brownie installation [guide](https://eth-brownie.readthedocs.io/en/stable/install.html).

## Clone the repo

`git clone https://github.com/rocketcapital-ai/competition.git -b main`

## Enter the directory
`cd competition`

## Run Tests

### Note for Tests
To test migration functions for V2, please use the test found in `test_fork_competition_child_token_proxy.py`.
This will run the test on an archive node, which means we will have the current state of the contract to test with. 
(The test can also be run based on the state of the competition at historical blocks.)

A csv file with 3 columns, historical challenge number, staker addresses and their corresponding staked amounts (in uint256) will need to be provided under the `tests` folder for the test to work properly. (See the `open_staker_info_csv` method in the above test file for more details.)

An archive node is required for this test. You may obtain access to one by creating an account on an archive node provider such as Moralis, Chainstack, Alchemy, Quicknode, Infura, Ankr, amongst others.  

Examples:
### Run All Tests
`brownie test`

### Run Specific Test
`brownie test tests/<test-file-name>`

## Compile All Contracts
`brownie compile --all`