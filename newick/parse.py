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
        """Serialize the list of trees in Newick format to a string.

        :return: Newick formatted string.
        """
        return ';\n'.join([tree.newick for tree in self]) + ';'

    def dump(self, fp):
        """Serialize the list of trees in Newick format to a file pointer.

        :param fp: a file pointer.
        """
        fp.write(self.dumps())

    def write(self, fname, encoding='utf8'):
        """Serialize the list of trees in Newick format to a file.

        :param fname: a file name.
        :param encoding: the file encoding to use.
        """
        with io.open(fname, encoding=encoding, mode='w') as fp:
            self.dump(fp)


class NewickParser(object):

    RESERVED_PUNCTUATION = ':;,()'

    @staticmethod
    def _count_spaces(s, offset):
        """Count leading whitespace in a string.

        :param s: string to parse.
        :param offset: a 0-based int index into s, indicating where to start parsing.
        :return: the number of leading whitespace characters in s.
        """
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
        """Parse a node name.

        :param s: string to parse for a name.
        :param offset: a 0-based int index into s, indicating where to start parsing.
        :return: a tuple of the name to store on the node and the number of characters
        consumed from s.
        """
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
        """Parse a node comment.

        :param s: string to parse for a comment.
        :param offset: a 0-based int index into s, indicating where to start parsing.
        :return: a tuple of the comment to store on the node and the number of characters
        consumed from s.
        """
        count = self._count_spaces(s, offset)
        match = COMMENT.search(s, offset + count)
        comment = match.group(0) if match else None
        return comment, count

    def _parse_length(self, s, offset):
        """Parse a node length.

        :param s: string to parse for a length.
        :param offset: a 0-based int index into s, indicating where to start parsing.
        :return: a tuple of the float length (or None, if no length is present) to store
        on the node and the number of characters consumed from s.
        """
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
                return float(''.join(digits)), count
            else:
                return None, count

    def _parse_node(self, s, offset):
        """Parse a Newick formatted string into a `Node` object.

        :param s: Newick formatted string to parse.
        :param offset: a 0-based int index into s, indicating where to start parsing.
        :return: a tuple of the `Node` instance and the number of characters consumed from s.
        """
        count = self._count_spaces(s, offset)
        node = Node()

        if s[offset + count] == '(':
            # The node has a list of descendents.
            count += 1
            while True:
                child, subcount = self._parse(s, offset + count)
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

        node.name, subcount = self._parse_name(s, offset + count)
        count += subcount

        node.comment, subcount = self._parse_comment(s, offset + count)
        count += subcount

        node.length, subcount = self._parse_length(s, offset + count)
        count += subcount

        return node, count

    def parse(self, s):
        """Parse a Newick formatted string into a `Node` object.

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
        """Load a list of trees from a Newick formatted string.

        :param s: Newick formatted string.
        :return: A TreeList object.
        """
        return TreeList([self.parse(ss.strip())
                         for ss in s.split(';') if ss.strip()])

    def load(self, fp):
        """Load a list of trees from an open Newick formatted file.

        :param fp: open file handle.
        :return: A TreeList object.
        """
        self.loads(fp.read())

    def read(self, fname, encoding='utf8'):
        """Load a list of trees from a Newick formatted file.

        :param fname: file path.
        :param encoding: The encoding of the file contents.
        :return: A TreeList object.
        """
        with io.open(fname, encoding=encoding) as fp:
            return self.load(fp)
