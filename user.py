import utilities
import constants


class User:
    def __init__(self, index=None, race=None, gender=None, user_vrs_prob=None):
        # TODO: Can we do this without hard-coding race and gender so it is easier to add new characteristics?
        self.index = index

        if race is None:
            race = utilities.draw_from_multinomial_distribution(discrete_dist=constants.RACE)
        self.race = race
        if gender is None:
            gender = utilities.draw_from_multinomial_distribution(discrete_dist=constants.GENDER)
        self.gender = gender

        if user_vrs_prob is not None:
            # The idea is privileged subgroups are expensive, so we can use VRS on cheaper subgroups to meet compliance.
            if (self.gender, self.race) not in constants.PRIVILEGED_SUBGROUPS:
                self.user_vrs_prob = 1
            else:
                self.user_vrs_prob = user_vrs_prob
        else:
            self.user_vrs_prob = 1

    def add_index(self, index):
        self.index = index

        # TODO: Variation along ~non-protected characteristic lines
        # 1. Have 1+ catch-all variable(s)
        # 2. We can tune the correlation with race-gender (some subset).
        # 3. This is the variable along which advertisers ARE allowed to discriminate. This is necessary because
        #    otherwise experimentally we would need advertisers to directly pick different based on race-gender OR
        #    pick uniformly - either way this is trivial.
