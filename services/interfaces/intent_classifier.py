from abc import ABC, abstractmethod
from enum import StrEnum


class Intent(StrEnum):
    PRICING = "pricing"
    AVAILABILITY = "availability"
    GENERAL = "general"
    CONVERSION = "conversion"


# Score deltas for lead scoring (conversion is 25x general — reflects sales reality)
INTENT_SCORES: dict[Intent, int] = {
    Intent.GENERAL: 1,
    Intent.AVAILABILITY: 5,
    Intent.PRICING: 10,
    Intent.CONVERSION: 25,
}


class IIntentClassifier(ABC):
    """
    Contract for classifying a user message into a sales intent category.
    Concrete implementations: KeywordIntentClassifier.
    """

    @abstractmethod
    def classify(self, message: str) -> Intent:
        """Return the Intent that best describes the message."""
        ...
