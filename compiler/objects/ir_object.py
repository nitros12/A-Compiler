from enum import IntEnum
from typing import Optional, Union, Iterable, List, Set, Any
from dataclasses import dataclass, field

from compiler.objects.variable import Variable
from compiler.objects.astnode import BaseObject


def pullsize(arg):
    if hasattr(arg, "size"):
        return arg.size
    return 4


class CompType(IntEnum):
    (leq, lt, eq, neq, gt, geq, uncond) = range(7)


@dataclass
class Register:
    reg: int
    size: int
    sign: bool = False
    physical_register: int = field(default=None, init=False)

    def resize(self, new_size: int=None, new_sign: bool=None) -> 'Register':
        """Get a resized copy of this register."""
        size = new_size or self.size
        sign = new_sign or self.sign
        return Register(self.reg, size, sign)

    def copy(self) -> 'Register':
        return Register(self.reg, self.size, self.sign)

    def __eq__(self, other):
        if not isinstance(other, Register):
            return False
        return self.reg == other.reg

    def __hash__(self):
        return hash(self.reg << 3)

    def __str__(self):
        phys_reg = self.physical_register if self.physical_register is not None else ''
        return f"%{self.reg}@{phys_reg}({'s' if self.sign else 'u'}{self.size})"

    __repr__ = __str__


@dataclass
class Immediate:

    val: int
    size: int

    def __str__(self):
        return f"Imm({self.val}:{self.size})"

    __repr__ = __str__


@dataclass
class Dereference:

    to: Register

    def __post_init__(self):
        self.to = self.to.copy()
        assert self.to.size == 2

    @property
    def size(self):
        return pullsize(self.to)

    def __str__(self):
        return f"Dereference({self.to})"


IRParam = Union[Register, Dereference, Immediate]


def filter_reg(reg: IRParam) -> Optional[Register]:
    """Filters a possible register object. returns None if not a register."""
    if isinstance(reg, Dereference):
        return reg.to
    if isinstance(reg, Register):
        return reg
    return None


@dataclass
class IRObject:
    """An instruction in internal representation."""

    #: list of instructions to be run before this instruction
    pre_instructions: List['IRObject'] = field(default_factory=list, init=False)

    #: regisers that are dead after this instruction
    closing_registers: Set[Register] = field(default_factory=set, init=False)

    parent: Optional[BaseObject] = field(default=None, init=False)

    def clone_regs(self):
        """Clone the registers of this instruction.
        This is so that they can be mutated without affecting other IR instructions."""
        def copy_reg(arg):
            if isinstance(arg, Register):
                return arg.copy()
            return arg

        for attr in self._touched_regs:
            # copy the instances of the registers we're using
            setattr(self, attr, copy_reg(getattr(self, attr)))

    @property
    def touched_registers(self) -> Iterable[Register]:
        """Get the registers that this instruction reads from and writes to."""
        attrs = self._touched_regs
        regs = (filter_reg(getattr(self, i)) for i in attrs)
        return list(filter(None, regs))

    _touched_regs = ()

    def insert_pre_instrs(self, *instrs):
        self.pre_instructions.extend(instrs)


@dataclass
class MakeVar(IRObject):
    # TODO: why does this exist?
    var: Variable


@dataclass
class LoadVar(IRObject):
    """Load a variable to a location.

    :param variable: Variable info object.
    :param to: Location to load to.
    :param lvalue: If true: load the memory location, if false, load the value.
    """

    variable: Variable
    to: IRParam
    lvalue: bool = False

    _touched_regs = ("to",)


@dataclass
class SaveVar(IRObject):

    variable: Variable
    from_: IRParam

    _touched_regs = ("from_",)


@dataclass
class Mov(IRObject):
    """More general than LoadVar/ SaveVar, for setting registers directly."""

    to: IRParam
    from_: IRParam

    _touched_regs = "to", "from_"


