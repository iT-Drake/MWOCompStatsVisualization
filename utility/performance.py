
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

# What the index is built from, and how much each part counts.
#
# Raw Damage is deliberately absent: 83-89 % of it is already inside MatchScore,
# and the part that is not - damage that killed nothing - is exactly what spread
# weapons in the low divisions inflate. Everything else keeps a damage concept:
# KillsMostDamage is damage that mattered, ComponentsDestroyed is damage that
# landed on one component.
METRICS = ['MatchScore', 'KillsMostDamage', 'ComponentsDestroyed', 'Kills']
WEIGHTS = {
    'MatchScore': 0.40,
    'KillsMostDamage': 0.25,
    'ComponentsDestroyed': 0.20,
    'Kills': 0.15,
}

# Groups smaller than this do not make a yardstick of their own.
MIN_SAMPLES = 10

# Blends a group's quantiles into its parent's by sample size instead of
# dropping the group below MIN_SAMPLES: n/(n+SHRINKAGE) of the own table, the
# rest from the coarser level. 0 switches the blending off.
SHRINKAGE = 0.0

_LEVELS = {
    'Mech':    ['Division', 'Mech'],
    'Chassis': ['Division', 'Chassis'],
    'Class':   ['Division', 'Class'],
}
_QUANTILES = [0.2, 0.5, 0.9]
_SPREAD = 0.25


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


def metric_score(value, p20, p50, p90):
    """Relative position of one stat inside its reference group, in 0.75 ... 1.25."""
    if value >= p50:
        return 1.0 + min((value - p50) / (p90 - p50 + 1e-6), 1.0) * _SPREAD
    return 1.0 - min((p50 - value) / (p50 - p20 + 1e-6), 1.0) * _SPREAD


def reference_quantiles(reference, shrinkage=SHRINKAGE, min_samples=MIN_SAMPLES):
    """
    The quantiles one row is measured against, or None if there is no basis.

    Args:
        reference: {level: (group_size, {metric: (p20, p50, p90)})} for every
            level that contains the row, finest first (see PerformanceIndex.reference).
        shrinkage: 0 keeps the plain rule - the finest level with at least
            min_samples rows. A positive value blends every level into the
            coarser one by sample size instead, so a rare variant contributes
            its own shape (25 % of the weight at 10 rows, 50 % at n = shrinkage,
            77 % at 100) rather than being silently replaced by its chassis.
            There is no cliff either way: the group sizes come from raw stats,
            so a variant keeps accumulating until it qualifies.

    Returns:
        {metric: (p20, p50, p90)} or None when no level holds enough rows.
    """
    levels = [level for level in _LEVELS if level in reference]
    if not levels:
        return None

    if shrinkage <= 0:
        for level in levels:
            size, quantiles = reference[level]
            if size >= min_samples:
                return quantiles
        return None

    # Coarsest first, each finer level blended into the result of the previous one.
    quantiles = None
    for level in reversed(levels):
        size, current = reference[level]
        if quantiles is None:
            quantiles = dict(current)
            continue
        weight = size / (size + shrinkage)
        quantiles = {
            metric: tuple(weight * own + (1.0 - weight) * parent
                          for own, parent in zip(current[metric], quantiles[metric]))
            for metric in current
        }
    return quantiles


def index_from_values(values, quantiles, metrics=None, weights=None):
    """
    Weighted mean of the per-metric scores of one row.

    Args:
        values: {metric: value per pilot} - already divided by the team size,
            which is the basis the reference tables are built on.
        quantiles: {metric: (p20, p50, p90)} or None for "no statistical record".
        metrics: metrics to use, defaults to the shipped set.
        weights: metric weights, defaults to WEIGHTS (a metric that is not in
            WEIGHTS counts as 1.0, so an alternative metric set must pass its own).

    Returns:
        1.0 when there is no reference, i.e. an entire match with no history.
    """
    if quantiles is None:
        return 1.0

    metrics = metrics or METRICS
    weights = weights or WEIGHTS

    total = 0.0
    weight_sum = 0.0
    for metric in metrics:
        weight = weights.get(metric, 1.0)
        total += weight * metric_score(values[metric], *quantiles[metric])
        weight_sum += weight
    return total / weight_sum


