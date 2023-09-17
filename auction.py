import random

import constants
import utilities


class Auction:
    """
    We are going to follow the AdWord model. At every step, a user with certain characteristics appears. We then
    hold an auction for this ad slot.
    """
    def __init__(self, advertiser_list, user, normalize_bid=False, auction_type='first'):
        self.advertiser_list = self.get_relevant_advertisers(advertiser_list)
        self.user = user
        self.normalize_bid = normalize_bid
        self.auction_type = auction_type

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

    def calc_bid_for_each_advertiser(self, advertiser):
        # Calculated by the platform but dependent on advertiser inputs (e.g. budget).
        true_bid = advertiser.calc_user_based_bid(self.user)

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

    def run(self):
        bid_list = [self.calc_bid_for_each_advertiser(a) for a in self.advertiser_list]
        adv_score_in_des_order = sorted(bid_list, key=lambda x: x[1], reverse=True)
        winner_idx = self.allocation_rule(adv_score_in_des_order)
        price_paid = self.payment_rule(adv_score_in_des_order)

        total_score = bid_list[winner_idx][1]
        true_bid = bid_list[winner_idx][2]
        winner = {
            'idx': winner_idx,
            'total_score': total_score,
            'true_bid': true_bid,
            'price_paid': price_paid,
        }

        return winner, bid_list
