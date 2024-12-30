from enum import Enum

class SortingOption(Enum):
    Score = 'Score'
    AdjustedWLR = 'Adjusted WLR'
    MatchScore = 'Match score'
    Damage = 'Damage'

    def __str__(self):
        return self.value
    
    @classmethod
    def Default(cls):
        return cls.Score

class AggregationMethod(Enum):
    Mean = 'Average values'
    Sum = 'Total values'

    def __str__(self):
        return self.value
    
    @classmethod
    def Default(cls):
        return cls.Mean
