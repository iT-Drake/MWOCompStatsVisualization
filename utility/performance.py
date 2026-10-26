
#---------------------------------------------------------------------
# PERFORMANCE INDEX
#
# The index says how a pilot did relative to other pilots who played the same
# mech in the same division. openskill uses it as a weight: above 1 makes the
# rating move more, below 1 less.
#
# Everything here is computed from the raw stats of the history prefix, never
# from the ratings, so the weight cannot feed back into itself.
#---------------------------------------------------------------------

# Half of the survivor-vs-dead gap: survivors get +SURVIVAL, the dead get -SURVIVAL,
# which keeps the same 5 percentage points the old flat +0.05 bonus had.
SURVIVAL = 0.025

# A team of three or fewer (duels included) is too different from the rest of the
# data to be a useful yardstick. Such matches still get rated, their rows are just
# left out of the reference tables.
MIN_TEAM_SIZE = 4


def _centred(values):
    """Divide by the mean, so the values average exactly 1.0."""
    mean = sum(values) / len(values)
    return [value / mean for value in values]


def _survival_shift(alive, survival=SURVIVAL):
    """Survival bonus with a mean of zero, so it cannot move the team average."""
    shift = [survival if flag else -survival for flag in alive]
    mean = sum(shift) / len(shift)
    return [value - mean for value in shift]


def team_weights(indices, alive, lam=1.0, survival=SURVIVAL):
    """
    Rating weights for one team, in the order given.

    The index is scaled by lam (lam=0 ignores performance, lam=1 keeps it as it
    is) and centred, then the survival bonus is added on top.

    Centring is not cosmetic. openskill multiplies a win by the weight but
    *divides* a loss by it, so weights that average below 1 make every loss
    bigger than the matching win. With the mean held at 1.0 the weight only
    decides who inside the team moves more, not how far the team moves. Both
    steps keep the mean at 1.0: the index is divided by its own mean and the
    survival shift is already zero-mean, so the bonus never rescales the index
    spread.
    """
    base = _centred([1.0 + lam * (index - 1.0) for index in indices])
    shift = _survival_shift(alive, survival)
    return [b + s for b, s in zip(base, shift)]


class PerformanceIndex:
    def __init__(self, df, mech_filter=None, min_samples=10):
        """
        Initializes player performance index system.

        Args:
            df: Dataframe with competitive play data.
            min_samples: Minimal number of rows per group to count it as a statistically significant.
        """
        dataset = df.copy() if not mech_filter else df[df['Mech'].isin(mech_filter)].copy()
        
        self._metrics = ['MatchScore', 'Damage', 'Kills', 'KillsMostDamage']
        self._quantiles = [0.2, 0.5, 0.90]
        self._levels = {
            'Mech':    ['Division', 'Mech'],
            'Chassis': ['Division', 'Chassis'],
            'Class':   ['Division', 'Class']
        }

        self._normalize_data(dataset, self._metrics)

        reference = dataset[dataset['TeamSize'] >= MIN_TEAM_SIZE]
        if reference.empty:
            reference = dataset

        self._ref_tables = self._reference_tables(reference, min_samples)
    
    def _normalize_data(self, df, metrics):
        team_counts = df.groupby(['Tournament', 'MatchID', 'TeamName'])['Username'].transform('count')
        df['TeamSize'] = team_counts.round().astype(int)
        for metric in metrics:
            df[metric] = df[metric] / df['TeamSize']
    
    def _reference_tables(self, df, min_samples):
        ref_tables = {}
        for name, group_cols in self._levels.items():
            counts = df.groupby(group_cols)['Username'].transform('count')
            filtered_df = df[counts >= min_samples]
            
            table = filtered_df.groupby(group_cols)[self._metrics].quantile(self._quantiles).unstack()
            table.columns = [f"{m}_{q}" for m, q in table.columns]
            ref_tables[name] = table.reset_index()

        return ref_tables
    
    
    def calculate(self, player_data):
        """Performance index of one row: 1.0 is the median of its reference group."""
        player = player_data['Username']
        ref = None
        for level in self._levels:
            temp_ref = self._ref_tables[level]
            mask = (temp_ref['Division'] == player_data['Division']) & (temp_ref[level] == player_data[level])
            
            res = temp_ref[mask]
            if not res.empty:
                ref = res.iloc[0]
                break
                
        if ref is None:
            return 1.0

        scores = []
        team_size = player_data['TeamSize']
        mech = player_data['Mech']
        # print(f"\n{player}, mech {mech}, scope {level}")
        for metric in self._metrics:
            val = player_data[metric] / team_size
            p50 = ref[f'{metric}_0.5']
            p90 = ref[f'{metric}_0.9']
            p20 = ref[f'{metric}_0.2']
            
            if val >= p50:
                # Good performance
                raw_score = 1.0 + (min((val - p50) / (p90 - p50 + 1e-6), 1.0) * 0.25)
            else:
                # Bad performance
                raw_score = 1.0 - (min((p50 - val) / (p50 - p20 + 1e-6), 1.0) * 0.25)
            
            scores.append(raw_score)
            # print(f"{metric} {p20:.2f} - {p50:.2f} - {p90:.2f}, value {player_data[metric]:.2f}, normalized {val:.2f}, score {raw_score:.2f}")
        
        # final_weight = max(scores)
        final_weight = sum(scores) / len(scores)
            
        return final_weight

    def weigh(self, team_data, lam=1.0):
        """Rating weights for the rows of one team, in the same order."""
        indices = [self.calculate(row) for _, row in team_data.iterrows()]
        alive = [row['HealthPercentage'] > 0 for _, row in team_data.iterrows()]
        return team_weights(indices, alive, lam)
