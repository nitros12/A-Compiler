from wewcompiler.backend.rustvm import compile_and_pack
from wewcompiler.objects.errors import CompileException

from pytest import raises
from tests.helpers import emptyfn, for_feature


def compile(inp: str):
    inp += "fn main() {}"  # add an empty main function
    return compile_and_pack(inp)


@for_feature(globals="Global variables")
def test_var_declaration_global():
    """Test variable declaration inside a global scope."""
    decl = "var a := 4;"
    compile(decl)


@for_feature(variables="Local variables")
def test_var_declaration_func():
    """Test variable declaration inside a function scope/."""
    decl = emptyfn("var a := 4;")
    compile(decl)


@for_feature(variables="Variables")
def test_var_multiple_same():
    """Test that multiple declarations of a variable with the same type is valid."""
    decl = ("var a:u4;"
            "var a:u4;")
    compile(decl)


@for_feature(variables="Variables")
def test_var_multiple_different_newscope():
    """Test that declarations of a variable with the same name as an existing
    variable of a different type in an enclosing type is valid."""
    decl = emptyfn("var a:u4;"
                   "{ var a:*u4; }")
    compile(decl)


@for_feature(variables="Variables")
def test_var_multiple_different():
    """Test that multiple declarations of a variable with different types is invalid."""
    decl = ("var a:u4;"
            "var a:s1;")
    with raises(CompileException):
        compile(decl)


@for_feature(math="Maths")
def test_types_to_binary_add_op():
    """Test types to binary add operation."""
    tests = (
        "1 + 1",
        "1 - 1",
        "1 + 1::*u4",
        "1::u2 + 1::u8",
        "1::u2 + 1::s8",
        "1::*u4 + 1",
        "1::*u4 - 1::*u4"
    )

    for i in tests:
        compile(emptyfn(i + ";"))


@for_feature(math="Maths")
def test_incompatible_types_to_binary_add_op():
    """Test incorrect types to binary add operation."""
    tests = (
        "1::*u4 + 1::*u4",
        "1::*u4 - 1::*u8"
    )

    for i in tests:
        with raises(CompileException):
            compile(emptyfn(i + ";"))


@for_feature(math="Maths")
def test_types_to_binary_mul_op():
    """Test types to binary multiply operation."""
    tests = (
        "1 * 1",
        "1 / 1"
    )

    for i in tests:
        compile(emptyfn(i + ";"))


@for_feature(math="Maths")
def test_incompatible_types_to_mul_op():
    """Test incorrect types to binary multiply operation."""
    tests = (
        "1 * 1::*u4",
        "1::*u4 * 1::*u4"
    )

    for i in tests:
        with raises(CompileException):
            compile(emptyfn(i + ";"))


@for_feature(bitwise="Bitwise")
def test_types_to_binary_shift_op():
    """Test types to binary shift operation."""
    tests = (
        "1 << 1",
        "1 >> 1"
    )

    for i in tests:
        compile(emptyfn(i + ";"))


@for_feature(bitwise="Bitwise")
def test_incompatible_types_to_shift_op():
    """Test incorrect types to binary shift operation."""
    tests = (
        "1 << 1::*u4",
        "1::*u4 >> 1::*u4"
    )

    for i in tests:
        with raises(CompileException):
            compile(emptyfn(i + ";"))


@for_feature(comparison="Relational")
def test_types_to_binary_relation_op():
    """Test types to binary relation operation."""
    tests = (
        "1 < 1",
        "1::*u1 < 1::*u1"
    )

    for i in tests:
        compile(emptyfn(i + ";"))


@for_feature(comparison="Relational")
def test_incompatible_types_to_relation_op():
    """Test incorrect types to binary relation operation."""
    tests = (
        "1 < 1::*u4",
        "1::*u4 > 1"
    )

    for i in tests:
        with raises(CompileException):
            compile(emptyfn(i + ";"))


@for_feature(bitwise="Bitwise")
def test_types_to_binary_bitwise_op():
    """Test types to binary bitwise operation."""
    tests = (
        "1 | 1",
    )

    for i in tests:
        compile(emptyfn(i + ";"))


