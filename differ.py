from difflib import SequenceMatcher, _count_leading


class Differ:
    """
    compare function return tuples for paint text
    id can be:
          - paint deleted line in file a
              return (id, y)
          + paint added line in file b
              return (id, y)
    -* / +* paint changed line in file a / b
              return (id, y)
    -^ / +^ gap in file a / b
              return (id, y, nline)
         -- detail paint deleted symbols in file a
         ++ detail paint added symbols in file b
              return (id, y, x, nlen)
    """
    def __init__(self, a='', b=''):
        self.a = a
        self.b = b
        self.diff = SequenceMatcher(None, a, b)

    def set_seqs(self, a, b):
        self.a = a
        self.b = b
        self.diff.set_seqs(a, b)

    def compare(self, ratio=0.75):
        self.cut = ratio
        diff = SequenceMatcher(None, self.a, self.b)
        for tag, i1, i2, j1, j2 in diff.get_opcodes():
            delta = abs(i1-i2-j1+j2)
            if tag == 'delete':
                yield ('+^', j2, delta)
                for y in range(i1, i2):
                    yield ('-', y)
            elif tag == 'insert':
                yield ('-^', i2, delta)
                for y in range(j1, j2):
                    yield ('+', y)
            elif tag == 'replace':
                yield from self._fancy_replace(self.a, i1, i2, self.b, j1, j2)

    def _fancy_replace(self, a, alo, ahi, b, blo, bhi):
        best_ratio, cutoff = self.cut-0.01, self.cut
        diff = SequenceMatcher(None)
        eqi, eqj = None, None
        for j in range(blo, bhi):
            bj = b[j]
            diff.set_seq2(bj)
            for i in range(alo, ahi):
                ai = a[i]
                if ai == bj:
                    if eqi is None:
                        eqi, eqj = i, j
                    continue
                diff.set_seq1(ai)
                if diff.real_quick_ratio() > best_ratio and \
                        diff.quick_ratio() > best_ratio and \
                        diff.ratio() > best_ratio:
                    best_ratio, best_i, best_j = diff.ratio(), i, j
        if best_ratio < cutoff:
            if eqi is None:
                yield from self._plain_replace(a, alo, ahi, b, blo, bhi)
                return
            best_i, best_j, best_ratio = eqi, eqj, 1.0
        else:
            eqi = None
        yield from self._fancy_helper(a, alo, best_i, b, blo, best_j)
        aelt, belt = a[best_i], b[best_j]
        if eqi is None:
            atags = btags = ""
            diff.set_seqs(aelt, belt)
            deca, decb = 0, 0
            for tag, ai1, ai2, bj1, bj2 in diff.get_opcodes():
                la, lb = ai2 - ai1, bj2 - bj1
                if tag == 'delete':
                    deca += 1
                    yield ('--', best_i, ai1, la)
                elif tag == 'insert':
                    decb += 1
                    yield ('++', best_j, bj1, lb)
                elif tag == 'replace':
                    deca += 1
                    decb += 1
                    yield ('--', best_i, ai1, la)
                    yield ('++', best_j, bj1, lb)
            yield ('-*', best_i)
            yield ('+*', best_j)
            yield ('-y', best_i) if deca == 0 else ('-r', best_i)
            yield ('+y', best_j) if decb == 0 else ('+g', best_j)
        yield from self._fancy_helper(a, best_i+1, ahi, b, best_j+1, bhi)

    def _fancy_helper(self, a, alo, ahi, b, blo, bhi):
        if alo < ahi:
            if blo < bhi:
                yield from self._fancy_replace(a, alo, ahi, b, blo, bhi)
            else:
                if ahi-alo > 0:
                    yield ('+^', blo, ahi-alo)
                for y in range(alo, ahi):
                    yield ('-', y)
        elif blo < bhi:
            if bhi-blo > 0:
                yield ('-^', ahi, bhi-blo)
            for y in range(blo, bhi):
                    yield ('+', y)

    def _plain_replace(self, a, alo, ahi, b, blo, bhi):
        da, db = ahi-alo, bhi-blo
        if da > db:
            yield ('+^', bhi, da-db)
        elif db > da:
            yield ('-^', ahi, db-da)
        for y in range(blo, bhi):
            yield ('+', y)
        for y in range(alo, ahi):
            yield ('-', y)
