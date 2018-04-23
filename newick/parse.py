# coding: utf8
"""
Functionality to read the Newick serialization format for trees.

.. seealso:: https://en.wikipedia.org/wiki/Newick_format
"""

import io
import re

from .node import Node

COMMENT = re.compile('\[[^\]]*\]')


class TreeList(list):
    def dumps(self):
        """
        Serialize a list of trees in Newick format.

        :return: Newick formatted string.
        """
        return ';\n'.join([tree.newick for tree in self]) + ';'

    def dump(self, fp):
        fp.write(self.dumps())

    def write(self, tree, fname, encoding='utf8'):
        with io.open(fname, encoding=encoding, mode='w') as fp:
            self.dump(fp)


class NewickParser(object):

    RESERVED_PUNCTUATION = ':;,()'

    @staticmethod
    def _count_spaces(s, offset):
        count = 0
        while True:
            try:
                c = s[offset]
            except IndexError:
                return count
            else:
                if c.isspace():
                    offset += 1
                    count += 1
                else:
                    return count

    def _parse_name(self, s, offset):
        count = self._count_spaces(s, offset)
        letters = []
        count = 0
        while True:
            try:
                c = s[offset + count]
            except IndexError:
                break
            else:
                if c in self.RESERVED_PUNCTUATION:
                    break
                else:
                    letters.append(c)
                    count += 1
        name = ''.join(letters).strip() or None

        return name, count

    def _parse_comment(self, s, offset):
        count = self._count_spaces(s, offset)
        match = COMMENT.search(s, offset + count)
        comment = match.group(0) if match else None
        return comment, count

    def _parse_length(self, s, offset):
        count = self._count_spaces(s, offset)

        try:
            c = s[offset + count]
        except IndexError:
            return None, count
        else:
            if c == ':':
                digits = []
                seenDot = False
                while True:
                    count += 1
                    try:
                        c = s[offset + count]
                    except IndexError:
                        break
                    else:
                        if c.isdigit():
                            digits.append(c)
                        elif c == '.' and not seenDot:
                            seenDot = True
                            digits.append(c)
                        else:
                            break
                return ''.join(digits), count
            else:
                return None, count

    def _parse_node(self, s, offset, strip_comments=False, **kw):
        """
        Parse a Newick formatted string into a `Node` object.

        :param s: Newick formatted string to parse.
        :param offset: a 0-based int index into s, indicating where to start parsing.
        :param strip_comments: Flag signaling whether to strip comments enclosed in square \
        brackets.
        :param kw: Keyword arguments are passed through to `Node.create`.
        :return: `Node` instance.
        """
        count = self._count_spaces(s, offset)
        node = Node(**kw)

        if s[offset + count] == '(':
            # The node has a list of descendents.
            count += 1
            while True:
                child, subcount = self._parse(s, offset + count,
                                              strip_comments=strip_comments, **kw)
                count += subcount
                node.add_descendant(child)

                count += self._count_spaces(s, offset + count)

                try:
                    c = s[offset + count]
                except IndexError:
                    break
                else:
                    if c == ',':
                        count += 1
                        continue
                    elif c == ')':
                        count += 1
                        break
                    else:
                        raise SyntaxError('In descendants, could not parse %r' %
                                          s[offset + count:offset + count + 100])

        name, subcount = self._parse_name(s, offset + count, node)
        count += subcount
        length, subcount = self._parse_length(s, offset + count)
        count += subcount

        node.name = name
        node.length = length

        return node, count

    def parse(self, s):
        """
        Parse a Newick formatted string into a `Node` object.

        :param s: Newick formatted string to parse.
        :return: `Node` instance.
        """

        node, count = self._parse(s, 0)
        count += self._count_spaces(s, count)

        try:
            c = s[count]
        except IndexError:
            if count != len(s):
                raise ValueError('Newick unexpected count!')
        else:
            if c == ';':
                count += 1
                count += self._count_spaces(s, count)
                if count != len(s):
                    print('%d chars unread from input: %r' % (len(s) - count, s[count:]))
            else:
                raise ValueError('Newick could not be parsed (expected ";") from %r.' % s[count:])

        return node

    def loads(self, s):
        """
        Load a list of trees from a Newick formatted string.

        :param s: Newick formatted string.
        :return: A TreeList object.
        """
        return TreeList([self.parse(ss.strip())
                         for ss in s.split(';') if ss.strip()])

    def load(self, fp):
        """
        Load a list of trees from an open Newick formatted file.

        :param fp: open file handle.
        :return: A TreeList object.
        """
        self.loads(fp.read())

    def read(self, fname, encoding='utf8'):
        """
        Load a list of trees from a Newick formatted file.

        :param fname: file path.
        :param encoding: The encoding of the file contents.
        :return: A TreeList object.
        """
        with io.open(fname, encoding=encoding) as fp:
            return self.load(fp)