class UnaryMeta(type):

    def __getattr__(cls, attr):
        if attr in cls.valid_ops:
            return lambda arg, to=None: cls(arg, attr, to)
        raise AttributeError(f"Unary op has no sub-op {attr}")


@dataclass
class Unary(IRObject, metaclass=UnaryMeta):
    """Unary operation

    if :param to: is not provided, defaults to :param  arg:
    """

    arg: IRParam
    op: str
    to: Optional[IRParam] = None

    def __post_init__(self):
        if self.to is None:
            self.to = self.arg

    valid_ops = ("binv", "linv", "neg", "pos")

    _touched_regs = ("op",)


class BinaryMeta(type):

    def __getattr__(cls, attr):
        if attr in cls.valid_ops:
            return lambda left, right, to=None: cls(left, right, attr, to)
        raise AttributeError(f"Binary op has no sub-op {attr}")


@dataclass
class Binary(IRObject, metaclass=BinaryMeta):
    """Binary operation.

    if :param to: is not provided, defaults to :param left:
    """

    left: IRParam
    right: IRParam
    op: str
    to: Optional[IRParam] = None

    def __post_init__(self):
        if self.to is None:
            self.to = self.left

    valid_ops = ("add", "sub", "mul", "div")

    _touched_regs = "left", "right", "to"


@dataclass
class Compare(IRObject):
    """Comparison operation.

    Compares two operands and sets resultant registers.
    """

    left: IRParam
    right: IRParam

    _touched_regs = "left", "right"


@dataclass
class SetCmp(IRObject):
    """Set register from last comparison."""

    reg: IRParam
    op: CompType

    _touched_regs = ("reg",)


@dataclass
class Push(IRObject):

    arg: IRParam

    _touched_regs = ("arg",)


@dataclass
class Pop(IRObject):

    arg: IRParam

    _touched_regs = ("arg",)


@dataclass
class Prelude(IRObject):
    """Function/ scope prelude."""

    scope: Any


@dataclass
class Epilog(IRObject):
    """Function/ scope epilog."""

    scope: Any


@dataclass
class Return(IRObject):
    """Function return
    This should be placed after preludes to all scopes beforehand.
    """

    reg: Optional[IRParam] = None

    _touched_regs = ("reg",)


@dataclass
class Call(IRObject):
    """Jump to location, push return address."""

    args: List[IRParam]
    jump: IRParam
    result: IRParam

    @property
    def argsize(self):
        return sum(i.size for i in self.args)

    _touched_regs = "jump", "result"


@dataclass
class Jumpable(IRObject):

    jumps_from: List['Jumpable'] = field(default_factory=list, init=False)
    jumps_to: List['Jumpable'] = field(default_factory=list, init=False)

    def add_jump_to(self, from_: 'Jumpable'):
        self.jumps_from.append(from_)
        from_.jumps_to.append(self)

    def take_jumps_from(self, other: 'Jumpable'):
        """Take all the jumps from another objects and make them owned by this."""
        for i in other.jumps_from:
            i.jumps_to.remove(self)
            i.jumps_to.append(self)
        self.jumps_from.extend(other.jumps_from)
        other.jumps_from = []


class JumpTarget(Jumpable):
    """Jump target."""
    pass


@dataclass
class Jump(Jumpable):
    """Conditional jump.

    If condition is not provided this is a unconditional jump, otherwise tests for truthyness of the argument
    """

    location: JumpTarget
    condition: Optional[IRParam] = None

    def __post_init__(self):
        self.add_jump_to(self.location)

    _touched_regs = ("condition",)


@dataclass
class Resize(IRObject):
    """Resize data."""

    from_: IRParam
    to: IRParam

    _touched_regs = "from_", "to"


@dataclass
class Spill(IRObject):
    """Spill a register to a location.

    :reg: Physical register to save
    :index: Index of saved registers to save to
    """

    reg: int
    index: int


@dataclass
class Load(IRObject):
    """Recover a spilled register.

    :reg: Physical register to load into
    :index: Index of saved registers to load from
    """

    reg: int
    index: int
