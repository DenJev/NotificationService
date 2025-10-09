from enum import StrEnum


class ResponseStatusEnum(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    ACCOUNT_SIGN_UP_FAILED = "account sign up failed"


class WordResponseStatusEnum(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    FAILED = "failed"


class GameResponseStatusEnum(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    FAILED = "failed"
    SUBMITTED = "submitted"


class WordValidResponseStatusEnum(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    WORD_NOT_FOUND = "word not found"
