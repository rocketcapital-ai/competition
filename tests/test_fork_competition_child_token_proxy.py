
from utils_for_testing import *
from brownie import web3, Contract, TransparentUpgradeableProxy, ProxyAdmin, Token, Competition, ChildToken, reverts, accounts
# from test_competition import TestCompetition
import eth_abi, csv


# class TestForkCompetitionChildTokenProxy(TestCompetition):
class TestForkCompetitionChildTokenProxy():
    def setup(self):
        self.num_rounds = 3
        self.stake_amt_history = {}
        self.staker_set_history = {}
        self.use_multi_admin = False
        self.admin = ''
        self.participants = accounts[:]
        self.latest_stake_record_cn = 15
        self.zero_address = '0x' + ('0' * 40)
        self.fork = True
        try: self.participants.remove(self.admin)
        except: pass

        # Point to MUSA Token and transfer from Rewards Delegate account for testing.
        self.token = Token.at('0x5E9cC1C5ec302402cA366c69fF796e0637A608f8')
        self.token.transfer(self.admin, int(Decimal('100000e18')), {'from': '0x505947d520a17a1443f6Edb30138C868566eA3bC'})

        # Deploy and Upgrade
        current_impl = '0x9E8faBaDF7729cea564a150717878B8c1b856731'
        current_comp = '0x6caDf1EB6e14650AF15194ED3D4C78F585598a70'
        self.proxy_admin = ProxyAdmin.at('0xF1861d6e44A171fA42983390dE5810fF06B4544e')

        if self.proxy_admin.getProxyImplementation(current_comp) == current_impl:
            new_impl = Competition.deploy({'from': self.admin})
            Competition.remove(new_impl)
            combined_abi = TransparentUpgradeableProxy.abi + Competition.abi
            self.competition = Contract.from_abi("doesnotmatter", current_comp, combined_abi)
            self.proxy_admin.upgrade(self.competition, new_impl, {'from': self.admin})
            verify(new_impl, self.proxy_admin.getProxyImplementation(self.competition))
            stake_threshold = self.competition.getStakeThreshold()

            # Airdrop to participants
            total_airdrop = int(Decimal(0.001) * Decimal(self.token.totalSupply()))
            single_airdrop = total_airdrop // len(self.participants)
            for i in range(len(self.participants)):
                self.execute_fn(self.token, self.token.transfer,
                                [self.participants[i], single_airdrop,
                                 {'from': '0x592A4441A6Fc71AeCe435D3c8f174BC1315c07fa'}],
                                self.use_multi_admin, exp_revert=False)
        else:
            combined_abi = TransparentUpgradeableProxy.abi + Competition.abi
            self.competition = Contract.from_abi("doesnotmatter", current_comp, combined_abi)

        # Initialise historical values after contract upgrade
        challenge_number = self.competition.getLatestChallengeNumber()
        current_phase = self.competition.getPhase(challenge_number)
        if current_phase == 1:
            self.execute_fn(self.competition, self.competition.closeSubmission, [{'from': self.admin}],
                            self.use_multi_admin, exp_revert=False)

        staker_address_dict, staked_amt_dict = self.open_staker_info_csv()
        chunk = 50
        for cn in range(1, self.latest_stake_record_cn + 1):
            stakers = staker_address_dict[cn]
            amounts = staked_amt_dict[cn]

            size = len(stakers)

            for i in range(0, size, chunk):
                if (i + chunk) > size:
                    stakers_list = stakers[i:]
                    amounts_list = amounts[i:]
                else:
                    stakers_list = stakers[i:i+chunk]
                    amounts_list = amounts[i:i+chunk]

                self.execute_fn(self.competition, self.competition.updateHistoricalStakedAmounts,
                                [cn, stakers_list, amounts_list, {'from': self.admin}], self.use_multi_admin, exp_revert=False)

        self.verify_historical_staked_amounts()

        # Add pre-exisitng stakers.
        pre_existing_stakers = staker_address_dict[challenge_number]
        to_remove = []
        self.execute_fn(self.competition, self.competition.updateStakerSet,
                        [to_remove, pre_existing_stakers, {'from': self.admin}],
                        self.use_multi_admin, exp_revert=False)

        existing_stakers = self.competition.getAllStakers()
        verify(set(pre_existing_stakers), set(existing_stakers))

        # Align backed participant of existing stakers.
        size = len(pre_existing_stakers)
        for i in range(0, size, chunk):
            if i + chunk > size:
                stakers_list = pre_existing_stakers[i:]
            else:
                stakers_list = pre_existing_stakers[i:i + chunk]
            self.execute_fn(self.competition, self.competition.alignBacking,
                            [stakers_list, {'from': self.admin}],
                            self.use_multi_admin, exp_revert=False)

        self.verify_backed_participants_for_self()

    def verify_total_staked(self):
        existing_stakers = self.competition.getAllStakers()
        total_staked = 0
        for staker in existing_stakers:
            total_staked += self.competition.getStake(staker)

        verify(total_staked, self.competition.getCurrentTotalStaked())

    def verify_backed_participants_for_self(self):
        stakers = self.competition.getAllStakers()
        for s in stakers:
            backed_participant = self.competition.getBackedParticipant(s)
            verify(True, backed_participant != self.zero_address)

    def verify_historical_staked_amounts(self):
        staker_address_dict, staked_amt_dict = self.open_staker_info_csv()

        for cn in range(1, self.latest_stake_record_cn + 1):
            stakers = staker_address_dict[cn]
            amounts = staked_amt_dict[cn]
            staker_set = set(self.competition.getHistoricalStakers(cn))
            verify(set(stakers), staker_set)

            amount_list = self.competition.getHistoricalStakeAmounts(cn, stakers)
            verify(amounts, amount_list)

    def open_staker_info_csv(self):
        stakers_file = 'tests//stake_records_up_to_challenge_{}.csv'.format(self.latest_stake_record_cn)
        staker_address_dict = {}
        staked_amt_dict = {}
        with open(stakers_file, 'r') as file:
            reader = csv.reader(file, delimiter=',', quotechar="'", quoting=csv.QUOTE_ALL)
            for row in reader:
                cn = int(row[1])
                staker = row[2]
                amt = int(row[3])
                try:
                    staker_address_dict[cn].append(staker)
                    staked_amt_dict[cn].append(amt)
                except:
                    staker_address_dict[cn] = [staker]
                    staked_amt_dict[cn] = [amt]
        return staker_address_dict, staked_amt_dict