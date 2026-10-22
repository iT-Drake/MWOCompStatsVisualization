
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
        self._ref_tables = self._reference_tables(dataset, min_samples)
    
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
        health = player_data['HealthPercentage']
        mech = player_data['Mech']
        # print(f"\n{player}, mech {mech}, scope {level}, health {health:.2f}")
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
        
        # Survival bonus
        if health > 0:
            final_weight = final_weight + 0.05
            
        return final_weight
