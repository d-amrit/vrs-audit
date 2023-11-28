"""
TODO:
1. We need to add new slates with housing advertisers in the final spots BUT the payment needs to be correctly handled.
2. We need to calculate utility.
3. We will need to add a 1 - delta constraint.
-----------------------------------------------------------------------------------------------------------------------
"""
import itertools
import numpy as np
# from numpy.random import lognormal
from numpy.random import uniform
import random
import math
import pulp

import utilities
import constants


def find_small_example_that_meets_condition(n=None, m=8, k=2, no_of_housing_adv=2, alpha=0, beta=0.1):
    if n is None:
        n = k + 2
    condition_met = False
    random_state = 0
    while not condition_met:
        data = VrsLpData(m=m, k=k, n=n, no_of_housing_adv=no_of_housing_adv, alpha=alpha, beta=beta,
                         random_state=random_state)
        lp = VrsLp(vrs_lp_data=data)
        lp.solve()
        _r = data.compare_lp_solution_to_independent_auctions(lp_allocation=lp.matrix_pi)
        auction_slates, lp_slates, auction_price, lp_price = _r
        print(random_state, auction_price, lp_price)

        # print('Slates chosen by IA:', auction_slates)
        # print('Slates chosen by LP:', lp_slates)
        # print('\n')
        # for adv, value in auction_price.items():
        #     ind_count = len([slate for slate in auction_slates if adv in slate])
        #     lp_count = len([slate for slate in lp_slates if adv in slate])
        #
        #     _v1 = '%.2f' % (value / ind_count) if ind_count > 0 else '0.00'
        #     _v2 = '%.2f' % (lp_price[adv] / lp_count) if lp_count > 0 else '0.00'
        #     print(f"Adv {adv}'s allocation: "
        #           f"({ind_count}, ${_v1}) in ind. auctions and "
        #           f"({lp_count}, ${_v2}) in LP allocation.")

        random_state += 1
        condition_met = (auction_slates != lp_slates) or random_state > 100


