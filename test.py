#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright (C) 2015 Adrien Vergé

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

import unittest

import context_unnester


class ContextUnnesterTestCase(unittest.TestCase):
    def _test_unwrap_tuple(self, input, output):
        res = context_unnester.unwrap_tuple(input)
        self.assertEqual(res, output)

    def test_unwrap_tuple(self):
        input = '   with mock(x, "string", call(), 42) as m:'
        output = ('   with mock(',
                  ['x', '"string"', 'call()', '42'],
                  ') as m:')
        self._test_unwrap_tuple(input, output)

        input = '(x, "string", call(), 42)'
        output = ('(',
                  ['x', '"string"', 'call()', '42'],
                  ')')
        self._test_unwrap_tuple(input, output)

        input = 'func(x, a(b(c(1, d(e(), f(2, v)), x))), z())'
        output = ('func(',
                  ['x', 'a(b(c(1, d(e(), f(2, v)), x)))', 'z()'],
                  ')')
        self._test_unwrap_tuple(input, output)

        input = '(x, "string", \'(other string\', 42)'
        output = ('(',
                  ['x', '"string"', "'(other string'", '42'],
                  ')')
        self._test_unwrap_tuple(input, output)

        input = '(x, "st\\", ri)ng", 42)'
        output = ('(',
                  ['x', '"st\\", ri)ng"', '42'],
                  ')')
        self._test_unwrap_tuple(input, output)

        input = 'test_end(1, 2, 3, )'
        output = ('test_end(',
                  ['1', '2', '3'],
                  ')')
        self._test_unwrap_tuple(input, output)

        input = "'no_parentheses' as hey:"
        output = ("'no_parentheses' as hey:",
                  [],
                  '')
        self._test_unwrap_tuple(input, output)

        input = "'make_port_dict') as mpd_block:"
        output = ("'make_port_dict') as mpd_block:",
                  [],
                  '')
        self._test_unwrap_tuple(input, output)

    def test_cut_long_line(self):
        input = ('    self.metering_label_abcdefgh_abcdefgh_abcdefgh('
                 'name, description, '
                 'my_long_function(truc, tric, trec, trek, trook, troc, trac))'
                 ' as metering_label:')
        output = ('    self.metering_label_abcdefgh_abcdefgh_abcdefgh(\n'
                  '        name,\n'
                  '        description,\n'
                  '        my_long_function(truc,\n'
                  '                         tric,\n'
                  '                         trec,\n'
                  '                         trek,\n'
                  '                         trook,\n'
                  '                         troc,\n'
                  '                         trac)) as metering_label:')
        res = context_unnester.cut_long_line(input)
        self.assertEqual(res, output)

    def test_cut_long_line2(self):
        input = ("                    'neutron.plugins.ml2.plugin.Ml2Plugin."
                 "_make_port_dict') as mpd_block:")
        output = input
        res = context_unnester.cut_long_line(input)
        self.assertEqual(res, output)

    def test_unnest_source(self):
        input = """
        with contextlib.nested(
                self.metering_label(name, description),
                self.metering_label(name, description)) as metering_label:
            self._test_list_resources('metering-label', metering_label)
"""
        output = """
        with self.metering_label(name, description) as v1,\\
                self.metering_label(name, description) as v2:
            metering_label = (v1, v2)
            self._test_list_resources('metering-label', metering_label)
"""
        res = context_unnester.unnest_source(input)
        self.assertEqual(res, output)
