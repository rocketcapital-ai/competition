# Documentation
Further documentation can be found [here](https://rocket-capital-investment.gitbook.io/competition-dapp/).

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

Run example:
>brownie test tests/test_fork_competition_child_token_proxy.py --network polygon_dev
### Run All Tests
`brownie test`

### Run Specific Test
`brownie test tests/<test-file-name>`

#### Useful flags
`--coverage` shows an evaluation of test coverage by function for each contract.

`--stateful [true,false]` 

True: runs only `test_competition_state.py` and `test_token_state.py`.


## Compile All Contracts
`brownie compile --all`