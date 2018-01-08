from compiler.objects import types
from compiler.objects.base import (CompileContext, ExpressionObject,
                                   ObjectRequest, Variable, ExprCompileType)
from compiler.objects.ir_object import (Dereference, Immediate, LoadVar, Mov,
                                        Register)
from typing import Generator, List, Tuple, Union

from tatsu.ast import AST


def is_constant_expression(obj: ExpressionObject) -> bool:
    return isinstance(obj, (IntegerLiteral, StringLiteral))


class IntegerLiteral(ExpressionObject):
    def __init__(self, ast: AST):
        super().__init__(ast)
        self.lit: int = ast.val
        self._type = ast.type or types.Int('s2')

    @property
    def type(self):
        return self._type

    @property
    def bytes(self):
        typ = yield from self.type
        return self.lit.to_bytes(typ.size, "little", signed=typ.signed)

    def compile(self, ctx: CompileContext) -> Register:
        reg = ctx.get_register(self._type.size, self._type.signed)
        ctx.emit(Mov(reg, Immediate(self.lit, self._type.size)))
        return reg


class StringLiteral(ExpressionObject):

    def __init__(self, ast: AST):
        super().__init__(ast)
        self.lit = ast.str

    @property
    def type(self):
        return types.string_lit

    def compile(self, ctx: CompileContext) -> ExprCompileType:
        var = ctx.compiler.add_string(self.lit)
        reg = ctx.get_register((yield from self.size))
        ctx.emit(LoadVar(var, reg, lvalue=True))
        return reg


class Identifier(ExpressionObject):
    def __init__(self, ast: AST):
        super().__init__(ast)
        self.name = ast.identifier
        self.var = None

    @property
    def type(self):
        if self.var is None:
            self.var = yield ObjectRequest(self.name)
        return self.var.type

    def load_value(self, ctx: CompileContext) -> Generator[ObjectRequest, Variable, Tuple[Register, Variable]]:
        if self.var is None:
            self.var = yield ObjectRequest(self.name)
        reg = ctx.get_register(types.Pointer(self.var.type).size)
        ctx.emit(LoadVar(self.var, reg, lvalue=True))
        return reg, self.var

    def load_lvalue(self, ctx: CompileContext) -> ExprCompileType:
        reg, _ = yield from self.load_value(ctx)
        return reg

    def compile(self, ctx: CompileContext) -> ExprCompileType:
        reg, var = yield from self.load_value(ctx)
        if isinstance(var.type, types.Array):
            return reg  # array type, value is the pointer
        rego = reg.resize(var.size)
        ctx.emit(Mov(rego, Dereference(reg)))
        return rego


class ArrayLiteral(ExpressionObject):
    def __init__(self, ast: AST):
        super().__init__(ast)
        self.exprs: List[ExpressionObject] = ast.obj

        self._type = None

    @property
    def type(self) -> Generator[ObjectRequest, Variable, Union[types.Array, types.Pointer]]:
        if self._type is None:
            self._type = types.Pointer((yield from self.exprs[0].type), const=True)
        return self._type

    def to_array(self):
        """Convert type to array object from pointer object."""
        to = (yield from self.exprs[0].type) if self._type is None else self._type.to
        self._type = types.Array(to, len(self.exprs))

    def compile(self, ctx: CompileContext) -> ExprCompileType:
        #  this is only run if we're not in the form of a array initialisation.
        #  check that everything is a constant
        my_type = yield from self.type
        if not all((yield from i.type) == my_type for i in self.exprs):
            raise self.error(f"Conflicting array literal types.")

        if not all(map(is_constant_expression, self.exprs)):
            raise self.error(f"Array literal terms are not constant.")

        if isinstance(my_type.to, types.Int):
            self.exprs: List[IntegerLiteral]
            bytes_ = b''.join(i.lit.to_bytes((yield from i.size)) for i in self.exprs)
            var = ctx.compiler.add_bytes(bytes_)
        elif isinstance(my_type.to, types.string_lit):
            self.exprs: List[StringLiteral]
            vars_ = [ctx.compiler.add_string(i.lit) for i in self.exprs]
            var = ctx.compiler.add_array(vars_)

        reg = ctx.get_register(var.size)
        ctx.emit(LoadVar(var, reg))
        return reg


def char_literal(ast):
    ast.val = ord(ast.chr)
    ast.size = types.const_char.size
    return IntegerLiteral(ast)