class PerformanceIndex:
    def __init__(self, df, mech_filter=None, min_samples=MIN_SAMPLES, shrinkage=SHRINKAGE, metrics=None):
        """
        Initializes player performance index system.

        Args:
            df: Dataframe with competitive play data.
            min_samples: Minimal number of rows per group to count it as a statistically significant.
            shrinkage: Sample size at which a group's own table gets half of the weight.
                Only used when min_samples cannot settle the group on its own.
            metrics: Metrics to build the reference tables from, defaults to METRICS.
                Only tools that compare metric sets need to pass this.
        """
        self._metrics = list(metrics or METRICS)
        self._weights = {metric: WEIGHTS.get(metric, 1.0) for metric in self._metrics}
        self._min_samples = min_samples
        self._shrinkage = shrinkage

        dataset = df.copy() if not mech_filter else df[df['Mech'].isin(mech_filter)].copy()
        self._normalize_data(dataset, self._metrics)

        reference = dataset[dataset['TeamSize'] >= MIN_TEAM_SIZE]
        if reference.empty:
            reference = dataset

        # Every group is kept, with its size. Whether a group is big enough to be
        # used is decided per row in reference_quantiles(), which is what lets the
        # same tables serve both the hard threshold and the blended variants.
        self._ref_tables = self._reference_tables(reference)

    def _normalize_data(self, df, metrics):
        team_counts = df.groupby(['Tournament', 'MatchID', 'TeamName'])['Username'].transform('count')
        df['TeamSize'] = team_counts.round().astype(int)
        for metric in metrics:
            df[metric] = df[metric] / df['TeamSize']

    def _reference_tables(self, df):
        ref_tables = {}
        for name, group_cols in _LEVELS.items():
            grouped = df.groupby(group_cols)
            table = grouped[self._metrics].quantile(_QUANTILES).unstack()
            table.columns = [f"{m}_{q}" for m, q in table.columns]
            table = table.reset_index()

            sizes = df.groupby(group_cols).size().rename('Size').reset_index()
            ref_tables[name] = table.merge(sizes, on=group_cols, how='left')

        return ref_tables

    def reference(self, row, complete=True):
        """
        The reference groups that hold this row.

        Args:
            complete: True collects every level, which is what the blended variants
                and tools/tune_lambda.py need. False stops at the first level that
                qualifies, which is all reference_quantiles() looks at when the hard
                threshold is in force - that is the production path and the walk over
                the tables is the expensive part of it.

        Returns:
            {level: (group_size, {metric: (p20, p50, p90)})}, finest level first.
        """
        reference = {}
        for level in _LEVELS:
            table = self._ref_tables[level]
            if table.empty:
                continue

            mask = (table['Division'] == row['Division']) & (table[level] == row[level])
            matches = table[mask]
            if matches.empty:
                continue

            entry = matches.iloc[0]
            size = int(entry['Size'])
            reference[level] = (size, {
                metric: (entry[f'{metric}_0.2'], entry[f'{metric}_0.5'], entry[f'{metric}_0.9'])
                for metric in self._metrics
            })
            if not complete and size >= self._min_samples:
                break
        return reference

    def values(self, row):
        """The row's stats per pilot, the basis the reference tables are built on."""
        team_size = row['TeamSize']
        return {metric: row[metric] / team_size for metric in self._metrics}

    def calculate(self, player_data):
        """Performance index of one row: 1.0 is the median of its reference group."""
        complete = self._shrinkage > 0
        quantiles = reference_quantiles(self.reference(player_data, complete),
                                        self._shrinkage, self._min_samples)
        return index_from_values(self.values(player_data), quantiles, self._metrics, self._weights)

    def weigh(self, team_data, lam=1.0):
        """Rating weights for the rows of one team, in the same order."""
        indices = [self.calculate(row) for _, row in team_data.iterrows()]
        alive = [row['HealthPercentage'] > 0 for _, row in team_data.iterrows()]
        return team_weights(indices, alive, lam)
