import numpy as np

import utilities
import constants


class Advertiser:
    def __init__(self, index, vrs=None, protected_domain=False, budget=100,
                 male_mu=-2.4, female_mu=-2.4, male_sigma=0.84, female_sigma=0.84, diff=None,
                 est_action_rate=1, quality_score=0):

        self.index = index
        self.protected_domain = protected_domain
        self.budget = budget
        self.est_action_rate = est_action_rate
        self.quality_score = quality_score

        self.vrs = vrs

        # TODO (1/2): I really don't like this. We need a cleaner way to allow bids to vary by user demographic.
        # Bid-related parameters.
        self.male_mu = male_mu
        self.male_sigma = male_sigma
        self.female_mu = female_mu
        self.female_sigma = female_sigma
        self.diff = diff

        # Ensure an advertiser sets same mu and sigma for men and women.
        if self.protected_domain:
            assert self.male_mu == self.female_mu and self.male_sigma == self.female_sigma, \
                'Advertisers in protected domains are not allowed to discriminate based on gender.'

        self.amount_spent = 0
        self.unique_users_reached = set()
        self.user_race_in_this_batch = {i[0]: 0 for i in constants.RACE}

        # TODO: Ideally, we would not like to hard code this.
        self.gender_count = {i[0]: 0 for i in constants.GENDER}
        self.gender_var_sign = {i[0]: 0 for i in constants.GENDER}

        self.true_race_count = {}
        self.metas_race_count = {}
        self.race_var_sign = {}
        for race in constants.RACE:
            self.true_race_count[race[0]] = 0
            self.metas_race_count[race[0]] = 0
            self.race_var_sign[race[0]] = 0

        self.iteration_count = 0

    def calc_user_based_bid(self, user):
        # TODO (2/2): Find cleaner way to allow them to vary their bid by user demographic.

        # Non-housing advertiser's vary their bids by diff based on race-gender.
        non_housing = not self.protected_domain
        diff_defined = self.diff is not None
        user_in_selected_groups = (user.gender, user.race) not in constants.USE_VRS_FOR_THESE_GROUPS
        if non_housing and diff_defined and user_in_selected_groups:
            assert self.male_mu == self.female_mu, 'For testing purposes, if we use diff, we do not want them to be' \
                                                   ' different but they are. Please change this!'
            bid = np.random.lognormal(mean=self.female_mu + self.diff, sigma=self.female_sigma)

        elif user.gender == 'Female':
            bid = np.random.lognormal(mean=self.female_mu, sigma=self.female_sigma)
        elif user.gender == 'Male':
            bid = np.random.lognormal(mean=self.male_mu, sigma=self.male_sigma)
        else:
            raise utilities.CustomError(f"Gender {user.gender} not supported. Please use 'Male' or 'Female'.")

        return bid

    @staticmethod
    def test_that_vrs_multiplier_works(vrs_multiplier, var_sign_dict, demographic):
        # Ensure VRS works.
        if var_sign_dict[demographic] == 0:
            assert vrs_multiplier == 1
        elif var_sign_dict[demographic] == -1:
            assert vrs_multiplier == constants.ADJUST_UP
        elif var_sign_dict[demographic] == 1:
            assert vrs_multiplier == constants.ADJUST_DOWN
        else:
            raise utilities.CustomError(f'Something is wrong! vrs_multiplier = {vrs_multiplier} but it should only be '
                                        f'-1, 0, or 1.')

    def update_params_after_winning_ad_slot(self, amount_spent, update_vrs, user=None,
                                            target_gender_count=None, target_race_count=None,
                                            total_no_of_users=None):
        """
        When an advertiser wins an ad auction, we:

        1. Add their bid to the amount spent.
        2. For later auditing, record the user's gender and race.
        3. After every k ads an advertiser displays, update the noisy race count using Meta's
           proposed system.
        """
        # TODO: We need a way to track amount spent. I'm not sure if we need to separately track VRS spend and non-VRS
        #  spend and then accordingly change the bidding rule to account for both.
        if not update_vrs:
            self.amount_spent += amount_spent

        # We do not count impressions to unique users.
        if update_vrs and user.index not in self.unique_users_reached:
            self.unique_users_reached.add(user.index)

            self.gender_count[user.gender] += 1
            self.true_race_count[user.race] += 1
            self.user_race_in_this_batch[user.race] += 1

            _p = self.vrs.update_vrs_related_parameters(
                vrs_ad_reach=len(self.unique_users_reached),
                user_race_in_this_batch=self.user_race_in_this_batch,
                target_gender_count=target_gender_count,
                target_race_count=target_race_count,
                true_race_count=self.true_race_count,
                metas_race_count=self.metas_race_count,
                gender_count=self.gender_count,
                total_no_of_users=total_no_of_users,
                race_var_sign=self.race_var_sign,
                gender_var_sign=self.gender_var_sign,
            )

            self.metas_race_count, self.race_var_sign, self.gender_var_sign, self.user_race_in_this_batch = _p
