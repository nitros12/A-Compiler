import sys
sys.path.append("")  # lookup modules in the cwd

from wewcompiler.backend.rustvm import compile_and_pack, assemble

decl = "\n".join((
    "var a : u8 = 1;",
    "var b : [s4] = {1, 2, 3, 4};",
    # "var c : [[s4]] = {{1, 2, 3}, {4, 5, 6}};  // This doesn't function correctly yet",
    "var d : u8;"
    "fn main() {}"
))

(offsets, code), compiler = compile_and_pack(decl)

assembled = assemble.assemble_instructions(code)

print(assembled)

for i in code:
    print(i)
