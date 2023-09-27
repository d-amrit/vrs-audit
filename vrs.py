import numpy as np
import copy
import random

from imprecise_bisg_with_dp import ImpreciseBISGwithDP
import constants


def voting_rule(gender_sign, race_sign, voting_rule_logic):
    """
    Both gender_sign and race_sign can take 3 values:

    +1 = Over-served
    0 = Equally served
    -1 = Under-served

    We aggregate these signs based on different rules.
    """

    if voting_rule_logic == 'AND':
        # Only if both over/under-served report, over/under-served.
        total_sum = gender_sign + race_sign
        if total_sum >= 1:  # previously 2
            return 1
        elif total_sum < 0:  # previously -2
            return -1
        else:
            return 0

    elif voting_rule_logic == 'OR':
        # Only if both over/under-served report, over/under-served.
        if gender_sign == -1 or race_sign == -1:
            return -1
        elif gender_sign == 1 or race_sign == 1:
            return 1
        else:
            return 0

    return 0


def calc_p_percentile_bid(results_without_vrs, percentile_value, multiply_by=100, exclude_housing=False):
    """
    We find the percentile_value of winning bids.
    """
    if exclude_housing:
        results_without_vrs = [i for i in results_without_vrs if not i['winner']['protected_domain']]

    winning_bid_list = [i['winner']['true_bid'] for i in results_without_vrs]
    p_top_bid = np.percentile(winning_bid_list, percentile_value * multiply_by)
    return p_top_bid


class VarianceReductionSystem:
    def __init__(self, calc_gender_var, calc_race_var, batch_size,
                 use_noisy_bisg=False, adjust_down=False):
        self.calc_gender_var = calc_gender_var
        self.calc_race_var = calc_race_var
        self.batch_size = batch_size

        self.use_noisy_bisg = use_noisy_bisg
        self.adjust_down = adjust_down
        self.count = 0

        # Metrics to track when a user's bid is not adjusted due to user-value or being part of an over- and under-
        # served demographic

        self.gender_under_race_over = self.initialize_race_gender_count_dict()
        self.gender_over_race_under = self.initialize_race_gender_count_dict()
        self.missed_due_to_user_var = self.initialize_race_gender_count_dict()
        self.vrs_applied = self.initialize_race_gender_count_dict()

    def update_vrs_related_parameters(self, vrs_ad_reach, total_no_of_users,
                                      metas_race_count, user_race_in_this_batch,
                                      target_race_count, true_race_count, race_var_sign,
                                      target_gender_count, gender_count, gender_var_sign,
                                      target_gender_race_count, gender_race_count, gender_race_var_sign):
        self.count += 1

        _count_of_users = sum(user_race_in_this_batch.values()) % self.batch_size
        assert (vrs_ad_reach % self.batch_size) == _count_of_users, f'Sum of race counts ({_count_of_users}) does ' \
                                                                    f'NOT match ad_reach ({vrs_ad_reach}).'

        if vrs_ad_reach % self.batch_size == 0:
            if self.use_noisy_bisg:
                bisg = ImpreciseBISGwithDP(
                    user_race_in_this_batch=user_race_in_this_batch,
                    metas_race_count=metas_race_count
                )
                metas_race_count = bisg.implement_metas_noisy_bisg()
            else:
                metas_race_count = copy.deepcopy(true_race_count)

            # Update variance sign of each subgroup.
            if self.calc_race_var:
                race_var_sign = self.update_variance_sign(
                    vrs_ad_reach=vrs_ad_reach,
                    count_dict=metas_race_count,
                    population_dist=target_race_count,
                    total_no_of_users=total_no_of_users
                )
                user_race_in_this_batch = {i[0]: 0 for i in constants.RACE}

            if self.calc_gender_var:
                gender_var_sign = self.update_variance_sign(
                    vrs_ad_reach=vrs_ad_reach,
                    count_dict=gender_count,
                    population_dist=target_gender_count,
                    total_no_of_users=total_no_of_users
                )

            gender_race_var_sign = self.update_variance_sign(
                vrs_ad_reach=vrs_ad_reach,
                count_dict=gender_race_count,
                population_dist=target_gender_race_count,
                total_no_of_users=total_no_of_users
            )

        return {
            'metas_race_count': metas_race_count,
            'race_var_sign': race_var_sign,
            'gender_var_sign': gender_var_sign,
            'gender_race_var_sign': gender_race_var_sign,
            'user_race_in_this_batch': user_race_in_this_batch
        }

    @staticmethod
    def update_variance_sign(vrs_ad_reach, count_dict, population_dist, total_no_of_users=1):
        """
        population_dist is the demographic distribution of UNIQUE users served upto this point in the experiment.
        """
        _var_sign_dict = {}
        for demographic, count in population_dist.items():
            exp_no_of_ads = (count / total_no_of_users) * vrs_ad_reach
            _diff = count_dict[demographic] - exp_no_of_ads
            if _diff < 0:
                _var_sign_dict[demographic] = -1
            elif _diff == 0:
                _var_sign_dict[demographic] = 0
            else:
                _var_sign_dict[demographic] = 1

        return _var_sign_dict

    @staticmethod
    def initialize_race_gender_count_dict():
        return {f'{g}-{r}': 0 for g in constants.GENDER_NAMES for r in constants.RACE_NAMES}

    @staticmethod
    def increment_race_gender_dict(input_dict, user):
        input_dict[f'{user.gender}-{user.race}'] += 1
        return input_dict

    def calc_vrs_multiplier(self, user, protected_domain, vrs_ad_reach,
                            gender_var_sign, race_var_sign):
        # VRS multiplier = 1 for advertisers in non-protected domains.
        if not protected_domain:
            return 1

        # We do not implement VRS for the first batch of ad slots
        if vrs_ad_reach < self.batch_size:
            return 1

        # Code that allows us to ensure that we can check variance only for gender or race. We put this code before
        # vrs_random_coin since we want to track when gender and race have the opposite variance sign.
        if self.calc_gender_var and not self.calc_race_var:
            gender_sign = race_sign = gender_var_sign[user.gender]
        elif self.calc_gender_var and not self.calc_race_var:
            gender_sign = race_sign = race_var_sign[user.race]
        else:
            gender_sign = gender_var_sign[user.gender]
            race_sign = race_var_sign[user.race]

            if gender_sign == -1 and race_sign == 1:
                self.increment_race_gender_dict(self.gender_under_race_over, user)
            elif gender_sign == 1 and race_sign == -1:
                self.increment_race_gender_dict(self.gender_over_race_under, user)

        adjust_up_based_on_sign = gender_sign + race_sign < 0
        adjust_down_based_on_sign = self.adjust_down and gender_sign + race_sign > 0
        # adjust_up_based_on_sign = gender_sign == -1 or race_sign == -1
        # adjust_down_based_on_sign = self.adjust_down and (gender_sign == 1 or race_sign == 1)

        # User.user_vrs_prob models the probability that we will use VRS for this user.
        vrs_random_coin = random.random()
        if adjust_up_based_on_sign or adjust_down_based_on_sign:
            if vrs_random_coin <= user.user_vrs_prob:
                # We only adjust up if neither gender or race are over-served. (So under/under, under/equal,
                # equal/under are allowed). Similar logic used for adjust down.
                if adjust_up_based_on_sign:
                    self.increment_race_gender_dict(self.vrs_applied, user)
                    return constants.ADJUST_UP
                elif adjust_down_based_on_sign:
                    self.increment_race_gender_dict(self.vrs_applied, user)
                    return constants.ADJUST_DOWN
            else:
                self.increment_race_gender_dict(self.missed_due_to_user_var, user)

        return 1
