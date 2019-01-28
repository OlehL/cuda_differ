from difflib import SequenceMatcher


class Differ(SequenceMatcher):

    def __init__(self, a='', b=''):
        super().__init__(None, a, b)

    def compare(self):
        """
        return tuple (id, x, y, nlen)
            id can be:
                - paint file a
                + paint file b
                *- gap file a
                *+ gap file b
                ++ detail paint file a
                -- detail paint file b
        """
        for tag, i1, i2, j1, j2 in self.get_opcodes():
            if tag != 'equal':
                # print(tag, i1, i2, j1, j2)
                for y in range(i1, i2):
                    yield ('-', 0, y, len(self.a[y]))
                for y in range(j1, j2):
                    yield ('+', 0, y, len(self.b[y]))
                i, j = i2 - i1, j2 - j1
                if i < j:
                    n = j - i
                    yield ('*-', 0, i2, n)
                if i > j:
                    n = i - j
                    yield ('*+', 0, j2, n)

                yield from self.detail_match(self.a, i1, i2, self.b, j1, j2)

    def detail_match(self, a, a1, a2, b, b1, b2):
        i = a[a1:a2]
        j = b[b1:b2]
        for tag, i1, i2, j1, j2 in \
                SequenceMatcher(None, ''.join(i), ''.join(j)).get_opcodes():
            # if tag != 'equal':
            #     print(tag, i1, i2, j1, j2)
            if tag == 'insert':
                yield from self._xy('++', j, j1, j2, b1)
            if tag == 'delete':
                yield from self._xy('--', i, i1, i2, a1)
            if tag == 'replace':
                yield from self._xy('--', i, i1, i2, a1)
                yield from self._xy('++', j, j1, j2, b1)

    def _xy(self, id, text, start, end, add):
        """
        input:
        text - list of str
        start, end - int pos in joined text

        return tuple (id, x, y, nlen)
            id can be:
                - paint file a
                + paint file b
                *- gap file a
                *+ gap file b
        """
        def get_xy(text, pos):
            "return text pos like (x, y)"
            for n, l in enumerate(text):
                ln = len(l)
                if pos <= ln:
                    return (pos, n)
                else:
                    pos -= ln

        x1, y1 = get_xy(text, start)
        x2, y2 = get_xy(text, end)
        for n in range(y1, y2+1):
            if n == y2:
                if y1 == y2:
                    yield (id+'1', x1, y2 + add, x2-x1)
                else:
                    yield (id+'2', 0, y2 + add, x2)
            elif n == y1:
                yield (id+'3', x1, y1 + add, len(text[y1])-x1)
            elif n < y2:
                yield (id+'4', 0, n + add, len(text[n]))
