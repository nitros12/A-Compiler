from typing import Union, Tuple, Iterable
from enum import IntEnum
from dataclasses import dataclass

from wewcompiler.objects.ir_object import Register, Dereference, DataReference, JumpTarget
from wewcompiler.objects.errors import InternalCompileException
from wewcompiler.objects import ir_object
from wewcompiler.utils.emitterclass import Emitter, emits

class BinaryInstructions(IntEnum):
    """Binary instructions."""
    (add, sub, mul, udiv, idiv, shl,
     shr, sar, and_, or_, xor, imod,
     umod) = range(13)

    @property
    def group(self):
        return 0


class UnaryInstructions(IntEnum):
    """Unary instructions."""
    (binv, linv, neg, pos) = range(4)

    @property
    def group(self):
        return 1


class Manip(IntEnum):
    """Cpu manipulation instructions."""
    (mov, sxu, sxi, jmp, set, tst, halt) = range(7)

    @property
    def group(self):
        return 2


class Mem(IntEnum):
    """Memory manipulation instructions."""
    (stks, push, pop, call, ret) = range(5)

    @property
    def group(self):
        return 3


class IO(IntEnum):
    """IO instructions."""
    (getc, putc, putint) = range(3)

    @property
    def group(self):
        return 4


# Why have this? because we need to distinguish from allocated free-use registers
# and other registers (stack pointer, base pointer, current-instruction pointer, etc)

@dataclass(frozen=True)
class HardwareRegister:
    """Reference to a named hardware register."""

    __slots__ = ("index",)

    index: int
    size = 8  # all hardware registers are just size 8


@dataclass(frozen=True)
class HardwareMemoryLocation:

    __slots__ = ("index",)

    index: int


class SpecificRegisters:
    free_reg_offset = 4

    (stk, bas, cur, ret) = map(HardwareRegister, range(4))


@dataclass
class HardWareInstruction:

    __slots__ = ("instr", "size", "args")

    instr: Union[BinaryInstructions,
                 UnaryInstructions,
                 Manip,
                 Mem,
                 IO]
    size: int
    args: Tuple[Union[Register,
                      Dereference,
                      DataReference,
                      HardwareMemoryLocation,
                      JumpTarget]]

    @property
    def code_size(self):
        return 2 * (1 + len(self.args))


def pack_instruction(instr: HardWareInstruction) -> bytes:
    """Pack an instruction into bytes."""
    idx = instr.instr

    size = {
        1: 0,
        2: 1,
        4: 2,
        8: 3
    }[instr.size]

    value = (size << 14) | (idx.group << 8) | idx
    return (value & 0xffff).to_bytes(2, byteorder="little")


def pack_param(param: int, reg: bool = False, deref: bool = False) -> bytes:
    """Packs a single parameter into bytes."""
    signed = param < 0
    return (param | reg << 15 | deref << 14).to_bytes(2, byteorder="little", signed=signed)