@for_feature(bitwise="Bitwise")
def test_incompatible_types_to_bitwise_op():
    """Test incorrect types to binary bitwise operation."""
    tests = (
        "1 | 1::*u4",
        "1::*u4 | 1::*u4"
    )

    for i in tests:
        with raises(CompileException):
            compile(emptyfn(i + ";"))


@for_feature(ss_ops="Short-circuiting")
def test_types_to_binary_comparison_op():
    """Test types to binary comparison operation."""
    compile(emptyfn("1 or 1;"))


@for_feature(ss_ops="Short-circuiting")
def test_types_to_binary_comparison_op_fail():
    """Test invalid types to binary comparison operation."""
    with raises(CompileException):
        compile(emptyfn("1 or 1::*u8;"))


@for_feature(variables="Variables")
def test_var_ref_subscope():
    """Test that variables in enclosing scopes can be referenced correctly."""
    decl = ("fn test() -> u1 {"
            "    var a := 3;"
            "    {"
            "        var b := a * 2;"
            "    }"
            "}")
    compile(decl)


@for_feature(globals="Globals")
def test_var_ref_global():
    """Test that variables in enclosing scopes can be referenced correctly."""
    decl = ("var a := 3;"
            "fn test() -> u1 {"
            "    var b := a * 3;"
            "}")
    compile(decl)


@for_feature(variables="Variables")
def test_var_ref_fail():
    """Test that undeclared variables fail."""
    decl = emptyfn("a;")
    with raises(CompileException):
        compile(decl)


@for_feature(assignment="Assignment", variables="Variables")
def test_var_assn():
    """Test variable initialisation and assignment."""
    decl = emptyfn("var a := 3;"
                   "a = 4;")
    compile(decl)


@for_feature(assignment="Assignment", pointers="Pointers")
def test_ptr_assn():
    """Test pointer assignment."""
    decl = emptyfn("*(0::*u1) = 3;")
    compile(decl)


@for_feature(assignment="Assignment", variables="Variables")
def test_invalid_var_assn():
    """Test variable initialisation and invalid const assignment."""
    decl = emptyfn("var a:|u4| = 3;"
                   "a = 4;")
    with raises(CompileException):
        compile(decl)


@for_feature(functions="Functions")
def test_return_stmt():
    """Test that the return statement functions correctly."""
    decl = emptyfn("return 1;")
    compile(decl)


@for_feature(functions="Functions")
def test_incompatible_types_to_return():
    """Test that returning non-castable types is invalid."""
    decl = emptyfn("return 1::*u1;")
    with raises(CompileException):
        compile(decl)


@for_feature(assignment="Assignment")
def test_no_lvalue():
    """Test that expressions that have no lvalue are invalid in assignment and increment expressions."""
    decl = emptyfn("1 = 2;")
    with raises(CompileException):
        compile(decl)
    decl = emptyfn("1++;")
    with raises(CompileException):
        compile(decl)


@for_feature(functions="Functions")
def test_function_call():
    """Test that functions reference correctly and can be called, and that argument types work."""
    decl = ("fn a(b: u1, c: *u2) -> u2 {"
            "    return c[b];"
            "}"
            "fn afn() -> u1 {"
            "    a(1, 2::*u2);"
            "}")
    compile(decl)


@for_feature(functions="Functions")
def test_function_call_fail_count():
    """Test that an incorrect number of arguments to functions are invalid."""
    decl = ("fn a(b: u1, c: *u2) -> u2 {"
            "    return c[b];"
            "}"
            "fn afn() -> u1 {"
            "    a(1);"
            "}")
    with raises(CompileException):
        compile(decl)


@for_feature(functions="Functions")
def test_function_call_fail_type():
    """Test that an incorrect type of arguments to functions are invalid."""
    decl = ("fn a(b: u1, c: *u2) -> u2 {"
            "    return c[b];"
            "}"
            "fn afn() -> u1 {"
            "    a(0::*u1, 1);"
            "}")
    with raises(CompileException):
        compile(decl)


@for_feature(pointers="Pointers")
def test_memory_reference_op():
    """Test the memory-location-of operator."""
    decl = emptyfn("var a: u1;"
                   "return &a;",
                   "*u1")
    compile(decl)


