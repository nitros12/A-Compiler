from typing import Optional

from dataclasses import dataclass

from wewcompiler.objects.types import Type
from wewcompiler.objects.astnode import BaseObject


@dataclass
class DataReference:
    """Index to some named object, the exact location to be resolved later."""
    name: str


@dataclass
class Variable:
    """A reference to a variable, holds scope and location information."""

    name: str
    type: Type
    parent: Optional[BaseObject] = None

    stack_offset: Optional[int] = None
    global_offset: Optional[DataReference] = None

    #: are we a function or something where dereferencing doesn't make sense
    lvalue_is_rvalue: Optional[bool] = False

    @property
    def size(self) -> int:
        return self.type.size

    @property
    def identifier(self) -> str:
        return self.name

    def __str__(self):
        return f"Variable({self.name}, {self.type})"