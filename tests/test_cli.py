from __future__ import annotations

import argparse
import io
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from kenshi_save_edit.cli import (
    SaveEditError,
    build_parser,
    build_stat_request,
    parse_relation_assignment,
    parse_stat_assignment,
    resolve_input_save,
    resolve_output_save,
)


class ParserTests(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = build_parser()

    def parse(self, *arguments: str) -> argparse.Namespace:
        return self.parser.parse_args(arguments)

    def test_list_requires_input_save(self) -> None:
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.parse("list")

    def test_relations_requires_input_save(self) -> None:
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.parse("relations")

    def test_set_requires_both_save_paths(self) -> None:
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.parse("set", "input")

    def test_set_accepts_positional_paths(self) -> None:
        arguments = self.parse(
            "set",
            "/saves/input",
            "/saves/output",
            "--money",
            "3000",
        )
        self.assertEqual(arguments.input_save, "/saves/input")
        self.assertEqual(arguments.output_save, "/saves/output")
        self.assertEqual(arguments.money, 3000)

    def test_character_selectors_are_mutually_exclusive(self) -> None:
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.parse(
                "set",
                "input",
                "output",
                "--character",
                "Beep",
                "--platoon",
                "Nameless_0",
                "--heal",
            )

    def test_legacy_save_flag_is_rejected(self) -> None:
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.parse("list", "--save", "quicksave")

    def test_reputation_alias_uses_relation_destination(self) -> None:
        arguments = self.parse(
            "set",
            "input",
            "output",
            "--reputation",
            "Tech Hunters=10",
        )
        self.assertEqual(arguments.relation, [("Tech Hunters", 10.0)])


class ValueParserTests(unittest.TestCase):
    def test_exact_and_minimum_stat_modes_conflict(self) -> None:
        with self.assertRaisesRegex(SaveEditError, "cannot be combined"):
            build_stat_request(
                [("strength", 80.0)],
                None,
                [("dexterity", 80.0)],
                None,
            )

    def test_relation_range(self) -> None:
        self.assertEqual(
            parse_relation_assignment("Holy Nation=-100"),
            ("Holy Nation", -100.0),
        )
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_relation_assignment("Holy Nation=100.1")

    def test_stat_alias_and_range(self) -> None:
        self.assertEqual(
            parse_stat_assignment("toughness=98"),
            ("toughness2", 98.0),
        )
        with self.assertRaises(argparse.ArgumentTypeError):
            parse_stat_assignment("strength=101")


class SavePathTests(unittest.TestCase):
    def test_resolve_input_and_new_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_save = root / "input save"
            input_save.mkdir()
            resolved_input = resolve_input_save(str(input_save))
            resolved_output = resolve_output_save(
                str(root / "output save"),
                resolved_input,
            )
            self.assertEqual(resolved_input, input_save.resolve())
            self.assertEqual(resolved_output, (root / "output save").resolve())

    def test_missing_input_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(SaveEditError, "input save does not exist"):
                resolve_input_save(str(Path(temporary) / "missing"))

    def test_existing_output_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_save = root / "input"
            output_save = root / "output"
            input_save.mkdir()
            output_save.mkdir()
            with self.assertRaisesRegex(SaveEditError, "refusing to overwrite"):
                resolve_output_save(str(output_save), input_save.resolve())

    def test_same_output_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            input_save = Path(temporary).resolve()
            with self.assertRaisesRegex(SaveEditError, "must be different"):
                resolve_output_save(str(input_save), input_save)

    def test_nested_output_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            input_save = Path(temporary).resolve()
            with self.assertRaisesRegex(SaveEditError, "cannot be inside"):
                resolve_output_save(str(input_save / "edited"), input_save)

    def test_missing_output_parent_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_save = root / "input"
            input_save.mkdir()
            with self.assertRaisesRegex(SaveEditError, "parent does not exist"):
                resolve_output_save(
                    str(root / "missing" / "output"),
                    input_save.resolve(),
                )


if __name__ == "__main__":
    unittest.main()
