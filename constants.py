import numpy as np
import os
import itertools

SAVE_PATH = '/Users/amrit/Documents/Code/VRS Audit/experimental_results/'
if not os.path.exists(SAVE_PATH):
    SAVE_PATH = ''


GENDER = [
    ('Male', 0.5),
    ('Female', 0.5)
]
NO_OF_GENDERS = len(GENDER)
GENDER_NAMES = [i[0] for i in GENDER]

# RACE = [
#     ('White', 0.589),
#     ('Hispanic', 0.191),
#     ('Black', 0.136)
# ]
# other_perc = round(1 - sum([i[1] for i in RACE]), 3)
# RACE.append(('Other', other_perc))
RACE = [
    ('White', 0.5),
    ('Black', 0.5)
]
RACE_IDX = {race[0]: idx for idx, race in enumerate(RACE)}
NO_OF_RACES = len(RACE)
RACE_NAMES = [i[0] for i in RACE]

GENDER_RACE_NAMES = [f'{g}-{r}' for g in GENDER_NAMES for r in RACE_NAMES]

# BISG introduces some error. The (i, j)th cell in this matrix represents Pr[BISG predicts race j | True race is j].
# For now we have set this to the identity matrix which means BISG perfectly predicts each race.
BISG_ERROR_PROB = np.eye(len(RACE))

# Differential Privacy (DP) Parameters
DP_DELTA = 0.1
DP_EPSILON = 1
DP_SENSITIVITY = 1

# Meta's VRS system sets the VRS multiplier to P40 (resp. B85) to bring the ad to the top (resp. bottom) of the ad
# auction 40% (resp. 85%) of the time.
P_TOP = 0.40
P_BOTTOM = 0.15
ADJUST_UP = 2
ADJUST_DOWN = 0.5

COMPLIANCE_REQUIREMENTS = [0.05, 0.1]

# Experiment parameters
HOUSING_BUDGET = 100

SUPPORTED_AUCTION_TYPES = ['first', 'second', 'vcg', 'critical_bid']
SUPPORTED_VOTING_RULES = [min, max, np.mean]
DEPRECATED_VOTING_RULES = ['AND-inclusive', 'AND-exclusive', 'OR', 'track-race-gender']
PRIVILEGED_SUBGROUPS = [('Male', 'White'), ('Female', 'Black')]

COLOR_LIST = ['blue', 'orange', 'green', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']
COLOR_LIST = [f'tab:{i}' for i in COLOR_LIST]
OVER_UNDER_SERVED_MAP = {
    1: 'over',
    0: None,
    -1: 'under'
}
DEMOGRAPHICS_TRACKED = ['gender', 'race']
GROUPS_TO_SUBGROUPS = {
    'race': RACE_NAMES,
    'gender': GENDER_NAMES
}
SUBGROUP_FREQUENCY = {
    'White': 0.5,
    'Black': 0.5,
    'Male': 0.5,
    'Female': 0.5
}
# Calculate frequency for cross-product of subgroups
subgroups_by_char = [GROUPS_TO_SUBGROUPS[char] for char in DEMOGRAPHICS_TRACKED]
subgroup_cross_product = [i for i in itertools.product(*subgroups_by_char)]
for subgroup in subgroup_cross_product:
    freq = np.prod([SUBGROUP_FREQUENCY[i] for i in subgroup])
    SUBGROUP_FREQUENCY['-'.join(subgroup)] = freq
