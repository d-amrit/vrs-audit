import constants
import utilities
import math
import numpy as np


class ImpreciseBISGwithDP:
    def __init__(self, user_race_in_this_batch, metas_race_count, add_dp=False):
        self.user_race_in_this_batch = user_race_in_this_batch
        self.metas_race_count = metas_race_count
        self.add_dp = add_dp

    def implement_metas_noisy_bisg(self):
        bisg_race_counts = self.get_bisg_race_counts()
        if self.add_dp:
            bisg_race_counts = self.add_dp_to_race_counts(bisg_race_counts)
        self.add_noisy_counts(bisg_race_counts)

        return self.metas_race_count

    def get_bisg_race_counts(self):
        """
        NOTE: This implementation differs from Meta.

        Meta feeds a user's surname and zipcode to BISG. It is possible that BISG makes some error, possibly
        non-uniformly between races (e.g. more accurate for Race 1 than Race 2)

        Instead of collecting surnames and zipcodes, we directly model this error probability. We have the true race
        and map it to BISG race with error probability specified in constants.py
        """
        # --------------------------------------------------------------------------------------------------------
        # TODO: Change this implementation. ~ We have not done it because we don't use this component.
        # 1. We originally set user_race_in_this_batch as a list of each race so this iterates over each race and with
        #    some probability assigns it to different races.
        # 2. For space-related reasons, we set user_race_in_this_batch to be a dictionary.
        # 3. Change the implementation so that it reads race: count and then spreads the count by error prob.
        # 4. Current implementation is inefficient but ensures backward compatibility.
        # --------------------------------------------------------------------------------------------------------
        _list_of_user_races = []
        for race, count in self.user_race_in_this_batch.items():
            _list_of_user_races += ([race] * count)
        # --------------------------------------------------------------------------------------------------------

        bisg_race_counts = {i[0]: 0 for i in constants.RACE}
        for true_race in _list_of_user_races:
            bisg_race = self.run_error_prone_bisg(true_race)
            bisg_race_counts[bisg_race] += 1
        return bisg_race_counts

    @staticmethod
    def run_error_prone_bisg(true_race):
        """
        BISG imperfectly predicts race from surname and gender. This imperfection may correlate with true race.
        We use matrix BISG_ERROR_PROB to capture this phenomenon.
        BISG_ERROR_PROB B_ij = Pr[BISG predicts race i | True race is j]
        """
        selection_prob = list(constants.BISG_ERROR_PROB[constants.RACE_IDX[true_race], :])
        discrete_dist = [(race, selection_prob[idx]) for idx, race in enumerate(constants.RACE_IDX)]
        bisg_race = utilities.draw_from_multinomial_distribution(discrete_dist=discrete_dist)
        return bisg_race

    @staticmethod
    def add_dp_to_race_counts(bisg_race_counts):
        var = (2 * math.log(1.25 / constants.DP_DELTA) * (constants.DP_SENSITIVITY ** 2)) / (constants.DP_EPSILON ** 2)
        for race, count in bisg_race_counts.items():
            bisg_race_counts[race] = count + np.random.normal(scale=var)
        return bisg_race_counts

    def add_noisy_counts(self, bisg_race_counts):
        for race in self.metas_race_count.keys():
            self.metas_race_count[race] += bisg_race_counts[race]