@for_feature(if_stmt="IF Statements")
def test_if_stmt():
    """Test the functionality of an if statement."""
    decl = emptyfn("var a := 1;"
                   "var b := 2;"
                   "if a < b {"
                   "    return a;"
                   "} elif a > b {"
                   "    return b;"
                   "} elif a == b {"
                   "    return a+b;"
                   "} else {"
                   "    return (a + b) / 2;"
                   "}")
    compile(decl)


@for_feature(loop_stmt="While Loops")
def test_while_loop():
    """Test the functionality of a while loop."""
    decl = emptyfn("var a := 2;"
                   "while a {"
                   "    a = a * 2;"
                   "}")
    compile(decl)


@for_feature(variables="Variables", arrays="Arrays", number_literals="Numeric literals")
def test_array_init_num():
    """Test array initialisation."""
    decl = emptyfn("var a := {1, 2, 3};")
    compile(decl)


@for_feature(variables="Variables", arrays="Arrays", string_literals="String literals")
def test_array_init_str():
    """Test array initialisation."""
    decl = emptyfn(
        "var a: [|*u8|] = {\"string\", \"morestring\", \"lessstring\"};")
    compile(decl)


@for_feature(variables="Variables", arrays="Arrays")
def test_array_decl():
    """Tests array declaration."""
    decl = emptyfn("var a: [u1];")  # this should error, no size information
    with raises(CompileException):
        compile(decl)

    decl = emptyfn("var a: [u1@5];")
    compile(decl)

    decl = emptyfn("var a: [u1@-4];")
    with raises(CompileException):
        compile(decl)


@for_feature(variables="Variables", arrays="Arrays")
def test_array_vars_first():
    """Test array initialisation where a variable is the inspected type."""
    decl = emptyfn("var b := 1;"
                   "var a := {b, 2, 3};")
    compile(decl)


@for_feature(variables="Variables", arrays="Arrays")
def test_array_vars_second():
    """Test array initialisation where a variable isn't the inspected type."""
    decl = emptyfn("var b := 2;"
                   "var a := {1, b, 3};")
    compile(decl)


@for_feature(variables="Variables", arrays="Arrays")
def test_array_init_invalid():
    """Test array initialisation with conflicting types."""
    decl = emptyfn("var a := {1, 2::*u2};")
    with raises(CompileException):
        compile(decl)


@for_feature(variables="Variables", arrays="Arrays")
def test_array_init_expr():
    """Test that expressions in an array initialisation are valid."""
    decl = emptyfn("var b := 4;"
                   "var a := {b, b * 2};")
    compile(decl)


@for_feature(arrays="Arrays", number_literals="Numeric literals")
def test_array_lit_num():
    """Test array literals with numbers."""
    decl = emptyfn("{1, 2, 3};")
    compile(decl)


@for_feature(variables="Variables", arrays="Arrays", string_literals="String literals")
def test_array_lit_str():
    """Test array literals with strings."""
    decl = emptyfn("{\"string\", \"morestring\", \"lessstring\"};")
    compile(decl)


@for_feature(arrays="Arrays")
def test_array_lit_no_const():
    """Test that non-constant expressions work in array lits."""
    decl = emptyfn("var a := 3;"
                   "{a, a * 2};")
    compile(decl)


@for_feature(pointers="Pointers", arrays="Arrays")
def test_array_indexes_no_void():
    """Assert that it is not possible to use void pointers inside array indexing operations."""
    decl = emptyfn("(0::*())[1];")
    with raises(CompileException):
        compile(decl)


@for_feature(variables="Variables")
def test_var_decl():
    """Test various variable declarations."""
    decl = emptyfn("var a: u1;")
    compile(decl)

    decl = emptyfn("var a: u1 = 3;")
    compile(decl)

    decl = emptyfn("var a: [u1] = {1, 2, 3};")
    compile(decl)

    decl = emptyfn("var a: [u1@4] = {1, 2, 3, 4};")
    compile(decl)

    decl = emptyfn("var a: [u1@4] = {1, 2, 3};")
    compile(decl)

    decl = emptyfn("var a: [*u1] = \"test\";")
    with raises(CompileException):
        compile(decl)

    decl = emptyfn("var a: [*u1] = {1, 2};")
    with raises(CompileException):
        compile(decl)

    decl = emptyfn("var a: [u1@4] = {1, 2, 3, 4, 5};")
    with raises(CompileException):
        compile(decl)

    decl = emptyfn("var a: [u1] = 3;")
    with raises(CompileException):
        compile(decl)


