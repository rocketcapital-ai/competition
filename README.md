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