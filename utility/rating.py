from openskill.models import PlackettLuce
from utility.globals import RATING_BASE

class MWO_Rating_System:
    def __init__(self, mu=25.0, sigma=25.0/3, beta=25.0/60, tau=25.0/3000):
        """
        Initializes the MWO rating system.

        Args:
            mu (float): The initial average rating for a new player.
            sigma (float): The initial uncertainty in a new player's rating.
            beta (float): The skill difference required to have a high chance of winning.
            tau (float): The rate at which sigma grows over time (not used here but for context).
        """
        self.model = PlackettLuce(mu=mu, sigma=sigma, beta=beta, tau=tau)
        self.model.weight_bounds = None

        self.player_ratings = {}
        self.chassis_stats = {None: {}}
        self.historic_stats_threshold = 10
        self.performance_indicators = ['MatchScore', 'Kills', 'KillsMostDamage', 'Assists', 'ComponentsDestroyed', 'Damage']

        self.processed_matches = 0
        self.correct_predictions = 0
        self.prediction_brackets = {}

    def _get_default_rating(self, player_name):
        """Creates rating object for a pilot."""
        return self.model.rating(name=player_name)

    def _get_player_rating(self, player_name):
        """Retrieves or initializes a player's rating."""
        if player_name not in self.player_ratings:
            self.player_ratings[player_name] = self._get_default_rating(player_name)
        return self.player_ratings[player_name]
    
    def _update_chassis_stats(self, chassis, stats, division = None):
        # if chassis not in self.chassis_stats:
        #     self.chassis_stats[chassis] = {indicator: stats[indicator] for indicator in self.performance_indicators}
        #     self.chassis_stats[chassis]['Uses'] = 1
        # else:
        #     historic_stats = self.chassis_stats[chassis]
        #     uses = historic_stats['Uses']
        #     for indicator in self.performance_indicators:
        #         historic_stats[indicator] = (stats[indicator] + historic_stats[indicator] * uses) / (uses + 1)
        #     historic_stats['Uses'] += 1

        def update(data, stats, chassis):
            if chassis in data:
                historic_stats = data[chassis]
                uses = historic_stats['Uses']
                for indicator in self.performance_indicators:
                    historic_stats[indicator] = (stats[indicator] + historic_stats[indicator] * uses) / (uses + 1)
                historic_stats['Uses'] += 1
            else:
                data[chassis] = {indicator: stats[indicator] for indicator in self.performance_indicators}
                data[chassis]['Uses'] = 1

        if division not in self.chassis_stats:
            self.chassis_stats[division] = {}

        division_data = self.chassis_stats[division]
        update(division_data, stats, chassis)

        if division is not None:
            general_data = self.chassis_stats[None]
            update(general_data, stats, chassis)

    def _performance_index(self, data):
        """Normalizes player stats based on the historical average for their mech."""

        def normalized_division(dividend, divisor):
            if divisor == 0:
                return 1
            
            floor = 0.75
            ceiling = 1.25
            result = dividend / divisor
            return floor if result < floor else ceiling if result > ceiling else result

        # def valid_stats(chassis):
        #     return chassis in self.chassis_stats and self.chassis_stats[chassis]['Uses'] >= self.historic_stats_threshold

        # chassis = data['Chassis']
        # if not valid_stats(chassis):
        #     self._update_chassis_stats(chassis, data)
        #     return 1
        
        # stats = self.chassis_stats[chassis]
        # normalized_stats = [normalized_division(data[indicator], stats[indicator]) for indicator in self.performance_indicators]
        # return sum(normalized_stats) / len(self.performance_indicators)

        def valid_stats(chassis, division):
            if division not in self.chassis_stats:
                self.chassis_stats[division] = {}
            division_data = self.chassis_stats[division]

            return chassis in division_data and division_data[chassis]['Uses'] >= self.historic_stats_threshold

        chassis = data['Chassis']
        division = data['Division']
        if not valid_stats(chassis, division):
            self._update_chassis_stats(chassis, data, division)
            return 1
        
        division_data = self.chassis_stats[division]
        stats = division_data[chassis]
        normalized_stats = [normalized_division(data[indicator], stats[indicator]) for indicator in self.performance_indicators]
        return sum(normalized_stats) / len(self.performance_indicators)

        # return 1
    
    def make_predictions(self, teams, ranks):
        self.processed_matches += 1
        if self.processed_matches < 1000:
            return
        
        bracket = self.processed_matches // 100
        if bracket not in self.prediction_brackets:
            self.prediction_brackets[bracket] = 0
        
        prediction = self.model.predict_win(teams=teams)
        if (prediction[0] > 0.5 and ranks[0] == 0) or (prediction[1] > 0.5 and ranks[1] == 0):
            self.correct_predictions += 1
            self.prediction_brackets[bracket] += 1

    def predict_result(self, teams):
        ratings = [[self._get_player_rating(player_name=player) for player in team] for team in teams]
        return self.model.predict_win(teams=ratings)

    def process_match(self, match_data):
        """
        Processes the results of a single match and updates player ratings.

        Args:
            match_data (list of dicts): A list of player performance dictionaries.
        """
        indexes = {}
        teams_data = {}
        teams_ranks = {}
        for _, side in match_data.groupby('Team'):
            team_id = side['Team'].iloc[0]
            if team_id not in teams_data:
                team_result = side['MatchResult'].iloc[0]
                rank = 0 if team_result == 'WIN' else 1

                teams_ranks[team_id] = rank
                teams_data[team_id] = {'players': [], 'performance': []}

            team = teams_data[team_id]
            for index, row in side.iterrows():
                player = row['Username']
                rating = self._get_player_rating(player_name=player)
                performance = self._performance_index(row)

                team['players'].append(rating)
                team['performance'].append(performance)
                indexes[player] = index

        team_ids = teams_data.keys()
        openskill_teams = [teams_data[team_id]['players'] for team_id in team_ids]
        openskill_ranks = [teams_ranks[team_id] for team_id in team_ids]
        openskill_performance = [teams_data[team_id]['performance'] for team_id in team_ids]
        
        self.make_predictions(openskill_teams, openskill_ranks)

        # Average team ratings
        team1, team2 = openskill_teams
        team1_rating = sum(p.ordinal(target=RATING_BASE) for p in team1) / len(team1)
        team2_rating = sum(p.ordinal(target=RATING_BASE) for p in team2) / len(team2)

        team_rating = {
            0: team1_rating,
            1: team2_rating
        }
        opposing_team_rating = {
            0: team2_rating,
            1: team1_rating
        }

        updated_ratings = self.model.rate(teams=openskill_teams, ranks=openskill_ranks, weights=openskill_performance)
        
        records = {}
        for team_index, team in enumerate(updated_ratings):
            for rating in team:
                self.player_ratings[rating.name] = rating
                index = indexes[rating.name]
                records[index] = {'PilotRating': rating.ordinal(target=RATING_BASE), 'RatingBase': rating.mu, 'RatingUncertainty': rating.sigma,
                                  'OpponentRating': opposing_team_rating[team_index], 'TeamRating': team_rating[team_index]}
        
        return records

    def get_player_info(self, player_name):
        """Returns a player's rating and uncertainty."""
        rating = self._get_player_rating(player_name)
        return {
            'mu': rating.mu,
            'sigma': rating.sigma,
            'confidence_interval': (rating.mu - 2 * rating.sigma, rating.mu + 2 * rating.sigma)
        }

    def populate_chassis_stats(self, historical_match_data):
        """
        Calculates and stores average stats per mech chassis from historical data.
        You would call this method with a large dataset of past matches.
        """
        # columns = ['Chassis', 'MatchScore', 'Kills', 'KillsMostDamage', 'Assists', 'ComponentsDestroyed', 'Damage', 'Uses']
        self.chassis_stats = historical_match_data