class InstructionEncoder(Emitter):

    @staticmethod
    def default(obj):
        name = type(obj).__name__
        raise InternalCompileException(f"Missing encoder for instruction {name}")

    @classmethod
    def encode_instr(cls, instr: ir_object.IRObject) -> Iterable[HardWareInstruction]:
        """Encode an IR Instruction into a hardware instruction.
        Some instructions may expand into multiple hardware instructions so the result is an iterable.
        """
        yield from cls.method_for(instr)(instr)

    @emits(ir_object.JumpTarget)
    def emit_jumptarget(cls, instr: ir_object.JumpTarget):
        yield instr

    @emits(ir_object.Mov)
    def emit_mov(cls, instr: ir_object.Mov):
        yield HardWareInstruction(
            Manip.mov,
            instr.to.size,
            (instr.to, instr.from_)
        )

    @emits(ir_object.Unary)
    def emit_unary(cls, instr: ir_object.Unary):

        hwin = getattr(UnaryInstructions, instr.op)

        yield HardWareInstruction(
            hwin,
            instr.arg.size,
            (instr.arg, instr.to)
        )

    @emits(ir_object.Binary)
    def emit_binary(cls, instr: ir_object.Binary):

        replacements = {
            "and": "and_",
            "or": "or_"
        }

        # replace 'and' with 'and_', etc. leave everything else
        op = replacements.get(instr.op) or instr.op

        hwin = getattr(BinaryInstructions, op)

        yield HardWareInstruction(
            hwin,
            instr.left.size,
            (instr.left, instr.right, instr.to)
        )

    @emits(ir_object.Compare)
    def emit_compare(cls, instr: ir_object.Compare):
        yield HardWareInstruction(
            Manip.tst,
            instr.left.size,
            (instr.left, instr.right)
        )

    @emits(ir_object.SetCmp)
    def emit_setcmp(cls, instr: ir_object.SetCmp):
        yield HardWareInstruction(
            Manip.set,
            instr.dest.size,
            (instr.op, instr.dest)
        )

    @emits(ir_object.Push)
    def emit_push(cls, instr: ir_object.Push):
        yield HardWareInstruction(
            Mem.push,
            instr.arg.size,
            (instr.arg,)
        )

    @emits(ir_object.Pop)
    def emit_pop(cls, instr: ir_object.Pop):
        yield HardWareInstruction(
            Mem.pop,
            instr.arg.size,
            (instr.arg,)
        )

    @emits(ir_object.Return)
    def emit_return(cls, instr: ir_object.Return):
        if instr.arg is not None:
            yield HardWareInstruction(
                Manip.mov,
                instr.arg.size,
                (SpecificRegisters.ret, instr.arg)
            )

        for reg in reversed(instr.scope.used_hw_regs):
            yield HardWareInstruction(
                Mem.pop,
                8,
                (ir_object.AllocatedRegister(8, False, reg), )
            )

        yield HardWareInstruction(
            BinaryInstructions.sub,
            8,
            (SpecificRegisters.stk, ir_object.Immediate(instr.scope.size, 8), SpecificRegisters.stk)
        )

        yield HardWareInstruction(
            Mem.ret,
            1,  # unused
            ()
        )

    @emits(ir_object.Call)
    def emit_call(cls, instr: ir_object.Call):

        yield HardWareInstruction(
            Mem.call,
            instr.jump.size,  # size of return address (we have two byte pointers)
            (instr.jump,)
        )

        arg_len = ir_object.Immediate(instr.argsize, 8)

        # move up the stack pointer to clear off the arguments

        yield HardWareInstruction(
            BinaryInstructions.sub,
            arg_len.size,
            (SpecificRegisters.stk, arg_len, SpecificRegisters.stk)
        )
        if instr.result is not None:
            yield HardWareInstruction(
                Manip.mov,
                instr.result.size,
                (instr.result, SpecificRegisters.ret)
            )

    @emits(ir_object.Jump)
    def emit_jump(cls, instr: ir_object.Jump):
        condition = instr.condition or ir_object.Immediate(1, 2)  # 2-byte containing 1

        yield HardWareInstruction(
            Manip.jmp,
            condition.size,
            (condition, instr.location)
        )

    @emits(ir_object.Resize)
    def emit_resize(cls, instr: ir_object.Resize):

        # if source is signed, we emit signed resize
        hwin = Manip.sxi if instr.from_.sign else Manip.sxu

        # instruction size is size of 'from_' param
        # instruction size parameter is size of 'to' param

        size = {
            1: 0,
            2: 1,
            4: 2,
            8: 3
        }[instr.to.size]

        yield HardWareInstruction(
            hwin,
            instr.from_.size,
            (instr.from_, size, instr.to)
        )

    @emits(ir_object.MachineInstr)
    def emit_machine_instr(cls, instr: ir_object.MachineInstr):

        for group in (BinaryInstructions, UnaryInstructions, Manip, Mem, IO):
            hwin = getattr(group, instr.instr, None)
            if hwin is not None:
                break
        else:
            raise InternalCompileException(f"Could not find instruction by name: {instr.instr}")

        yield HardWareInstruction(
            hwin,
            instr.size,
            tuple(instr.args)
        )
