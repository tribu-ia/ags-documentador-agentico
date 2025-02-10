from dataclasses import dataclass

@dataclass
class QueryValidation:
    """Validation scores for a search query"""
    specificity: float
    relevance: float
    clarity: float
    
    @property
    def overall_score(self) -> float:
        return (self.specificity + self.relevance + self.clarity) / 3 