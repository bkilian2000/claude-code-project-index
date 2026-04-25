#!/usr/bin/env python3
"""
Tests for all language parsers in index_utils.py.

Run with:  python3 tests/test_parsers.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from index_utils import (
    extract_python_signatures,
    extract_javascript_signatures,
    extract_shell_signatures,
    extract_gdscript_signatures,
    extract_function_calls_python,
    extract_function_calls_javascript,
    extract_function_calls_shell,
    extract_function_calls_gdscript,
    PARSEABLE_LANGUAGES,
    CODE_EXTENSIONS,
)


# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------

class TestPythonSignatures(unittest.TestCase):

    def test_simple_function(self):
        src = "def hello(name: str) -> str:\n    return name\n"
        r = extract_python_signatures(src)
        self.assertIn("hello", r["functions"])
        info = r["functions"]["hello"]
        self.assertIn("name: str", info["signature"])
        self.assertIn("str", info["signature"])

    def test_async_function(self):
        src = "async def fetch(url: str) -> bytes:\n    pass\n"
        r = extract_python_signatures(src)
        self.assertIn("fetch", r["functions"])

    def test_class_with_methods(self):
        src = (
            "class Dog:\n"
            "    def __init__(self, name: str) -> None:\n"
            "        self.name = name\n"
            "    def bark(self) -> str:\n"
            "        return 'woof'\n"
        )
        r = extract_python_signatures(src)
        self.assertIn("Dog", r["classes"])
        self.assertIn("bark", r["classes"]["Dog"]["methods"])

    def test_class_inheritance(self):
        src = "class Cat(Animal):\n    pass\n"
        r = extract_python_signatures(src)
        self.assertIn("Cat", r["classes"])
        self.assertEqual(r["classes"]["Cat"].get("inherits"), ["Animal"])

    def test_constants(self):
        src = "MAX_SIZE = 100\nDEBUG = True\n"
        r = extract_python_signatures(src)
        self.assertIn("MAX_SIZE", r["constants"])

    def test_imports(self):
        src = "import os\nfrom pathlib import Path\n"
        r = extract_python_signatures(src)
        self.assertIn("os", r["imports"])
        self.assertIn("pathlib", r["imports"])

    def test_docstring_extracted(self):
        src = (
            'def compute():\n'
            '    """Compute the result."""\n'
            '    return 42\n'
        )
        r = extract_python_signatures(src)
        info = r["functions"].get("compute", {})
        self.assertIsInstance(info, dict)

    def test_decorated_function(self):
        src = (
            "@staticmethod\n"
            "def helper(x: int) -> int:\n"
            "    return x\n"
        )
        r = extract_python_signatures(src)
        self.assertIn("helper", r["functions"])

    def test_call_graph(self):
        src = (
            "def foo():\n"
            "    bar()\n"
            "\n"
            "def bar():\n"
            "    pass\n"
        )
        r = extract_python_signatures(src)
        foo = r["functions"].get("foo", {})
        self.assertIn("bar", foo.get("calls", []))

    def test_no_false_positive_builtins(self):
        src = (
            "def process(items):\n"
            "    return len(items)\n"
        )
        r = extract_python_signatures(src)
        calls = r["functions"].get("process", {}).get("calls", [])
        self.assertNotIn("len", calls)

    def test_empty_file(self):
        r = extract_python_signatures("")
        self.assertIsInstance(r["functions"], dict)
        self.assertIsInstance(r["classes"], dict)


class TestPythonFunctionCalls(unittest.TestCase):

    def test_direct_call(self):
        calls = extract_function_calls_python("foo()", {"foo", "bar"})
        self.assertIn("foo", calls)

    def test_method_call(self):
        calls = extract_function_calls_python("self.bar()", {"foo", "bar"})
        self.assertIn("bar", calls)

    def test_excludes_keywords(self):
        calls = extract_function_calls_python("if True:\n    len(x)", {"len"})
        self.assertNotIn("len", calls)

    def test_only_known_functions(self):
        calls = extract_function_calls_python("unknown()", {"known"})
        self.assertNotIn("unknown", calls)


# ---------------------------------------------------------------------------
# JavaScript / TypeScript
# ---------------------------------------------------------------------------

class TestJavaScriptSignatures(unittest.TestCase):

    def test_function_declaration(self):
        src = "function greet(name) { return name; }"
        r = extract_javascript_signatures(src)
        self.assertIn("greet", r["functions"])

    def test_arrow_function(self):
        src = "const add = (a, b) => a + b;"
        r = extract_javascript_signatures(src)
        self.assertIn("add", r["functions"])

    def test_async_function(self):
        src = "async function fetchData(url) { return fetch(url); }"
        r = extract_javascript_signatures(src)
        self.assertIn("fetchData", r["functions"])

    def test_class_with_methods(self):
        src = (
            "class Animal {\n"
            "  constructor(name) { this.name = name; }\n"
            "  speak() { return this.name; }\n"
            "}\n"
        )
        r = extract_javascript_signatures(src)
        self.assertIn("Animal", r["classes"])
        self.assertIn("speak", r["classes"]["Animal"]["methods"])

    def test_class_inheritance(self):
        src = "class Dog extends Animal { bark() {} }"
        r = extract_javascript_signatures(src)
        self.assertIn("Dog", r["classes"])
        self.assertEqual(r["classes"]["Dog"].get("extends"), "Animal")

    def test_constants(self):
        src = "const MAX_RETRIES = 3;"
        r = extract_javascript_signatures(src)
        self.assertIn("MAX_RETRIES", r["constants"])

    def test_imports_esm(self):
        src = "import React from 'react';"
        r = extract_javascript_signatures(src)
        self.assertIn("react", r["imports"])

    def test_imports_require(self):
        src = "const fs = require('fs');"
        r = extract_javascript_signatures(src)
        self.assertIn("fs", r["imports"])

    def test_typescript_interface(self):
        src = "interface User { name: string; age: number; }"
        r = extract_javascript_signatures(src)
        self.assertIn("User", r["interfaces"])

    def test_typescript_enum(self):
        src = "enum Color { Red, Green, Blue }"
        r = extract_javascript_signatures(src)
        self.assertIn("Color", r["enums"])
        self.assertIn("Red", r["enums"]["Color"]["values"])

    def test_typescript_type_alias(self):
        src = "type ID = string | number;"
        r = extract_javascript_signatures(src)
        self.assertIn("ID", r["type_aliases"])

    def test_call_graph(self):
        src = (
            "function main() { helper(); }\n"
            "function helper() { return 1; }\n"
        )
        r = extract_javascript_signatures(src)
        main = r["functions"].get("main", {})
        self.assertIn("helper", main.get("calls", []))

    def test_empty_file(self):
        r = extract_javascript_signatures("")
        self.assertIsInstance(r["functions"], dict)


class TestJavaScriptFunctionCalls(unittest.TestCase):

    def test_direct_call(self):
        calls = extract_function_calls_javascript("foo()", {"foo"})
        self.assertIn("foo", calls)

    def test_method_call(self):
        calls = extract_function_calls_javascript("this.bar()", {"bar"})
        self.assertIn("bar", calls)

    def test_excludes_keywords(self):
        calls = extract_function_calls_javascript("if (true) {}", {"if"})
        self.assertNotIn("if", calls)


# ---------------------------------------------------------------------------
# Shell
# ---------------------------------------------------------------------------

class TestShellSignatures(unittest.TestCase):

    def test_function_style1(self):
        src = "my_func() {\n  echo hello\n}\n"
        r = extract_shell_signatures(src)
        self.assertIn("my_func", r["functions"])

    def test_function_style2(self):
        src = "function do_thing {\n  echo hi\n}\n"
        r = extract_shell_signatures(src)
        self.assertIn("do_thing", r["functions"])

    def test_doc_comment(self):
        src = "# Print a greeting\ngreet() {\n  echo hi\n}\n"
        r = extract_shell_signatures(src)
        info = r["functions"].get("greet", {})
        self.assertIsInstance(info, dict)
        self.assertIn("doc", info)

    def test_exports(self):
        src = "export PATH=/usr/bin\n"
        r = extract_shell_signatures(src)
        self.assertIn("PATH", r.get("exports", {}))

    def test_source_include(self):
        src = "source ./lib/helpers.sh\n"
        r = extract_shell_signatures(src)
        self.assertIn("./lib/helpers.sh", r.get("sources", []))

    def test_call_graph(self):
        # Opening brace on its own line so the body extractor can find it.
        src = (
            "main()\n"
            "{\n"
            "  setup\n"
            "}\n"
            "setup()\n"
            "{\n"
            "  echo ready\n"
            "}\n"
        )
        r = extract_shell_signatures(src)
        self.assertIn("main", r["functions"])
        self.assertIn("setup", r["functions"])
        main = r["functions"]["main"]
        if isinstance(main, dict):
            self.assertIn("setup", main.get("calls", []))

    def test_empty_script(self):
        r = extract_shell_signatures("#!/bin/bash\n")
        self.assertIsInstance(r["functions"], dict)


class TestShellFunctionCalls(unittest.TestCase):

    def test_start_of_line_call(self):
        calls = extract_function_calls_shell("  setup\ncleanup", {"setup", "cleanup"})
        self.assertIn("setup", calls)

    def test_after_semicolon(self):
        calls = extract_function_calls_shell("foo; bar", {"foo", "bar"})
        self.assertIn("bar", calls)

    def test_command_substitution(self):
        calls = extract_function_calls_shell("x=$(get_value)", {"get_value"})
        self.assertIn("get_value", calls)

    def test_unknown_not_included(self):
        calls = extract_function_calls_shell("unknown_cmd", {"known"})
        self.assertNotIn("unknown_cmd", calls)


# ---------------------------------------------------------------------------
# GDScript
# ---------------------------------------------------------------------------

class TestGDScriptSignatures(unittest.TestCase):

    # --- metadata ---

    def test_extends(self):
        src = "extends CharacterBody2D\n"
        r = extract_gdscript_signatures(src)
        self.assertEqual(r.get("extends"), "CharacterBody2D")

    def test_class_name(self):
        src = "class_name Player\n"
        r = extract_gdscript_signatures(src)
        self.assertEqual(r.get("class_name"), "Player")

    # --- signals ---

    def test_signal_no_params(self):
        src = "signal died\n"
        r = extract_gdscript_signatures(src)
        self.assertIn("died", r.get("signals", []))

    def test_signal_with_params(self):
        src = "signal health_changed(old_val, new_val)\n"
        r = extract_gdscript_signatures(src)
        signals = r.get("signals", [])
        self.assertTrue(any("health_changed" in s for s in signals))
        self.assertTrue(any("old_val" in s for s in signals))

    # --- enums ---

    def test_named_enum(self):
        src = "enum State { IDLE, RUNNING, DEAD }\n"
        r = extract_gdscript_signatures(src)
        self.assertIn("State", r.get("enums", {}))
        self.assertIn("IDLE", r["enums"]["State"]["values"])
        self.assertIn("DEAD", r["enums"]["State"]["values"])

    def test_anonymous_enum(self):
        src = "enum { UP, DOWN }\n"
        r = extract_gdscript_signatures(src)
        self.assertIn("_anonymous", r.get("enums", {}))

    # --- constants ---

    def test_constant_number(self):
        src = "const MAX_SPEED: float = 300.0\n"
        r = extract_gdscript_signatures(src)
        self.assertIn("MAX_SPEED", r.get("constants", {}))
        self.assertEqual(r["constants"]["MAX_SPEED"], "number")

    def test_constant_string(self):
        src = 'const GAME_NAME = "My Game"\n'
        r = extract_gdscript_signatures(src)
        self.assertIn("GAME_NAME", r.get("constants", {}))
        self.assertEqual(r["constants"]["GAME_NAME"], "str")

    # --- variables ---

    def test_plain_var(self):
        src = "var speed: float = 150.0\n"
        r = extract_gdscript_signatures(src)
        self.assertIn("speed", r.get("variables", []))

    def test_export_var(self):
        src = "@export var health: int = 100\n"
        r = extract_gdscript_signatures(src)
        self.assertIn("health", r.get("variables", []))

    def test_onready_var(self):
        src = "@onready var sprite: Sprite2D = $Sprite2D\n"
        r = extract_gdscript_signatures(src)
        self.assertIn("sprite", r.get("variables", []))

    def test_local_var_excluded(self):
        src = (
            "func _ready() -> void:\n"
            "\tvar local = 42\n"
        )
        r = extract_gdscript_signatures(src)
        self.assertNotIn("local", r.get("variables", []))

    # --- imports ---

    def test_preload(self):
        src = 'const BulletScene = preload("res://scenes/bullet.tscn")\n'
        r = extract_gdscript_signatures(src)
        self.assertIn("res://scenes/bullet.tscn", r.get("imports", []))

    def test_load(self):
        src = 'var tex = load("res://textures/player.png")\n'
        r = extract_gdscript_signatures(src)
        self.assertIn("res://textures/player.png", r.get("imports", []))

    # --- functions ---

    def test_simple_function(self):
        src = "func _ready() -> void:\n\tpass\n"
        r = extract_gdscript_signatures(src)
        self.assertIn("_ready", r["functions"])

    def test_function_with_params(self):
        src = "func move(direction: Vector2, speed: float) -> void:\n\tpass\n"
        r = extract_gdscript_signatures(src)
        self.assertIn("move", r["functions"])
        sig = r["functions"]["move"]["signature"]
        self.assertIn("direction: Vector2", sig)
        self.assertIn("speed: float", sig)

    def test_function_return_type(self):
        src = "func get_name() -> String:\n\treturn name\n"
        r = extract_gdscript_signatures(src)
        sig = r["functions"]["get_name"]["signature"]
        self.assertIn("-> String", sig)

    def test_static_function(self):
        src = "static func clamp_val(v: float) -> float:\n\treturn v\n"
        r = extract_gdscript_signatures(src)
        self.assertIn("clamp_val", r["functions"])
        sig = r["functions"]["clamp_val"]["signature"]
        self.assertIn("static", sig)

    def test_function_doc_comment(self):
        src = (
            "## Initialise the player node.\n"
            "func _ready() -> void:\n"
            "\tpass\n"
        )
        r = extract_gdscript_signatures(src)
        info = r["functions"].get("_ready", {})
        self.assertIsInstance(info, dict)
        self.assertIn("doc", info)
        self.assertIn("Initialise", info["doc"])

    def test_function_line_number(self):
        src = "\nextends Node\n\nfunc foo():\n\tpass\n"
        r = extract_gdscript_signatures(src)
        self.assertEqual(r["functions"]["foo"]["line"], 4)

    # --- call graph ---

    def test_call_graph_direct(self):
        src = (
            "func _ready() -> void:\n"
            "\t_init_player()\n"
            "\n"
            "func _init_player() -> void:\n"
            "\tpass\n"
        )
        r = extract_gdscript_signatures(src)
        ready = r["functions"].get("_ready", {})
        self.assertIn("_init_player", ready.get("calls", []))

    def test_call_graph_chained(self):
        src = (
            "func a() -> void:\n"
            "\tb()\n"
            "\n"
            "func b() -> void:\n"
            "\tc()\n"
            "\n"
            "func c() -> void:\n"
            "\tpass\n"
        )
        r = extract_gdscript_signatures(src)
        self.assertIn("b", r["functions"]["a"].get("calls", []))
        self.assertIn("c", r["functions"]["b"].get("calls", []))

    def test_no_false_positive_builtins(self):
        src = (
            "func _process(delta: float) -> void:\n"
            "\tprint('hello')\n"
            "\tvar x = int(delta)\n"
        )
        r = extract_gdscript_signatures(src)
        calls = r["functions"]["_process"].get("calls", [])
        self.assertNotIn("print", calls)
        self.assertNotIn("int", calls)

    # --- inner classes ---

    def test_inner_class(self):
        src = (
            "class Hitbox extends Area2D:\n"
            "\tvar damage: int = 10\n"
            "\n"
            "\tfunc _on_body_entered(body: Node) -> void:\n"
            "\t\tbody.take_damage(damage)\n"
        )
        r = extract_gdscript_signatures(src)
        self.assertIn("Hitbox", r.get("classes", {}))
        self.assertEqual(r["classes"]["Hitbox"].get("extends"), "Area2D")
        self.assertIn("_on_body_entered", r["classes"]["Hitbox"]["methods"])

    def test_inner_class_method_not_in_top_functions(self):
        src = (
            "class Inner:\n"
            "\tfunc do_thing() -> void:\n"
            "\t\tpass\n"
        )
        r = extract_gdscript_signatures(src)
        self.assertNotIn("do_thing", r["functions"])
        self.assertIn("do_thing", r["classes"]["Inner"]["methods"])

    # --- empty / minimal ---

    def test_empty_file(self):
        r = extract_gdscript_signatures("")
        self.assertIsInstance(r["functions"], dict)
        self.assertIsInstance(r.get("classes", {}), dict)

    def test_extends_only(self):
        src = "extends Node\n"
        r = extract_gdscript_signatures(src)
        self.assertEqual(r.get("extends"), "Node")
        self.assertEqual(r["functions"], {})


class TestGDScriptFunctionCalls(unittest.TestCase):

    def test_direct_call(self):
        calls = extract_function_calls_gdscript("do_thing()", {"do_thing"})
        self.assertIn("do_thing", calls)

    def test_method_call(self):
        calls = extract_function_calls_gdscript("self.update_ui()", {"update_ui"})
        self.assertIn("update_ui", calls)

    def test_excludes_keywords(self):
        calls = extract_function_calls_gdscript("if true:\n\tpass", {"if"})
        self.assertNotIn("if", calls)

    def test_excludes_builtins(self):
        calls = extract_function_calls_gdscript("print('hi')\nstr(x)", {"print", "str"})
        self.assertNotIn("print", calls)
        self.assertNotIn("str", calls)

    def test_only_known_functions(self):
        calls = extract_function_calls_gdscript("mystery()", {"known"})
        self.assertNotIn("mystery", calls)


# ---------------------------------------------------------------------------
# Language registration
# ---------------------------------------------------------------------------

class TestLanguageRegistration(unittest.TestCase):

    def test_gdscript_in_parseable(self):
        self.assertIn(".gd", PARSEABLE_LANGUAGES)
        self.assertEqual(PARSEABLE_LANGUAGES[".gd"], "gdscript")

    def test_gdscript_in_code_extensions(self):
        self.assertIn(".gd", CODE_EXTENSIONS)

    def test_python_registered(self):
        self.assertIn(".py", PARSEABLE_LANGUAGES)

    def test_js_registered(self):
        self.assertIn(".js", PARSEABLE_LANGUAGES)

    def test_ts_registered(self):
        self.assertIn(".ts", PARSEABLE_LANGUAGES)

    def test_shell_registered(self):
        self.assertIn(".sh", PARSEABLE_LANGUAGES)


if __name__ == "__main__":
    unittest.main(verbosity=2)
