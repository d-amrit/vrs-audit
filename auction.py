import random

import constants


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
        """
        # TODO: Implement.
        This is going to be used in the auction calculation.
        """
        return 1

    @staticmethod
    def calc_quality_bid(advertiser):
        """
        # TODO: Implement.
        This is going to be used in the auction calculation.
        """
        return 0

    def calc_bid_for_each_advertiser(self, advertiser):
        # Calculated by the platform but dependent on advertiser inputs (e.g. budget).
        true_bid, vrs_multiplier = advertiser.calc_bid(self.user)

        # Calculated by the platform.
        quality_bid = self.calc_quality_bid(advertiser)
        est_action_rate = self.calc_est_action_rate(advertiser)

        advertiser_component = est_action_rate * true_bid
        adjusted_bid = advertiser_component + quality_bid

        # We pick winners based on the normalized bid and charge the winner their true bid.
        return adjusted_bid, true_bid, vrs_multiplier

    def compare_bid_to_current_highest_price_and_bid(self, idx, adj_bid, true_bid, winner_dict):
        _current_highest_bid = winner_dict['adj_bid']

        # If first-price auction then you pay your true bid.
        if self.auction_type == 'first':
            _price_paid = true_bid
        # Else if this is a second-price auction, then you pay the second highest true bid.
        else:
            _price_paid = winner_dict['true_bid']

        # If new bid is greater than prior highest bid then
        if adj_bid > _current_highest_bid:
            winner_dict = {
                'idx': idx,                  # Index of advertiser with largest bid so far, bid
                'adj_bid': adj_bid,          # Adjusted bid score (estimated action rate, quality score, VRS, etc.)
                'true_bid': true_bid,        # True bid.
                'price_paid': _price_paid,   # Price advertiser pays.
            }

        # For second-price auction, new bid is smaller than current highest bid but higher than the second highest
        # bidder than adjust price paid by the winner.
        elif self.auction_type == 'second' and _price_paid > winner_dict['price_paid']:
            winner_dict['price_paid'] = _price_paid

        return winner_dict

    def find_winning_bid_and_price_they_pay(self, bid_list):
        """
        Comment: This is possibly an inefficient implementation but it iterates over the list once and collects all the
        information we want.

        :param bid_list: Bid with and without VRS applied are indices 0 and 1 respectively.
        :return: Advertiser idx of advertiser with largest bid.
        """

        winner = {'idx': None, 'adj_bid': float('-inf'), 'true_bid': None, 'price_paid': 0}
        for idx, bid_tuple in enumerate(bid_list):
            adjusted_bid, true_bid, _ = bid_tuple

            winner = self.compare_bid_to_current_highest_price_and_bid(
                idx=idx,
                adj_bid=adjusted_bid,
                true_bid=true_bid,
                winner_dict=winner
            )

        return winner

    def find_vrs_winner(self, bid_list, winner):
        """
        if this demographic is underserved:
            w.p. P_TOP:
                return housing advertiser as the winner.
        elif this demographic is over-served:
            w.p. P_BOTTOM:
                Remove housing advertiser from the auction, thereby, ensuring they lose.
                return winner of this modified auction.

        return regular winner.
        """
        assert self.advertiser_list[0].protected_domain, 'First advertiser is not protected. ' \
                                                         'Please ensure first advertiser is protected.'

        vrs_multiplier = bid_list[0][2]
        vrs_random_coin = random.random()
        if vrs_multiplier > 1 and vrs_random_coin <= constants.P_TOP:
            winner = {
                'idx': 0,
                'adj_bid': 'RAISE_ERROR_IF_WE_USE_THIS',
                'true_bid': bid_list[0][1],
                'price_paid': bid_list[0][1]
            }

        elif vrs_multiplier < 1 and vrs_random_coin <= constants.P_BOTTOM:
            winner = self.find_winning_bid_and_price_they_pay(bid_list[1:])

        return winner, vrs_multiplier, vrs_random_coin

    def run(self):
        """
        Runs auction with and without VRS simultaneously. This ensures we certainly use the same bids across our
        experiments. ~ This is not necessary! We could: (a) Save bids and then re-run, (b) Rely on using same
        random state but this removes all doubt.
        """

        # Get bid for each advertiser.
        bid_list = [self.calc_bid_for_each_advertiser(a) for a in self.advertiser_list]

        # Find regular and VRS winner.
        regular_winner = self.find_winning_bid_and_price_they_pay(bid_list)
        vrs_winner, vrs_multiplier, vrs_random_coin = self.find_vrs_winner(bid_list, regular_winner)

        return vrs_winner, regular_winner, bid_list, vrs_multiplier, vrs_random_coin