class VrsLpData:
    def __init__(self, m, k, n=None, random_state=0,
                 matrix_bids=None,
                 no_of_housing_adv=1,
                 protected_characteristics=None,
                 alpha=1, beta=1, gamma=0.0, delta=1,
                 position_discount=0.9, allow_over_under_bidding=False):
        # Initialize the randomness for replicable results.
        utilities.initialize_random_state(random_state)

        # Define dimensions of the data.
        self.m = m
        self.k = k
        if n is None:
            n = self.k + 2
        self.n = n
        self.position_discount = position_discount
        self.allow_over_under_bidding = allow_over_under_bidding

        # Advertiser-related information. WLOG, we assume the first {{no_of_housing_adv}} advertisers are housing advs.
        self.no_of_housing_adv = no_of_housing_adv
        self.housing_adv = list(range(self.no_of_housing_adv))
        self.non_housing_adv = list(range(self.no_of_housing_adv, self.n))
        self.budget_vector = self.gen_budgets()

        # Demographic-related information.
        if protected_characteristics is None:
            protected_characteristics = ['race', 'gender']
        self.protected_characteristics = protected_characteristics
        self.subgroups = []
        for char in self.protected_characteristics:
            self.subgroups += constants.GROUPS_TO_SUBGROUPS[char]
        self.users_demographics, self.subgroup_user_idx_map = self.assign_demographic_groups()
        
        # Parameters of the problem.
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma
        self.delta = delta
        # We use M to linearize y_A^{(h)} = 1 if housing advertiser h is compliant w.r.t. characteristic A (e.g. race).
        self.M = 100 * self.m

        # Get each advertiser's bid, quality score, EAR, and score for each user.
        self.matrix_bids = self.gen_bid_landscape(matrix_bids)
        self.matrix_qs = self.gen_quality_score()
        self.matrix_ear = self.gen_estimated_action_rate()
        self.matrix_scores = np.multiply(self.matrix_bids, self.matrix_ear) + self.matrix_qs

        # Consider all possible _combinations_ of k + 1 advertisers that participate.
        self.participating_advs = [i for i in itertools.combinations(range(self.n), self.k + 1)]
        self.no_of_slates = len(self.participating_advs)

        # Consider every possible slate for each user and record associated information.
        # self.slate_metrics = {j: {slate_idx: {} for slate_idx in range(self.no_of_slates)} for j in range(self.m)}
        self.slate_metrics = {j: {} for j in range(self.m)}
        self.calc_metrics_for_each_slate()
        self.add_slates_that_allow_housing_adv_to_over_under_bid()
        # self.adv_to_user_slate_map = self.map_advertisers_to_user_slates()

    def gen_budgets(self):
        # TODO: Placeholder values here.
        return [100 for _ in range(self.n)]

    def gen_bid_landscape(self, matrix_bids):
        """
        # TODO: Placeholder values for now.
        Ideally this is where the magic happens.
        We draw values from a specified distribution.
        Possibly different for different advertisers.
        One advertiser could have a higher value (for all demographic groups or for specific demographic groups).

        ASSUMPTION 1: Advertisers bid their value.
        ASSUMPTION 2 (POSITION DISCOUNT d): We generate an n x m matrix where v_{ij} is the i-th advertiser's value
        for the j-th slot. Then we multiply position discount to get slot-specific value.

        NOTE 1: This should be fairly high since d^k --> 0 as k gets large in which case the final few slots are free.
        NOTE 2: This would make lower slots very cheap.
        """
        # We are going to assume the first {{no_of_housing_adv}} are housing and the rest are non-housing.
        if matrix_bids is None:
            matrix_bids = []
            for i in range(self.n):
                # TODO: What is the restriction on housing advertisers - is their bidding distribution required to be
                #  the same? Or is their bid required to be the same? ~ No way can it be bid.
                if i < self.no_of_housing_adv:
                    # lognormal(mean=-0.5493, sigma=0.8326)
                    matrix_bids.append([uniform(low=0, high=1) for _ in range(self.m)])
                else:
                    # lognormal(mean=-0.3466, sigma=0.8326)
                    matrix_bids.append([uniform(low=0.25, high=1) for _ in range(self.m)])
            matrix_bids = np.array(matrix_bids)
        return matrix_bids

    def gen_quality_score(self):
        # TODO: Below we have implemented quality_score = 0.01 for everyone.
        #  We also considered picking it u.a.r. but that introduces noise that may complicate the initial findings.
        matrix_qs = np.ones((self.n, self.m)) * self.gamma
        # matrix_qs = [np.random.uniform(size=(self.m, )) for _ in range(self.n)]
        # matrix_qs = np.array(matrix_qs)
        return matrix_qs

    def gen_estimated_action_rate(self):
        # TODO: Placeholder values used.
        return np.ones((self.n, self.m))

    def order_advertisers_in_slate(self, set_of_advs, user_idx):
        _scores = [(self.matrix_scores[i][user_idx], i) for i in set_of_advs]
        ordered_slate = sorted(_scores, reverse=True)
        ordered_slate = [i[1] for i in ordered_slate]
        return ordered_slate

    def calc_payment_for_kth_slot(self, winner_idx, runner_up_idx, user_idx, slot_idx):
        """
        Payment = Bid winner needed to make to have the same score as the runner up.
        """
        _ear = self.matrix_ear[winner_idx][user_idx]
        _qs = self.matrix_qs[winner_idx][user_idx]
        score_of_runner_up = self.matrix_scores[runner_up_idx][user_idx]
        payment = (1 / _ear) * (score_of_runner_up - _qs)
        payment = (self.position_discount ** slot_idx) * payment
        return payment

    def calc_metrics_for_each_slate(self):
        """
        Each user has k slots which together are referred to as a slate. Any number of advertisers may participate in
        the auction but only the first k advertisers receive a slot. We need the (k + 1)st advertiser to determine the
        price of the k-th advertiser.

        While more than k + 1 advertisers may take part in an auction, We only care about the first k + 1
        advertisers so we only consider combinations of k + 1 advertisers. As long as we consider all such combinations,
        we cover all cases.

        TODO: Going forward, we may first want to filter advertisers based on targeting criteria.
        TODO: We have made the simplifying assumption that all k slots are filled for each user. This may not be true.
        """
        # Since scores are user-dependent, the slates may be ordered differently for different users.
        slate_idx = 0
        for user_idx in range(self.m):
            for set_of_advs in self.participating_advs:
                # Given a set of participating advertisers, calculate and save the "base slate", i.e., advertisers
                # are sorted in descending order of score.
                ordered_slate = self.order_advertisers_in_slate(set_of_advs, user_idx)
                self.slate_metrics[user_idx][slate_idx] = {}
                self.slate_metrics[user_idx][slate_idx]['ordered_slate'] = ordered_slate

                # Adv price is the true price of the slot, given the set of participating advertisers.
                _adv_price = [self.calc_payment_for_kth_slot(
                    winner_idx=ordered_slate[slot_idx],
                    runner_up_idx=ordered_slate[slot_idx + 1],
                    user_idx=user_idx,
                    slot_idx=slot_idx
                ) for slot_idx in range(self.k)]

                # Save this slate.
                slate_idx = self.store_slate_related_info(ordered_slate, user_idx, slate_idx, _adv_price)

                # Give housing advertisers a chance to over-/under-bid.

    def store_slate_related_info(self, ordered_slate, user_idx, slate_idx, _adv_price):
        # Map winning advertisers to price paid and their utility.
        _price_paid = {ordered_slate[slot_idx]: _adv_price[slot_idx] for slot_idx in range(self.k)}
        # TODO: Verify!
        _utility = {}
        for adv_idx in ordered_slate[:self.k]:
            _util = self.matrix_bids[adv_idx][user_idx] - _price_paid[adv_idx]
            # TODO: Discuss if we want to prevent this. If non-housing has negative utility then we do not allow this
            #  combination.
            # if adv_idx in self.non_housing_adv and _util < 0:
            #     return slate_idx
            _utility[adv_idx] = _util

        # Total quality score if this slot is chosen.
        _qs = [self.matrix_qs[adv][user_idx] * (self.position_discount ** idx)
               for idx, adv in enumerate(ordered_slate)]

        # Save price paid, total revenue, and total quality score.

        self.slate_metrics[user_idx][slate_idx]['price'] = _price_paid
        self.slate_metrics[user_idx][slate_idx]['utility'] = _utility
        self.slate_metrics[user_idx][slate_idx]['revenue'] = sum(_adv_price)
        self.slate_metrics[user_idx][slate_idx]['quality_score'] = sum(_qs)
        slate_idx += 1

        return slate_idx

    def add_slates_that_allow_housing_adv_to_over_under_bid(self):
        """
        TODO:
        1. Note that over- and under-bidding is separate!
            1. In overbidding, the only new slates to add are swapping the non-housing adv in the kth position with
               a housing advertiser and accounting for the payment.
            2. In contrast, allows under-bidding allows the housing advertiser to swap multiple positions. So if it
               is in position p < k then we need to move it down to p + 1, p + 2, ..., k, k + 1. We also need to work
               out what everyone pays.
       2. We need to ensure self.no_of_slates is correctly updated.
       """
        pass

    def map_advertisers_to_user_slates(self):
        """
        Recall that since scores are user-dependent, the slates may be ordered differently for different users.
        We want to map each advertiser to the user-slates they are part of.
        We will then use to calculate x_ij = \sum_S \pi_{Sj}
        """
        # TODO: We should add advertiser's utility here for each slate.
        adv_to_user_slate_map = {i: {j: [] for j in range(self.m)} for i in range(self.n)}
        for user_idx in range(self.m):
            for slate_idx, set_of_advs in enumerate(self.participating_advs):
                ordered_slate = self.slate_metrics[user_idx][slate_idx]['ordered_slate']
                for i in ordered_slate[:self.k]:
                    adv_to_user_slate_map[i][user_idx].append(slate_idx)
        return adv_to_user_slate_map

    def assign_demographic_groups(self):
        """
        TODO: We have made a simplifying assumption that all housing advertisers take part in all
        auctions. This may not be true. A weaker assumption that at least one housing advertiser
        takes part in each auction is probably okay. This is because we can assume we filtered out
        auctions where this does not hold. The only impact of this filtering is that the available
        budget of non-housing advertisers may be lower. We can assume that those auctions occurred
        before our auctions and we subtracted the necessary amount. This may impact the pacing
        multiplier but is probably okay to ignore this until later in the project.
        """

        # Get each combination of protected attributes (e.g. Female-White, Female-Black, etc.)
        subgroups_by_char = [constants.GROUPS_TO_SUBGROUPS[char] for char in self.protected_characteristics]
        subgroup_cross_product = [i for i in itertools.product(*subgroups_by_char)]
        
        # Pick each combination based on their combined frequency. ~ Not sure if we want to change this to a sampling
        # approach. Not sure what value this adds.
        users_demographics = []
        for subgroup in subgroup_cross_product:
            freq = np.prod([constants.SUBGROUP_FREQUENCY[i] for i in subgroup])
            _user = {char: subgroup[idx] for idx, char in enumerate(self.protected_characteristics)}
            users_demographics += ([_user] * math.ceil(freq * self.m))
        
        # Shuffle order of demographics and ensure demographics for only m users. ~ Shuffling is probably not necessary.
        random.shuffle(users_demographics)
        # TODO: Generalize.
        assert len(users_demographics) == self.m, 'We are directly using the true demographic frequency to encode ' \
                                                  'the TVD constraint. So for now, we require m to be an integer ' \
                                                  'multiple of the number of subgroups.'
        users_demographics = users_demographics[:self.m]

        # Create map of {subgroup: user indices with this subgroup}
        subgroup_user_idx_map = {i: [] for i in self.subgroups}
        for user_idx, user in enumerate(users_demographics):
            for char in self.protected_characteristics:
                subgroup_user_idx_map[user[char]].append(user_idx)

        return users_demographics, subgroup_user_idx_map

    def compare_lp_solution_to_independent_auctions(self, lp_allocation, decimals=2):
        # Run each auction independently and see who wins each auction.
        slates_chosen_by_ind_auctions = []
        for ad_auction in self.matrix_scores.T:
            _winner = sorted([(score, adv_idx) for adv_idx, score in enumerate(ad_auction)], reverse=True)[:self.k + 1]
            _winner = [adv[1] for adv in _winner]
            slates_chosen_by_ind_auctions.append(_winner)

        # See which slates were chosen by the LP.
        slates_chosen_by_lp = [self.slate_metrics[j][s]['ordered_slate'] for j in range(self.m) for s in
                               range(self.no_of_slates) if lp_allocation[j, s].value() == 1]

        # We want to see how much everyone paid.
        ind_auctions = {i: 0 for i in range(self.n)}
        lp_payment = {i: 0 for i in range(self.n)}
        for j in range(self.m):
            for s in range(self.no_of_slates):
                _slate = self.slate_metrics[j][s]['ordered_slate']
                if _slate == slates_chosen_by_lp[j]:
                    for i in _slate[:self.k]:
                        lp_payment[i] += self.slate_metrics[j][s]['price'][i]

                if _slate == slates_chosen_by_ind_auctions[j]:
                    for i in _slate[:self.k]:
                        ind_auctions[i] += self.slate_metrics[j][s]['price'][i]

        # For viewing purposes, round prices.
        ind_auctions = {k: round(v, decimals) for k, v in ind_auctions.items()}
        lp_payment = {k: round(v, decimals) for k, v in lp_payment.items()}

        # For each slate, only show the winners.
        slates_chosen_by_ind_auctions = [i[:self.k] for i in slates_chosen_by_ind_auctions]
        slates_chosen_by_lp = [i[:self.k] for i in slates_chosen_by_lp]

        return slates_chosen_by_ind_auctions, slates_chosen_by_lp, ind_auctions, lp_payment


