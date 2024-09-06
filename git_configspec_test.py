#! /usr/bin/env python3

import unittest
import git_configspec as uut

class GitConfigSpecTest(unittest.TestCase):

    def test_line_parser_empty_iterator(self):
        actual = uut.parse_iterable(())
        self.assertEqual(actual, [], "Should be empty")

    def test_line_parser_with_comments(self):
        actual = uut.parse_iterable(("# This shoud generate nothing",
                                     " # The same with this string."))
        self.assertEqual(actual, [], "Should be empty")

    def test_line_parser_with_whitespace(self):
        actual = uut.parse_iterable(("", " ", "  ", "   "))
        self.assertEqual(actual, [], "Should be empty")

    def test_line_parser_with_single_char_scope(self):
        actual = uut.parse_iterable(("element * HEAD",
                                     "element A foobar"))
        expected = [uut.ConfigSpecRule("element", "*", "HEAD"),
                    uut.ConfigSpecRule("element", "A", "foobar")]
        self.assertEqual(actual, expected)

    def test_line_parser_with_multiple_char_scope(self):
        actual = uut.parse_iterable(("element some/path HEAD",
                                     "element another/path foobar"))
        expected = [uut.ConfigSpecRule("element", "some/path", "HEAD"),
                    uut.ConfigSpecRule("element", "another/path", "foobar")]

        self.assertEqual(actual, expected)

    def test_line_parser_with_multiple_char_scope_with_whitespaces(self):
        actual = uut.parse_iterable(("element \"a/file with space.txt\" A",
                                     "element \"dir with/space.foo\" B"))
        expected = [uut.ConfigSpecRule("element", "a/file with space.txt", "A"),
                    uut.ConfigSpecRule("element", "dir with/space.foo", "B")]

        self.assertEqual(actual, expected)

if __name__ == "__main__":
    unittest.main()
