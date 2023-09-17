import numpy as np
import os

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
#     ('African American', 0.136)
# ]
# other_perc = round(1 - sum([i[1] for i in RACE]), 3)
# RACE.append(('Other', other_perc))
RACE = [
    ('White', 0.5),
    ('African American', 0.5)
]
RACE_IDX = {race[0]: idx for idx, race in enumerate(RACE)}
NO_OF_RACES = len(RACE)
RACE_NAMES = [i[0] for i in RACE]

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
P_BOTTOM = 0.85
ADJUST_UP = 2
ADJUST_DOWN = 0.5

COMPLIANCE_REQUIREMENTS = [0.05, 0.1]

# Experiment parameters
HOUSING_BUDGET = 100
SUPPORTED_AUCTION_TYPES = ['first', 'vcg', 'critical_bid']
USE_VRS_FOR_THESE_GROUPS = [('Male', 'White'), ('Female', 'African American')]

COLOR_LIST = ['blue', 'orange', 'green', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']
COLOR_LIST = [f'tab:{i}' for i in COLOR_LIST]
