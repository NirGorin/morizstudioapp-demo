from enum import Enum

class GenderEnum(str, Enum):
    male = "male"
    female = "female"

class RoleEnum(str, Enum):
    admin = "admin"
    trainer = "trainer"
    trainee = "trainee"

class LevelEnum(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"
    expert = "expert"

class NumberOfWeekTrainingEnum(str, Enum):
    one = "one"
    two = "two"
    three = "three"
    four = "four"
    five = "five"