class VrsLp:
    def __init__(self, vrs_lp_data, objective_fn='revenue', add_compliance_req=False):
        self.vrs_lp_data = vrs_lp_data
        self.objective_fn = objective_fn
        self.add_compliance_req = add_compliance_req

        # Initialize LP
        self.lp = pulp.LpProblem(objective_fn, pulp.LpMaximize)

        # Initialize variables
        self.matrix_pi = None
        self.matrix_x = None
        self.matrix_s = None
        self.matrix_y = None
        self.matrix_z = None
        self.slates_chosen_by_lp = None

    def add_variables(self):
        # \Pi_{Sj} = 1 if slate S is shown to user j and 0 otherwise.
        self.matrix_pi = pulp.LpVariable.dicts("Pi", ((j, s)
                                                      for j in range(self.vrs_lp_data.m)
                                                      for s in range(self.vrs_lp_data.no_of_slates)),
                                               cat='Binary')

        # X_{ij} = 1 if adv i showed ad to user j and 0 otherwise.
        self.matrix_x = pulp.LpVariable.dicts("X", ((i, j)
                                                    for i in range(self.vrs_lp_data.n)
                                                    for j in range(self.vrs_lp_data.m)))

        if self.add_compliance_req:
            # S_h is the total number of slots assigned to housing advertiser h.
            self.matrix_s = pulp.LpVariable.dicts("S", (h for h in range(self.vrs_lp_data.no_of_housing_adv)))

            # Y_A^{(h)} is 1 if the housing advertiser is compliant w.r.t. protected characteristic A.
            self.matrix_y = pulp.LpVariable.dicts("Y",
                                                  ((h, A) for h in range(self.vrs_lp_data.no_of_housing_adv)
                                                   for A in range(len(self.vrs_lp_data.protected_characteristics))),
                                                  cat='Binary')

            # Z_a^{(h)} is the TVD b/w target and actual audience for subgroup a for housing advertiser h.
            self.matrix_z = pulp.LpVariable.dicts("Z", ((h, a) 
                                                        for h in range(self.vrs_lp_data.no_of_housing_adv) 
                                                        for a in range(len(self.vrs_lp_data.subgroups))))

    def add_objective(self):
        total_revenue = pulp.lpSum(self.matrix_pi[j, s] * self.vrs_lp_data.slate_metrics[j][s][self.objective_fn]
                                   for j in range(self.vrs_lp_data.m)
                                   for s in range(self.vrs_lp_data.no_of_slates))
        self.lp += total_revenue

    def add_constraints(self):
        self.constraint_only_1_slate_per_user()
        self.constraint_total_quality_score_at_least_gamma()
        self.constraint_define_x_ij_in_terms_of_pi_j_s()
        self.constraint_add_budget()
        if self.add_compliance_req:
            self.constraint_compliance_requirements()

    def solve(self):
        self.add_variables()
        self.add_objective()
        self.add_constraints()
        self.lp.solve(pulp.PULP_CBC_CMD(msg=1))
        if self.add_compliance_req:
            self.slates_chosen_by_lp = self._get_slates_chosen_by_lp()
            self.verify_compliance_requirements_are_met()

    def constraint_only_1_slate_per_user(self):
        for j in range(self.vrs_lp_data.m):
            self.lp += pulp.lpSum(self.matrix_pi[j, s] for s in range(self.vrs_lp_data.no_of_slates)) == 1

    def constraint_total_quality_score_at_least_gamma(self):
        _qs = pulp.lpSum(self.matrix_pi[j, s] * self.vrs_lp_data.slate_metrics[j][s]['quality_score']
                         for j in range(self.vrs_lp_data.m)
                         for s in range(self.vrs_lp_data.no_of_slates))
        self.lp += self.vrs_lp_data.gamma <= _qs

    def constraint_define_x_ij_in_terms_of_pi_j_s(self):
        # Define x_{ij} = 1 if adv i showed ad to user j and 0 otherwise.
        for i in range(self.vrs_lp_data.n):
            for j in range(self.vrs_lp_data.m):
                _x_ij = pulp.lpSum(self.matrix_pi[j, s] for s in self.vrs_lp_data.adv_to_user_slate_map[i][j])
                self.lp += self.matrix_x[i, j] == _x_ij

    def constraint_add_budget(self):
        for i in range(self.vrs_lp_data.n):
            _budget = pulp.lpSum(self.matrix_pi[j, s] * self.vrs_lp_data.slate_metrics[j][s]['price'][i]
                                 for j in range(self.vrs_lp_data.m)
                                 for s in self.vrs_lp_data.adv_to_user_slate_map[i][j])
            self.lp += self.vrs_lp_data.budget_vector[i] >= _budget

    def constraint_compliance_requirements(self):
        # S_h is the total number of slots assigned to housing advertiser h.
        self._constraint_define_s_h_in_terms_of_x_hj()

        for char_idx, char in enumerate(self.vrs_lp_data.protected_characteristics):
            self._constraint_ensure_alpha_compliance(char_idx)

            for h in range(self.vrs_lp_data.no_of_housing_adv):
                _tvd = 0
                for subgroup in constants.GROUPS_TO_SUBGROUPS[char]:
                    # Index of subgroup
                    a = self.vrs_lp_data.subgroups.index(subgroup)

                    # Add constraints to ensure Z[h, a] is abs distance b/w target and actual audience for subgroup a.
                    self._constraint_find_abs_dist_for_subgroup_a(subgroup, h, a)

                    # Add each Z[h, a] for y_h-related constraint.
                    _tvd += self.matrix_z[h, a]

                # Add constraint: y_h = 1 if TVD w.r.t protected characteristic < \beta
                self.lp += _tvd <= (2 * self.vrs_lp_data.beta) + (self.vrs_lp_data.M * (1 - self.matrix_y[h, char_idx]))

    def _constraint_define_s_h_in_terms_of_x_hj(self):
        for h in range(self.vrs_lp_data.no_of_housing_adv):
            self.lp += self.matrix_s[h] == pulp.lpSum(self.matrix_x[h, j] for j in range(self.vrs_lp_data.m))

    def _constraint_ensure_alpha_compliance(self, char_idx):
        # TODO: We are assuming the compliance fraction is the same across characteristics. This is not true.
        # Interesting to ask what is the impact of this.
        _compliant_fraction = (1 - self.vrs_lp_data.alpha) * self.vrs_lp_data.no_of_housing_adv

        # Ensure that at least (1 - \alpha) fraction of housing advertisers are compliant.
        _compliant_housing_adv = pulp.lpSum(self.matrix_y[h, char_idx]
                                            for h in range(self.vrs_lp_data.no_of_housing_adv))
        self.lp += _compliant_housing_adv >= _compliant_fraction

    def _constraint_find_abs_dist_for_subgroup_a(self, subgroup, h, a):
        # Z_a^{(h)} is the TVD b/w target and actual audience for subgroup a for housing advertiser h.
        _fraction_of_target_aud = constants.SUBGROUP_FREQUENCY[subgroup] * self.matrix_s[h]
        _fraction_of_actual_aud = pulp.lpSum(self.matrix_x[h, a]
                                             for a in self.vrs_lp_data.subgroup_user_idx_map[subgroup])
        _dist_for_a = _fraction_of_actual_aud - _fraction_of_target_aud
        self.lp += self.matrix_z[h, a] >= _dist_for_a
        self.lp += self.matrix_z[h, a] >= _dist_for_a

    def _get_slates_chosen_by_lp(self):
        return [self.vrs_lp_data.slate_metrics[j][s]['ordered_slate']
                for j in range(self.vrs_lp_data.m)
                for s in range(self.vrs_lp_data.no_of_slates)
                if self.matrix_pi[j, s].value() == 1]

    def verify_compliance_requirements_are_met(self):
        # Check for compliance.

        _compliant_fraction = (1 - self.vrs_lp_data.alpha) * self.vrs_lp_data.no_of_housing_adv
        no_of_compliant_advertisers = 0
        for h in range(self.vrs_lp_data.no_of_housing_adv):
            # print('-' * 90)
            # print(f'Housing advertiser {h}')
            # print('-' * 90)

            # Check S[h].
            _total_slots = len([slate for slate in self.slates_chosen_by_lp if h in slate])
            assert self.matrix_s[h].value() == _total_slots, 'Total #slot for h is wrong!'
            if self.matrix_s[h].value() == 0:
                # print('No slots assigned to this advertiser.')
                continue

            for char_idx, char in enumerate(self.vrs_lp_data.protected_characteristics):
                # Get ad slot count by subgroup - needed to check Z[h, a], and Y[h, A]
                subgroup_count = {subgroup: 0 for subgroup in constants.GROUPS_TO_SUBGROUPS[char]}
                for user_idx, slate in enumerate(self.slates_chosen_by_lp):
                    if h in slate:
                        subgroup_count[self.vrs_lp_data.users_demographics[user_idx][char]] += 1

                # Check Z[h, a]
                for subgroup in constants.GROUPS_TO_SUBGROUPS[char]:
                    a = self.vrs_lp_data.subgroups.index(subgroup)
                    _fraction_of_target_aud = constants.SUBGROUP_FREQUENCY[subgroup] * _total_slots
                    _true_z_ha = abs(subgroup_count[subgroup] - _fraction_of_target_aud)
                    # print(f'h = {h}, subgroup = {subgroup}, True = {_true_z_ha}, LP = {Z[h, a].value()}')
                    assert _true_z_ha == self.matrix_z[h, a].value(), f'Z[h = {h}, subgroup = {subgroup}] is incorrect!'

                # Check Y[h, A]
                _target = [constants.SUBGROUP_FREQUENCY[key] for key in constants.GROUPS_TO_SUBGROUPS[char]]
                _actual = utilities.convert_count_dict_to_list_of_perc(subgroup_count, multiply_by=1)
                _true_tvd = utilities.calc_total_variation_distance(_target, _actual, normalize=False)
                _true_y_hA = 1 if _true_tvd <= self.vrs_lp_data.beta else 0
                # print(f'h = {h}, char = {char}, True TVD = {_true_tvd}, True = {_true_y_hA}, '
                #       f'LP = {self.matrix_y[h, char_idx].value()}')

                # The LP incorrectly labels y_hA when it doesn't matter.
                if no_of_compliant_advertisers < _compliant_fraction:
                    assert _true_y_hA == self.matrix_y[h, char_idx].value(), f'Y[h = {h}, char = {char}] is incorrect!'
                else:
                    if _true_y_hA != self.matrix_y[h, char_idx].value():
                        pass
                        # print(f'WARNING: LP incorrectly labeled Y[h = {h}, char = {char}]. '
                        #       f'Not required to meet compliance requirements.')

                no_of_compliant_advertisers += _true_y_hA

                # Is compliance met for protected characteristic {{char}}.
                assert sum([self.matrix_y[h, char_idx].value() for h in range(
                    self.vrs_lp_data.no_of_housing_adv)]) >= _compliant_fraction, 'Compliance requirement is not met!'
