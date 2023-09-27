import utilities


class Auction:
    """
    We are going to follow the AdWord model. At every step, a user with certain characteristics appears. We then
    hold an auction for this ad slot.
    """
    def __init__(self, advertiser_list, user, normalize_bid=False, auction_type='first',
                 voting_rule_logic='AND-inclusive'):
        self.advertiser_list = self.get_relevant_advertisers(advertiser_list)
        self.user = user
        self.normalize_bid = normalize_bid
        self.auction_type = auction_type
        self.voting_rule_logic = voting_rule_logic

    @staticmethod
    def get_relevant_advertisers(advertiser_list):
        # TODO: We may want to use only a subset of advertisers from all possible advertisers?
        return advertiser_list

    @staticmethod
    def calc_est_action_rate(advertiser):
        # TODO: Implement.
        return advertiser.est_action_rate

    @staticmethod
    def calc_quality_score(advertiser):
        # TODO: Implement.
        return advertiser.quality_score

    def calc_bid_for_each_advertiser(self, advertiser, true_bid=None, vrs_over_bid=None, vrs_under_bid=None):
        # Calculated by the platform but dependent on advertiser inputs (e.g. budget).
        if true_bid is None:
            true_bid = advertiser.calc_user_based_bid(self.user)

        if vrs_over_bid is not None:
            true_bid = max(true_bid, vrs_over_bid)
        elif vrs_under_bid is not None:
            true_bid = min(true_bid, vrs_under_bid)

        # Calculated by the platform.
        quality_bid = self.calc_quality_score(advertiser)
        est_action_rate = self.calc_est_action_rate(advertiser)

        advertiser_component = est_action_rate * true_bid
        total_score = advertiser_component + quality_bid

        # We pick winners based on the normalized bid and charge the winner their true bid.
        return advertiser.index, total_score, true_bid

    @staticmethod
    def allocation_rule(adv_score_in_des_order):
        """
        Return advertiser with the largest total score.
        """
        return adv_score_in_des_order[0][0]

    def payment_rule(self, adv_score_in_des_order):
        # TODO: Ideally, we would want to pass the payment rule as a function.
        if self.auction_type == 'first':
            return self.first_price_auction(adv_score_in_des_order)
        elif self.auction_type == 'second':
            return self.second_price_auction(adv_score_in_des_order)
        elif self.auction_type == 'vcg':
            return self.vcg_auction(adv_score_in_des_order)
        elif self.auction_type == 'critical_bid':
            _winning_adv_idx = adv_score_in_des_order[0][0]
            _winning_adv = self.advertiser_list[_winning_adv_idx]

            return self.pay_critical_bid(
                adv_score_in_des_order=adv_score_in_des_order,
                quality_score=_winning_adv.quality_score,
                est_action_rate=_winning_adv.est_action_rate,
            )
        else:
            raise utilities.CustomError("Only, first, vcg, and critical_bid are supported. Please specify a supported "
                                        "auction.")

    @staticmethod
    def first_price_auction(adv_score_in_des_order):
        """
        Winner pays their true bid.
        """
        return adv_score_in_des_order[0][2]

    @staticmethod
    def second_price_auction(adv_score_in_des_order):
        """
        Winner pays bid of advertiser with second-highest score.
        """
        return adv_score_in_des_order[1][2]

    @staticmethod
    def vcg_auction(adv_score_in_des_order):
        """
        The winner pays the difference in total score b/w advertiser with highest and second highest total score.
        """
        highest_score = adv_score_in_des_order[0][1]
        second_highest_score = adv_score_in_des_order[1][1]
        _diff = highest_score - second_highest_score

        # Tests.
        assert _diff >= 0, 'Difference in score is negative. Check!'
        _winners_true_bid = adv_score_in_des_order[0][2]
        assert _diff <= _winners_true_bid, 'Winner pays more than their value. Check!'

        return _diff

    @staticmethod
    def pay_critical_bid(adv_score_in_des_order, quality_score, est_action_rate, vrs_multiplier=1):
        """
        We find the minimum bid the winning advertiser would have to make to have the second highest total score
        """
        # Get second highest total score.
        second_highest_score = adv_score_in_des_order[1][1]

        # Remove quality score component.
        _min_bid = second_highest_score - quality_score

        # Divide out estimated action rate component.
        _min_bid = _min_bid / est_action_rate

        # Divide out VRS multiplier component.
        _min_bid = _min_bid / vrs_multiplier

        return _min_bid

    def use_vrs_to_adjust_advertisers_bids(self, bid_list, vrs_over_bid, vrs_under_bid):
        """
        We iterate over the bid list. For each advertiser who is both: (a) from a protected domain AND (b) {under, over}
        served the demographic to which this user belongs, we set the the advertiser's bid to vrs_adj_bid.

        vrs_adj_bid can be higher or lower depending on what needs to be achieved.

        # TODO: If we want to move this to vrs.py, we would need to move calc_bid_for_each_advertiser as a method of
        the Advertiser class.
        """
        vrs_bid_list = bid_list[:]
        for idx, bid_tuple in enumerate(vrs_bid_list):
            _, _, true_bid = bid_tuple
            _adv = self.advertiser_list[idx]
            if _adv.protected_domain:
                _over_under_served = _adv.is_demographic_under_or_over_served(user=self.user,
                                                                              voting_rule_logic=self.voting_rule_logic)
                if _over_under_served == 'under':
                    vrs_bid_list[idx] = self.calc_bid_for_each_advertiser(_adv, true_bid=true_bid,
                                                                          vrs_over_bid=vrs_over_bid)
                elif _over_under_served == 'over' and vrs_under_bid is not None:
                    vrs_bid_list[idx] = self.calc_bid_for_each_advertiser(_adv, true_bid=true_bid,
                                                                          vrs_under_bid=vrs_under_bid)
        return vrs_bid_list

    def run_auction(self, bid_list):
        adv_score_in_des_order = sorted(bid_list, key=lambda x: x[1], reverse=True)
        winner_idx = self.allocation_rule(adv_score_in_des_order)
        price_paid = self.payment_rule(adv_score_in_des_order)

        total_score = bid_list[winner_idx][1]
        true_bid = bid_list[winner_idx][2]
        return {
            'idx': winner_idx,
            'total_score': total_score,
            'true_bid': true_bid,
            'price_paid': price_paid,
            'protected_domain': self.advertiser_list[winner_idx].protected_domain
        }

    def run(self, bid_list=None, apply_vrs=False, vrs_over_bid=None, vrs_under_bid=None):
        if bid_list is None:
            bid_list = [self.calc_bid_for_each_advertiser(a) for a in self.advertiser_list]
        if apply_vrs:
            bid_list = self.use_vrs_to_adjust_advertisers_bids(
                bid_list=bid_list,
                vrs_over_bid=vrs_over_bid,
                vrs_under_bid=vrs_under_bid
            )

        winner = self.run_auction(bid_list)

        return winner, bid_list
