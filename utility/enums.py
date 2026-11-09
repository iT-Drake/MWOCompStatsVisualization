from enum import Enum

class SortingOption(Enum):
    MatchScore = 'Match score'
    WLR = 'Win-Loss ratio'
    Damage = 'Damage'

    def __str__(self):
        return self.value
    
    @classmethod
    def Default(cls):
        return cls.MatchScore

class AggregationMethod(Enum):
    Mean = 'Average values'
    Sum = 'Total values'

    def __str__(self):
        return self.value
    
    @classmethod
    def Default(cls):
        return cls.Mean
