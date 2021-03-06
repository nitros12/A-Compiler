from enum import IntEnum
from typing import Optional, Union, Iterable, List, Set, Any
from dataclasses import dataclass, field

from wewcompiler.objects.variable import Variable, DataReference
from wewcompiler.objects.astnode import BaseObject

class CompType(IntEnum):
    (uncond,  # unconditional (set to 1)
     lt,  # less than
     leq,  # less than or equal
     eq,  # equal to
     lts,  # less than signed
     leqs,  # less than or equal signed
     geq,  # greater than or equal
     gt,  # greater than
     neq,  # not equal to
     geqs,  # greather than or equal signed
     gts) = range(11)  # greater than signed


@dataclass
class AllocatedRegister:
    """References an allocated register."""

    size: int
    sign: bool = False
    physical_register: Optional[int] = None


@dataclass
class Register:
    """A generic register for an infinite register machine."""

    reg: int
    size: int
    sign: bool = False
    physical_register: Optional[int] = None

    def resize(self, new_size: int = None, new_sign: bool = None) -> 'Register':
        """Get a resized copy of this register."""
        size = new_size or self.size
        sign = new_sign or self.sign
        return Register(self.reg, size, sign)

    def copy(self) -> 'Register':
        return self.__copy__()

    def __copy__(self):
        return type(self)(self.reg, self.size, self.sign)

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
    """An immediate value."""

    __slots__ = ("val", "size")

    val: int
    size: int

    def __str__(self):
        return f"Imm({self.val}:{self.size})"

    def __post_init__(self):
        assert isinstance(self.val, int)

    __repr__ = __str__


@dataclass
class Dereference:
    """Represents dereferencing a register, address or immediate value."""

    __slots__ = ("to", "size")

    to: Union[Register, AllocatedRegister, Immediate, DataReference]
    size: int

    def __post_init__(self):
        if isinstance(self.to, Register):
            self.to = self.to.copy()

    def __str__(self):
        return f"Dereference({self.to})"


IRParam = Union[Register, AllocatedRegister, Dereference, Immediate, DataReference]


def filter_reg(reg: IRParam) -> Optional[Register]:
    """Filters a possible register object. returns None if not a register."""
    if isinstance(reg, Dereference) and isinstance(reg.to, Register):
        return reg.to
    if isinstance(reg, Register):
        return reg
    return None


@dataclass
class IRObject:
    """An instruction in internal representation."""

    #: list of instructions to be run before this instruction
    pre_instructions: List[Any] = field(default_factory=list, init=False, repr=False)

    #: regisers that are dead after this instruction
    closing_registers: Set[Register] = field(default_factory=set, init=False, repr=False)

    parent: Optional[BaseObject] = field(default=None, init=False, repr=False)

    def clone_regs(self):
        """Clone the registers of this instruction.
        This is so that they can be mutated without affecting other IR instructions."""
        def copy_reg(arg):
            if isinstance(arg, Register):
                return arg.copy()
            return arg

        for attr in self.touched_regs:
            # copy the instances of the registers we're using
            setattr(self, attr, copy_reg(getattr(self, attr)))

    @property
    def touched_registers(self) -> Iterable[Register]:
        """Get the registers that this instruction reads from and writes to."""
        attrs = self.touched_regs
        regs = (filter_reg(getattr(self, i)) for i in attrs)
        return list(filter(None, regs))

    touched_regs = ()

    def insert_pre_instrs(self, *instrs):
        self.pre_instructions.extend(instrs)


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

    touched_regs = ("to",)


@dataclass
class SaveVar(IRObject):

    __slots__ = ("variable", "from_")

    variable: Variable
    from_: IRParam

    touched_regs = ("from_",)


@dataclass
class Mov(IRObject):
    """More general than LoadVar/ SaveVar, for setting registers directly."""

    __slots__ = ("to", "from_")

    to: IRParam
    from_: IRParam

    touched_regs = "to", "from_"


class UnaryMeta(type):
    """Metaclass for the Unary ir object.
    used to allow Unary.neg(arg, to) as a shortcut to Unary(arg, "neg", to)
    """

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

    touched_regs = ("arg", "to")


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

    valid_ops = ("add", "sub", "mul", "udiv", "idiv",
                 "shr", "sar", "shl", "and", "or", "xor",
                 "imod", "umod")

    touched_regs = "left", "right", "to"


@dataclass
class Compare(IRObject):
    """Comparison operation.

    Compares two operands and sets resultant registers.
    """

    __slots__ = ("left", "right")

    left: IRParam
    right: IRParam

    touched_regs = "left", "right"


@dataclass
class SetCmp(IRObject):
    """Set a location from the results of the last comparison."""

    __slots__ = ("dest", "op")

    dest: IRParam
    op: CompType

    touched_regs = ("dest",)


@dataclass
class Push(IRObject):

    __slots__ = ("arg",)

    arg: IRParam

    touched_regs = ("arg",)


@dataclass
class Pop(IRObject):

    __slots__ = ("arg",)

    arg: IRParam

    touched_regs = ("arg",)


@dataclass
class Prelude(IRObject):
    """Function/ scope prelude."""

    __slots__ = ("scope",)

    scope: Any


@dataclass
class Epilog(IRObject):
    """Function/ scope epilog."""

    __slots__ = ("scope",)

    scope: Any


@dataclass
class Return(IRObject):
    """Function return
    This should be placed after preludes to all scopes beforehand.
    """

    scope: Any
    arg: Optional[IRParam] = None

    touched_regs = ("arg",)


@dataclass
class Call(IRObject):
    """Call a procedure with arguments and possibly collect the result."""

    args: List[IRParam]
    jump: IRParam
    result: Optional[IRParam] = None

    @property
    def argsize(self):
        return sum(i.size for i in self.args)

    touched_regs = "jump", "result"


@dataclass
class Jumpable(IRObject):

    jumps_from: List['Jumpable'] = field(default_factory=list, init=False, repr=False)
    jumps_to: List['Jumpable'] = field(default_factory=list, init=False, repr=False)

    # none of these are used at the moment but if we add optimisations they will be needed
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

    __slots__ = ()

    @property
    def identifier(self):
        return f"jump-target-{id(self)}"

    def __repr__(self):
        return f"{self.__class__.__name__}(identifier={self.identifier})"


@dataclass
class Jump(Jumpable):
    """Conditional jump.

    If condition is not provided this is a unconditional jump,
    otherwise tests for truthyness of the argument
    """

    location: JumpTarget
    condition: Optional[IRParam] = None

    def __post_init__(self):
        self.add_jump_to(self.location)

    touched_regs = ("condition",)


@dataclass
class Resize(IRObject):
    """Resize data."""

    __slots__ = ("from_", "to")

    from_: IRParam
    to: IRParam

    touched_regs = "from_", "to"


@dataclass
class MachineInstr(IRObject):
    """Special machine instruction IR type to allow for inline ASM."""

    __slots__ = ("instr", "size", "args")

    instr: str
    size: int
    args: List[IRParam]

    @property
    def touched_registers(self) -> Iterable[Register]:
        """Get the registers that this instruction reads from and writes to."""

        regs = map(filter_reg, self.args)
        return list(filter(None, regs))
