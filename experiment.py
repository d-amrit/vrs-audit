"""
TODO:

1. Hard-coding of mu-sigma

WHAT? We would like to remove experiment hard-coding of mu/sigma, male/female mu mu/sigma. This should entirely be
handled in the advertiser class. However, for the experiment to run, we do need to set those values.

WHEN TO ADDRESS THIS? If and when we want (non-)housing advertisers to have different mu-sigma.
"""
import numpy as np
import random
import os
import json
import datetime
import copy

from advertiser import Advertiser
from user import User
from auction import Auction
import utilities
import constants
import vrs


class Experiment:
    """
    1. To compare impressions vs users, we can create a original and fake index so we don't need to change the code.
    """

    def __init__(self, random_state=0, auction_type='critical_bid',
                 advertiser_list=None, no_of_housing_advertisers=1,
                 no_of_non_housing_advertisers=1,
                 housing_budget=100, non_housing_budget=1000,
                 mu=None, sigma=None,
                 housing_value_mu=-4.4, housing_value_sigma=0.8,
                 non_housing_value_male_mu=-4.4, non_housing_value_male_sigma=0.8,
                 non_housing_value_female_mu=-4.4, non_housing_value_female_sigma=0.8,
                 non_housing_diff=None,
                 user_list=None, no_of_users=40_000, ad_slot_per_user=1,
                 user_vrs_prob=None, voting_rule_logic='max',
                 calc_gender_var=True, calc_race_var=True, use_noisy_bisg=False,
                 adjust_down=False, batch_size=10, p_top=constants.P_TOP, p_bottom=constants.P_BOTTOM):
        """
        user_vrs_prob is the probability with which VRS is applied to a specific user. For now, this is group-based,
        and allows us to specify "use VRS to win 'cheaper' groups" to satisfy compliance. If user_vrs_prob = 0, then
        we _never_ use VRS to win a slot for the user. Similarly, if user_vrs_prob = 1, then we use VRS _as appropriate_
         to win a slot for the user.
        """

        # Initializing random state for replication purposes.
        utilities.initialize_random_state(random_state)

        # See auction.py for definition of diff.
        _auction_types = ', '.join(constants.SUPPORTED_AUCTION_TYPES)
        assert auction_type in constants.SUPPORTED_AUCTION_TYPES, f"{auction_type} is not supported. " \
                                                                  f"Only {_auction_types} auction types are supported."
        self.auction_type = auction_type

        _voting_rules = ', '.join(constants.SUPPORTED_VOTING_RULES)
        assert voting_rule_logic in constants.SUPPORTED_VOTING_RULES, f"{voting_rule_logic} is not supported. Only " \
                                                                      f"{_voting_rules} auction types are supported."
        self.voting_rule_logic = voting_rule_logic

        # VRS-specific variables.
        self.calc_gender_var = calc_gender_var
        self.calc_race_var = calc_race_var
        self.batch_size = batch_size
        self.use_noisy_bisg = use_noisy_bisg
        self.p_top = p_top
        self.p_bottom = p_bottom
        self.adjust_down = adjust_down

        # Advertisers
        self.no_of_housing_advertisers = no_of_housing_advertisers
        self.no_of_non_housing_advertisers = no_of_non_housing_advertisers
        self.housing_budget = housing_budget
        self.non_housing_budget = non_housing_budget
        self.non_housing_diff = non_housing_diff

        if self.non_housing_diff:
            assert mu is not None and sigma is not None, 'For testing purposes, we want to all advertisers have the ' \
                                                         'same mu and sigma, and the difference is driven by non_' \
                                                         'housing_diff.'

        if mu is not None:
            self.housing_value_mu = mu
            self.non_housing_value_male_mu = mu
            self.non_housing_value_female_mu = mu
        else:
            self.housing_value_mu = housing_value_mu
            self.non_housing_value_male_mu = non_housing_value_male_mu
            self.non_housing_value_female_mu = non_housing_value_female_mu
        if sigma is not None:
            self.housing_value_sigma = sigma
            self.non_housing_value_male_sigma = sigma
            self.non_housing_value_female_sigma = sigma
        else:
            self.housing_value_sigma = housing_value_sigma
            self.non_housing_value_male_sigma = non_housing_value_male_sigma
            self.non_housing_value_female_sigma = non_housing_value_female_sigma

        self.input_advertiser_list = advertiser_list
        self.advertiser_list = self.get_advertiser_list(self.input_advertiser_list)
        self.housing_adv_budget_exhausted = [False for _ in range(no_of_housing_advertisers)]

        # Unique users and ad slots.
        self.user_vrs_prob = user_vrs_prob
        self.user_list = self.get_user_list(user_list, no_of_users)
        self.ad_slot_per_user = ad_slot_per_user
        self.ad_slot_list = self.gen_ad_slot_list()

        # Index of users that we have already seen. Count by protected characteristics.
        self.unique_users = set()
        self.target_gender_count = {i[0]: 0 for i in constants.GENDER}
        self.target_race_count = {i[0]: 0 for i in constants.RACE}
        self.target_gender_race_count = {i: 0 for i in constants.GENDER_RACE_NAMES}

        self.results = [{
            'bid_list': None,
            'user': user,
            'race': user.race,
            'gender': user.gender
        } for user in self.ad_slot_list]
    
    def get_advertiser_list(self, advertiser_list):
        if advertiser_list is not None:
            return advertiser_list
        else:
            housing = [
                Advertiser(
                    index=i,
                    budget=self.housing_budget,
                    protected_domain=True,
                    male_mu=self.housing_value_mu,
                    female_mu=self.housing_value_mu,
                    male_sigma=self.housing_value_sigma,
                    female_sigma=self.housing_value_sigma,
                    vrs_class=vrs.VarianceReductionSystem(
                        calc_gender_var=self.calc_gender_var,
                        calc_race_var=self.calc_race_var,
                        batch_size=self.batch_size,
                        use_noisy_bisg=self.use_noisy_bisg,
                        adjust_down=self.adjust_down
                    )
                ) for i in range(self.no_of_housing_advertisers)]
            non_housing = [
                Advertiser(
                    index=i,
                    budget=self.non_housing_budget,
                    protected_domain=False,
                    male_mu=self.non_housing_value_male_mu,
                    female_mu=self.non_housing_value_female_mu,
                    male_sigma=self.non_housing_value_male_sigma,
                    female_sigma=self.non_housing_value_female_sigma,
                    diff=self.non_housing_diff
                ) for i in range(self.no_of_housing_advertisers, self.no_of_non_housing_advertisers + 1)
            ]
            advertiser_list = housing + non_housing
            return advertiser_list

    def get_user_list(self, user_list, no_of_users, create_equal_fraction=False):
        if user_list is not None:
            return user_list
        elif no_of_users is not None:
            if create_equal_fraction:
                _gr = [(race, gender) for race in constants.RACE_NAMES for gender in constants.GENDER_NAMES]
                no_of_copies = (no_of_users // len(_gr))
                _user_list = [User(race=race, gender=gender, user_vrs_prob=self.user_vrs_prob)
                              for race, gender in _gr
                              for _ in range(no_of_copies)
                              ]
                for idx, u in enumerate(_user_list):
                    u.index = idx
                random.shuffle(_user_list)
            else:
                _user_list = [User(index=i, user_vrs_prob=self.user_vrs_prob) for i in range(no_of_users)]

            set_of_user_values = set([i.user_vrs_prob for i in _user_list])
            if self.user_vrs_prob not in [1, None]:
                assert self.user_vrs_prob in set_of_user_values, 'User VRS probability has not been added to users.'
            else:
                assert set_of_user_values == {1}, 'user_vrs_prob is None BUT vrs_prob is NOT 1 for all users.'
            return _user_list
        else:
            raise utilities.CustomError('Please specify either user_list or no_of_users.')
    
    def gen_ad_slot_list(self):
        """
        TODO: Maybe we want to change this. Make number of ad slots a user sees to be a random variable?
        What's the distribution?
        """
        ad_slot_list = self.user_list * self.ad_slot_per_user
        random.shuffle(ad_slot_list)
        return ad_slot_list
        
    def maintain_set_of_unique_users(self, user):
        if user.index not in self.unique_users:
            self.target_gender_count[user.gender] += 1
            self.target_race_count[user.race] += 1
            self.target_gender_race_count[f'{user.gender}-{user.race}'] += 1
            self.unique_users.add(user.index)

    def update_winning_advertiser(self, user, winner, update_vrs):
        # Update amount spent by winner.
        self.advertiser_list[winner['idx']].update_params_after_winning_ad_slot(
            amount_spent=winner['price_paid'],
            update_vrs=update_vrs,
            user=user,
            target_gender_count=self.target_gender_count,
            target_race_count=self.target_race_count,
            target_gender_race_count=self.target_gender_race_count,
            total_no_of_users=len(self.unique_users)
        )

    def simulate(self, apply_vrs=False, vrs_over_bid=None, vrs_under_bid=None, prefix=''):
        for auction_idx, r in enumerate(self.results):
            # 2nd simulation: Maintain set of users + target_{race, gender, race-gender}_count.
            if apply_vrs:
                self.maintain_set_of_unique_users(r['user'])

            a = Auction(
                advertiser_list=self.advertiser_list,
                user=r['user'],
                auction_type=self.auction_type,
                voting_rule_logic=self.voting_rule_logic,
            )
            winner, bid_list = a.run(
                bid_list=r['bid_list'],
                apply_vrs=apply_vrs,
                vrs_over_bid=vrs_over_bid,
                vrs_under_bid=vrs_under_bid,
            )

            # Update winning advertiser.
            _update_vrs = apply_vrs and winner['protected_domain']
            self.update_winning_advertiser(r['user'], winner, update_vrs=_update_vrs)

            # Save results ~ For some reason without deepcopy, this wasn't saving correctly.
            self.results[auction_idx].update({
                f'{prefix}winner': copy.deepcopy(winner),
                f'{prefix}bid_list': bid_list[:],
            })

            # Only the winning advertiser's status could have changed so we check only their status.
            if self.check_if_all_housing_adv_have_spent_budget(winner['idx']):
                # 1st simulation: Ends when all housing advertisers have exhausted their budget. By design, this occurs
                # before all users are served, truncate the results.
                if not apply_vrs:
                    self.results = self.results[:auction_idx + 1]
                return

    def run(self):
        # Run auction w/o VRS.
        self.simulate()

        # Reset advertisers.
        self.advertiser_list = self.get_advertiser_list(advertiser_list=self.input_advertiser_list)
        self.housing_adv_budget_exhausted = [False for _ in range(self.no_of_housing_advertisers)]

        # VRS-stuff.
        vrs_over_bid = vrs.calc_p_percentile_bid(self.results[:], self.p_top)
        if self.adjust_down:
            vrs_under_bid = vrs.calc_p_percentile_bid(self.results[:], self.p_bottom)
        else:
            vrs_under_bid = None

        # Run auction with VRS.
        self.simulate(
            apply_vrs=True,
            vrs_over_bid=vrs_over_bid,
            vrs_under_bid=vrs_under_bid,
            prefix='vrs_'
        )

    def check_if_all_housing_adv_have_spent_budget(self, idx):
        """
        We end the experiment when every housing advertiser has exhausted their budget.
        """
        _adv = self.advertiser_list[idx]
        if _adv.protected_domain:
            self.housing_adv_budget_exhausted[idx] = _adv.amount_spent > _adv.budget
        return all(self.housing_adv_budget_exhausted)

    # --------------------------------------------------------------------------------------------------------------
    # Test cases.
    # --------------------------------------------------------------------------------------------------------------

    def test_check_if_regular_winner_was_correctly_calculated(self):
        for iteration, result in enumerate(self.results):
            _bid_list = result['bid_list']
            _max_total_score = max([i[0] for i in _bid_list])
            check_total_score = result['winner']['total_score'] == _max_total_score
            _max_true_bid = max([i[1] for i in _bid_list])
            check_true_bid = result['winner']['true_bid'] == _max_true_bid
            assert check_total_score and check_true_bid, f'Regular winner was incorrectly chosen in ' \
                                                         f'iteration {iteration}.'

    def _get_list_of_idx_of_vrs_winner(self):
        # Used in test_var_sign method.
        # Get list of indices for ad slots that the housing advertiser won.
        count = 0
        idx_list = []
        for idx, r in enumerate(self.results):
            if r['vrs_winner']['idx'] == 0:
                count += 1
                if count % 10 == 0:
                    idx_list.append(idx)
        assert count > 0, 'VRS never changed the result of the auction. Something is wrong.'
        return idx_list

    @staticmethod
    def test_individual_demographic_var_sign(results_dict, idx, demographic, demographic_name_list):
        # Explicitly check that variance sign was correctly calculated.
        t = utilities.convert_count_dict_to_list_of_perc(results_dict[f'target_{demographic}_count'])
        a = utilities.convert_count_dict_to_list_of_perc(results_dict[f'{demographic}_count'])

        _diff = np.array(a) - np.array(t)
        _diff = np.where(_diff < 0)[0]
        if _diff.size > 0:
            underserved_demographic = demographic_name_list[_diff[0]]

            assert results_dict[f'{demographic}_var_sign'][underserved_demographic] == -1, \
                f'{demographic.title} variance is incorrectly assigned. Look at iteration {idx}'

    def test_var_sign(self):
        idx_list = self._get_list_of_idx_of_vrs_winner()
        for idx in idx_list:
            _d = self.results[idx]
            self.test_individual_demographic_var_sign(results_dict=_d, idx=idx, demographic='gender',
                                                      demographic_name_list=constants.GENDER_NAMES)
            self.test_individual_demographic_var_sign(results_dict=_d, idx=idx, demographic='race',
                                                      demographic_name_list=constants.RACE_NAMES)

    def test_results(self):
        self.test_check_if_regular_winner_was_correctly_calculated()
        # TODO: Re-add
        # self.test_check_vrs_random_coin_implementation()
        self.test_var_sign()

    def save_results(self, suffix=None):
        self.test_results()
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S:%f')
        file_name = f'VRS_Audit_Experiment_Result_{timestamp}'
        if suffix is not None:
            file_name = f'{file_name}_{suffix}'
        file_path = os.path.join(constants.SAVE_PATH, file_name)
        open(f'{file_path}.json', 'w').write(json.dumps({'Results': self.results}))


if __name__ == '__main__':
    pass