@for_feature(number_literals="Numeric literals")
def test_numeric_literals():
    """Test various numeric literals."""
    decl = emptyfn("var a := 1;")
    compile(decl)
    decl = emptyfn("var a := 1/u1;")
    compile(decl)
    decl = emptyfn("var a := 1/s1;")
    compile(decl)
    decl = emptyfn("var a := 1/u8;")
    compile(decl)


@for_feature(pointers="Pointers", functions="Functions")
def test_dereference_operation():
    """Test pointer dereference operations."""
    decl = ("fn deref(ptr: *u4, offset: u2) -> u4 {"
            "    return *(ptr + offset);"
            "}")
    compile(decl)
    decl = ("fn deref(ptr: *u4, offset: u2) -> u4 {"
            "    return ptr[offset];"
            "}")
    compile(decl)


@for_feature(pointers="Pointers")
def test_void_dereference():
    """Ensure that void pointers cannot be dereferenced."""
    decl = emptyfn("*(0::*());")
    with raises(CompileException):
        compile(decl)


@for_feature(functions="Functions")
def test_function_void():
    """Test implicit void and explicit void function declarations."""
    decl = ("fn isvoid() {}")
    compile(decl)

    decl = ("fn isvoid() -> () {}")
    compile(decl)


@for_feature(functions="Functions")
def test_void_function_usage():
    """Make sure we can't use void types in expressions."""
    decl = ("fn isvoid() {}"
            "var x := isvoid() * 3;")
    with raises(CompileException):
        compile(decl)


@for_feature(modules="Modules")
def test_modules():
    """Check for functionality of modules and module namespaces."""
    decl = """
    mod test {
        fn in_test() {
            ..in_outer();
        }

        fn also_in_test() {
            in_test();
        }
    }

    fn in_outer() {
        test.in_test();
    }
    """
    compile(decl)


@for_feature(modules="Modules")
def test_modules_fail():
    """Make sure that we can't reference identifiers that are inside a module."""
    decl = """
    mod test {
        fn in_test() {
        }
    }

    fn in_outer() {
        in_test();
    }
    """
    with raises(CompileException):
        compile(decl)


@for_feature(functions="Functions")
def test_function_array_param():
    """Make sure we can't use arrays in function parameters."""
    decl = """
    fn test(x: [u8]) {
    }
    """

    with raises(CompileException):
        compile(decl)


@for_feature(functions="Functions")
def test_function_array_return():
    """Make sure we can't return arrays from functions."""
    decl = """
    fn test() -> [u1@4] {
        return {1, 2, 3, 4};
    }
    """

    with raises(CompileException):
        compile(decl)


@for_feature(functions="Functions")
def test_void_function_return():
    """Make sure we can use an empty return in void functions, and also cannot return values from a void function."""
    decl = """
    fn avoid() {
        return;
    }
    """

    compile(decl)

    decl = """
    fn avoid() {
        return 4;
    }
    """

    with raises(CompileException):
        compile(decl)


def test_unary_negate_on_unsigned():
    """Make sure we cannot use unary negate on unsigned integers."""
    decl = emptyfn(
        "var a := 1;"
        "var b := -a;"
    )

    with raises(CompileException):
        compile(decl)


@for_feature(pointers="Pointers")
def test_deref_nonptr():
    """Make sure we cannot dereference non-pointer types."""
    decl = emptyfn(
        "*(3::u8);"
    )

    with raises(CompileException):
        compile(decl)


@for_feature(functions="Functions")
def test_call_nonfn():
    """Make sure we can't call non-function types."""
    decl = emptyfn(
        "(3::u8)();"
    )

    with raises(CompileException):
        compile(decl)
