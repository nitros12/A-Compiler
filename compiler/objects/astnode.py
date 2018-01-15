from typing import Optional

from compiler.objects.errors import CompileException

from tatsu.ast import AST
from tatsu.infos import ParseInfo


class BaseObject:
    """Base class of compilables."""

    def __init__(self, ast: Optional[AST]):
        self.context = None
        self._ast = ast
        if ast is not None:
            self._info: ParseInfo = ast.parseinfo
        else:
            self._info = None

    @property
    def identifier(self) -> str:
        info = self._info
        return f"{info.line}:{info.pos}:{info.endpos}"

    @property
    def highlight_lines(self) -> str:
        """Generate the error info line for this ast node."""
        info = self._info
        startl, endl = info.line, info.endline
        startp, endp = info.pos, info.endpos

        source = info.buffer.get_lines()
        # startp and endp are offsets from the start
        # calculate their offsets from the line they are on.
        startp = startp - sum(map(len, source[:startl])) + 1
        endp = endp - sum(map(len, source[:endl]))

        # strip newlines here (they are counted in startp and endp offsets)
        source = [i.rstrip('\n') for i in source]

        def fmtr():
            if startl == endl:
                # start and end on same line, only need simple fmt
                width = (endp - startp) - 2  # leave space for carats + off by one
                separator = '-' * width
                yield source[startl]
                yield f"{'^':>{startp}}{separator}^"
            else:
                width = (len(source[startl]) - startp)
                separator = '-' * width
                yield source[startl]
                yield f"{'^':>{startp}}{separator}"
                for i in source[startl + 1:endl]:
                    yield i
                    yield '-' * len(i)
                width = endp - 1  # - len(source[endl])
                separator = '-' * width
                if endl < len(source):  # sometimes this is one more than the total number of lines
                    yield source[endl]
                yield f"{separator}^"

        return "\n".join(fmtr())

    def make_error(self) -> Optional[str]:
        """Make an error for the ast node this object belongs to.

        if no ast node exists returns None
        """
        info = self._info
        if info is None:
            return None
        startl, endl = info.line, info.endline

        return "\n".join(((f"on line {startl}"
                           if startl == endl else
                           f"on lines {startl} to {endl}"),
                          self.highlight_lines))

    def error(self, reason: str):
        return CompileException(reason, self.make_error())