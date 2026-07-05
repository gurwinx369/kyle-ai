from enum import Enum


class RoleEnum(str, Enum):
    student = "student"
    developer = "developer"
    writer = "writer"
    designer = "designer"
    other = "other"


class ModeEnum(str, Enum):
    contextual = "contextual"
    general = "general"
