import numpy as np

import vrs
import utilities
import constants


class Advertiser:
    def __init__(self, index, vrs_class=None, protected_domain=False, budget=100,
                 male_mu=-2.4, female_mu=-2.4, male_sigma=0.84, female_sigma=0.84, diff=None,
                 est_action_rate=1, quality_score=0):

        self.index = index
        self.protected_domain = protected_domain
        self.budget = budget
        # TODO: Add functions calc_est_action_rate(user) and calc_quality_score(user) that allow this to vary by user.
        self.est_action_rate = est_action_rate
        self.quality_score = quality_score
        self.vrs_class = vrs_class

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
        # TODO: Currently gender-race doesn't incorporate noisy race labels.
        self.gender_race_count = {i: 0 for i in constants.GENDER_RACE_NAMES}
        self.gender_race_var_sign = {i: 0 for i in constants.GENDER_RACE_NAMES}

        self.gender_count = {i[0]: 0 for i in constants.GENDER}
        self.gender_var_sign = {i[0]: 0 for i in constants.GENDER}

        self.true_race_count = {}
        self.metas_race_count = {}
        self.race_var_sign = {}
        for race in constants.RACE:
            self.true_race_count[race[0]] = 0
            self.metas_race_count[race[0]] = 0
            self.race_var_sign[race[0]] = 0

        # TODO: Review. I think this is okay. Just read from constants.
        self.vrs_multiplier = {subgroup: 1 for subgroup in constants.SUBGROUP_FREQUENCY.keys()}

    def calc_user_based_bid(self, user):
        # TODO (2/2): Find cleaner way to allow them to vary their bid by user demographic.

        # Non-housing advertiser's vary their bids by diff based on race-gender.
        non_housing = not self.protected_domain
        diff_defined = self.diff is not None
        user_in_selected_groups = (user.gender, user.race) in constants.PRIVILEGED_SUBGROUPS
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

    def calc_est_action_rate(self):
        # TODO: Implement. We possibly want this to vary by user.
        return self.est_action_rate

    def calc_quality_score(self):
        # TODO: Implement. We possibly want this to vary by user.
        return self.quality_score

    def calc_bid_for_each_advertiser(self, user, true_bid=None, vrs_multiplier=1,
                                     vrs_over_bid=None, vrs_under_bid=None):
        # Calculated by the platform but dependent on advertiser inputs (e.g. budget).
        if true_bid is None:
            true_bid = self.calc_user_based_bid(user)

        true_bid = true_bid * vrs_multiplier
        # Here we are retaining the {vrs_over_bid, vrs_under_bid} to allow for constraints on how large/small we are
        # allowed to make an advertiser's bid.
        if vrs_over_bid is not None:
            true_bid = min(true_bid, vrs_over_bid)
        if vrs_under_bid is not None:
            true_bid = max(true_bid, vrs_under_bid)

        quality_score = self.calc_quality_score()
        est_action_rate = self.calc_est_action_rate()
        advertiser_component = est_action_rate * true_bid
        total_score = advertiser_component + quality_score

        # We pick winners based on the normalized bid and charge the winner their true bid.
        return self.index, total_score, true_bid

    def is_demographic_under_or_over_served(self, user, voting_rule_logic):
        if voting_rule_logic == 'track-race-gender':
            _sign = self.gender_race_var_sign[f'{user.gender}-{user.race}']
        else:
            _sign = vrs.voting_rule(
                gender_sign=self.gender_var_sign[user.gender],
                race_sign=self.race_var_sign[user.race],
                voting_rule_logic=voting_rule_logic
            )

        return constants.OVER_UNDER_SERVED_MAP[_sign]

    def update_params_after_winning_ad_slot(self, amount_spent, update_vrs, user=None,
                                            target_gender_count=None, target_race_count=None,
                                            target_gender_race_count=None, total_no_of_users=None):
        """
        When an advertiser wins an ad auction, we:

        1. Add their bid to the amount spent.
        2. For later auditing, record the user's gender and race.
        3. After every k ads an advertiser displays, update the noisy race count using Meta's
           proposed system.
        """
        if not update_vrs:
            self.amount_spent += amount_spent

        # We do not count impressions to unique users.
        if update_vrs and user.index not in self.unique_users_reached and self.protected_domain:
            self.unique_users_reached.add(user.index)

            self.gender_race_count[f'{user.gender}-{user.race}'] += 1
            self.gender_count[user.gender] += 1
            self.true_race_count[user.race] += 1
            self.user_race_in_this_batch[user.race] += 1

            _p = self.vrs_class.update_vrs_related_parameters(
                vrs_ad_reach=len(self.unique_users_reached),
                total_no_of_users=total_no_of_users,
                # Currently unused - present to implement Meta's noisy BISG.
                metas_race_count=self.metas_race_count,
                user_race_in_this_batch=self.user_race_in_this_batch,
                # Race-related variables.
                target_race_count=target_race_count,
                true_race_count=self.true_race_count,
                race_var_sign=self.race_var_sign,
                # Gender-related variables.
                target_gender_count=target_gender_count,
                gender_count=self.gender_count,
                gender_var_sign=self.gender_var_sign,
                # Gender-Race related variables.
                target_gender_race_count=target_gender_race_count,
                gender_race_count=self.gender_race_count,
                gender_race_var_sign=self.gender_race_var_sign,
            )

            # Written this way to avoid overflow
            self.metas_race_count = _p['metas_race_count']
            self.race_var_sign = _p['race_var_sign']
            self.gender_var_sign = _p['gender_var_sign']
            self.gender_race_var_sign = _p['gender_race_var_sign']
            self.user_race_in_this_batch = _p['user_race_in_this_batch']
