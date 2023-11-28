import numpy as np
import random

# Constants for the environment
# TODO: We need to generalize this! So it's not based on race.
RACES = ["white", "black", "other"]
TARGET_DISTRIBUTION = {"white": 0.6, "black": 0.3, "other": 0.1}
WEIGHTS = [v for v in TARGET_DISTRIBUTION.values()]
NUM_AUCTIONS = 1000  # Total number of auctions
BUDGET = 1000        # Total budget
VALUE_PER_USER = 10  # v_j value


class Environment:
    def __init__(self):
        self.budget = BUDGET
        self.lambdas = [1, 1, 1]
        self.statuses = [0, 0, 0]
        self.num_auctions = NUM_AUCTIONS
        self.distribution = {race: 0 for race in RACES}
        self.total_ads_shown = 0

        self.state_to_int = {}
        self.int_to_state = {}
        self.next_state_index = 0

    def get_state_index(self, state_dict):
        # Convert state dictionary to a unique integer
        state_tuple = tuple(state_dict.items())  # Convert dictionary to a tuple for hashing
        if state_tuple not in self.state_to_int:
            self.state_to_int[state_tuple] = self.next_state_index
            self.int_to_state[self.next_state_index] = state_dict
            self.next_state_index += 1
        return self.state_to_int[state_tuple]

    def get_state_dict(self, state_index):
        # Convert integer back to state dictionary
        return self.int_to_state[state_index]

    def step(self, action):
        # Interpret the action to update lambda values
        race_index = action // 3  # Determine which race the action is for
        action_type = action % 3  # Determine the type of action (0: increase, 1: decrease, 2: do nothing)

        if action_type == 0:
            self.lambdas[race_index] += 0.1
        elif action_type == 1:
            self.lambdas[race_index] = max(0, self.lambdas[race_index] - 0.1)

        # Simulate the arrival of a user
        # TODO: We need to remove this. Users and bid profile should be the same.
        demographic = random.choices(RACES, weights=WEIGHTS)[0]  # Choose a demographic based on the distribution
        # TODO: Need to find user_race
        bid = VALUE_PER_USER * self.lambdas[race_index]  # Calculate the bid

        # Check if the advertiser wins the auction (simplified for this example)
        # TODO: Implement whether the user won the auction or not.
        win = random.random() < 0.5  # 50% chance of winning, can be adjusted
        self.total_ads_shown += 1

        # Update budget and distribution if the auction is won
        # TODO: With the small bid assumption, if bids << budget, we don't usually bother with self.budget >= bid.
        if win and self.budget >= bid:
            # TODO: update payment.
            self.budget -= bid
            self.distribution[demographic] += 1
            # TODO: Change reward so it is minus 1 if demographic is underserved. Also, we need to ensure do nothing is
            #  properly rewarded.
            reward = 1  # Reward for winning the auction
        else:
            reward = 0  # No reward if the auction is lost or not enough budget

        # Check if the budget is exhausted or all users have arrived.
        done = self.budget <= 0 or self.total_ads_shown >= self.num_auctions

        return demographic, reward, done

    def reset(self):
        # TODO: Don't like repetition of code with init.
        # to just use a new environment.
        self.budget = BUDGET
        self.lambdas = [1, 1, 1]
        self.statuses = [0, 0, 0]
        self.distribution = {race: 0 for race in RACES}
        self.total_ads_shown = 0

    def calculate_dist_bw_target_and_actual_audience(self):
        # Calculate the total variational distance between actual and target distributions
        # TODO (1/2): Use utilities version of TVD.
        # TODO (2/2): Add option to make target distribution online.
        total_population = sum(self.distribution.values())
        _dist = sum(abs((self.distribution[race] / total_population) - TARGET_DISTRIBUTION[race]) for race in RACES) / 2
        return _dist

    def check_alpha_constraint(self, alpha):
        # Check if the total variation distance exceeds alpha
        total_variation_distance = self.calculate_dist_bw_target_and_actual_audience()
        return total_variation_distance > alpha


class QLearningAgent:
    # TODO: Implement functions to encode and decode states
    def __init__(self, num_of_states, num_of_actions, learning_rate=0.1, discount_factor=0.9, epsilon=0.1):
        self.num_of_actions = num_of_actions  # 2 actions (increase, decrease) for each of the 3 races
        self.q_table = np.zeros((num_of_states, self.num_of_actions))  # Initialize the Q-table
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon

    def choose_action(self, state):
        # Epsilon-greedy policy for action selection
        if random.uniform(0, 1) < self.epsilon:
            return random.randint(0, self.num_of_actions - 1)  # Random action
        else:
            # TODO: Only some actions are allowed based on the race so we need to edit the argmax.
            return np.argmax(self.q_table[state])  # Best action based on Q-table

    def update_q_table(self, state, action, reward, next_state):
        # Update the Q-table using the Q-learning update rule
        best_next_action = np.argmax(self.q_table[next_state])
        td_target = reward + self.discount_factor * self.q_table[next_state][best_next_action]
        td_error = td_target - self.q_table[state][action]
        self.q_table[state][action] += self.learning_rate * td_error


def run_q_learning(episodes=100, num_of_subgroups=3):
    env = Environment()

    # TODO: Should be more general? I think the max value of lambda is lambda = budget/min_j v_j.
    # One state for each combination of sign and lambda value
    num_of_states = num_of_subgroups * int(BUDGET / VALUE_PER_USER / 0.1)
    num_of_actions = num_of_subgroups * 3
    agent = QLearningAgent(
        num_of_states=num_of_states,
        num_of_actions=num_of_actions
    )

    for episode in range(episodes):
        env.reset()
        state = None
        done = False

        while not done:
            action = agent.choose_action(state)                      # Select an action
            next_state, reward, done = env.step(action)              # Take the action in the environment
            agent.update_q_table(state, action, reward, next_state)  # Update Q-table
            state = next_state                                       # Move to the next state

    # TODO: We need to possibly start with higher epsilon and then decrease it. Similarly, we need to reduce alpha.



if __name__ == "__main__":
    run_q_learning()
