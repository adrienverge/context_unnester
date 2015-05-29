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

import argparse
import os
import re

import autopep8


DESCRIPTION = """Fixes Python source code that use contextlib.nested.
This method is deprecated since Python 2.7 and incompatible with Python 3."""


def detuple(string):
    ret = []
    start = 0
    nest = 0
    for i in range(len(string)):
        char = string[i]
        if char == ')':
            nest -= 1
        elif char == '(':
            nest += 1
        elif nest == 0 and char == ',':
            ret.append(string[start:i].strip())
            start = i + 1
        if nest < 0:
            i = len(string)
            break
    i += 1
    if i > start:
        if string[start:i].strip() != '':
            ret.append(string[start:i].strip())
    return ret


class BadlyNestedCodeBlock(object):
    def __init__(self, inner, indent, keys, vals):
        self.inner = inner
        self.indent = indent
        self.keys = keys
        self.vals = vals

    def autopep8(self, source):
        """Uses autopep8 to make source code better."""

        # But before, add fake statements before to prevent autopep8 from
        # removing indents
        nest = int(len(self.indent) / 4)
        for i in range(nest):
            source = '    ' * (nest - i - 1) + 'while True:\n' + source

        source = autopep8.fix_code(source)

        # Remove fake statements
        source = '\n'.join(source.splitlines()[nest:])

        return source

    def cut_long_lines(self, source):
        newlines = []
        for line in source.splitlines():
            if len(line) > 79:
                try:
                    pos = line.find('(') + 1
                    args = detuple(line[pos:])
                    line = line[:pos] + (',\n' + ' ' * len(line[:pos])).join(args)
                except ValueError:
                    pass

                #line = re.sub(r'\((\w)', '(\n' + self.indent + r'    \1',
                #              line, 1)
                print(line)

                # try:
                #     pos = line.index('(') + 1
                #     pos1 = line.index('(', pos)
                #     pos2 = line.index(')', pos)
                #     if pos < length:
                #         newlines.append(line[:pos])
                #         newlines.append(self.indent + '    ' + line[pos:])
                #         continue
                # except ValueError:
                #     pass
            newlines.append(line)
        source = '\n'.join(newlines)

        return source

    def rewrite(self):
        """Rewrites a code block by transforming the nested() call.

        Rewriting handles three input cases:
        1. with nested(A(), B(), C()):
           with A(), B(), C():
               do_stuff()
        2. with nested(A(), B(), C()) as (a, _, c):
           with A() as a, B(), C() as c:
               do_stuff(1, a, c)
        3. with nested(A(), B(), C()) as abc:
           with A() as a, B() as b, C() as c:
               abc = (a, b, c)
               do_stuff(1, abc)
        """

        vals = detuple(self.vals)

        tuple_var = None

        keys = None
        if self.keys:
            keys = detuple(self.keys)
            assert len(keys) == len(vals) or len(keys) == 1
            if len(keys) == 1 and len(vals) > 1:
                tuple_var = keys[0]
                keys = ['v' + str(i) for i in range(1, len(vals) + 1)]
        else:
            keys = [None for i in range(1, len(vals) + 1)]

        # Check that every key is really used
        if not tuple_var:
            for i in range(len(keys)):
                if keys[i]:
                    if (keys[i][0] != '(' and
                            not re.search(r'\b%s\b' % keys[i], self.inner)):
                        # print(keys[i])
                        # print(self.inner)
                        # assert False
                        keys[i] = None

        # Clean vals
        # for i in range(len(vals)):
        #     vals[i] = re.sub(r'\s*\\?\n\s*', r' ', vals[i])

        stmts = []
        for i in range(len(vals)):
            if keys[i]:
                stmts.append(vals[i] + ' as ' + keys[i])
            else:
                stmts.append(vals[i])

        # If short, put in one line
        line = self.indent + 'with ' + ', '.join(stmts) + ':'
        if len(line) <= 79:
            lines = [line]
        # else, one line per statement
        else:
            lines = (self.indent + 'with ' +
                     ',\\\n        '.join(stmts) + ':').splitlines()

        if tuple_var:
            lines.append(self.indent + '    ' +
                         tuple_var + ' = (' + ', '.join(keys) + ')')

        block = '\n'.join(lines)

        # Use autopep8 to format code
        block = self.autopep8(block)

        # Try to split long lines
        block = self.cut_long_lines(block)

        # Use autopep8 to format code
        block = self.autopep8(block)

        return block


r = (r'(?P<indent>[^\n\S]*)with\s+(?:contextlib\.)?nested\s*'
     r'\((?P<vals>.+?)\)'
     r'(?:\s+as\s+'
     r'\(?(?P<keys>.+?)\)?)?\s*:')
p = re.compile(r, re.MULTILINE | re.DOTALL)


def unnest_source(content):
    offset = 0
    new_content = ''

    results = p.finditer(content)
    for result in results:
        start = result.start()
        end = result.end()

        indent = result.group('indent')
        inner_content = []
        for line in content[end:].splitlines()[1:]:
            if line != '' and not line.startswith(indent + ' '):
                break
            inner_content.append(line)
        inner_content = '\n'.join(inner_content)

        codeblock = BadlyNestedCodeBlock(inner_content,
                                         indent,
                                         result.group('keys'),
                                         result.group('vals'))

        # Perform the code transformation
        rewritten = codeblock.rewrite()

        new_content += content[offset:start] + rewritten
        offset = end

    new_content += content[offset:]

    return new_content


def remove_useless_import(content):
    if not re.search(r'^import contextlib$', content, re.MULTILINE):
        return content

    # Do not remove import if library used in code
    if len(re.findall(r'\bcontextlib\b', content)) > 1:
        return content

    return re.sub(r'^import contextlib\n', r'', content, 0, re.MULTILINE)


def fix_file(file):
    print(file)
    with open(file) as f:
        content = f.read()

    content = unnest_source(content)
    content = remove_useless_import(content)

    with open(file, 'w') as f:
        f.write(content)


def find_python_source_files(path):
    """Recursively finds all Python source files in the given path."""

    if os.path.isfile(path):
        return {path}

    all_files = set()
    if os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith('.py'):
                    all_files |= {os.path.join(root, file)}
        return all_files

    raise Exception('Path "%s" is neither a file or a directory.' % path)


def main():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('paths', metavar='PATH', nargs='+',
                        help='Path to source that needs to be fixed. If PATH '
                             'is a dir, apply to all Python files in it.')

    args = parser.parse_args()

    all_files = set()
    for arg in args.paths:
        all_files |= find_python_source_files(arg)

    for file in all_files:
        fix_file(file)


if __name__ == '__main__':
    main()
