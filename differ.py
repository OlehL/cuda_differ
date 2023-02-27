from difflib import SequenceMatcher, unified_diff


A_LINE_DEL = '-'
B_LINE_ADD = '+'
A_LINE_CHANGE = '-*'
B_LINE_CHANGE = '+*'
A_GAP = '-^'
B_GAP = '+^'
A_SYMBOL_DEL = '--'
B_SYMBOL_ADD = '++'
A_DECOR_YELLOW = '-y'
A_DECOR_RED = '-r'
B_DECOR_YELLOW = '+y'
B_DECOR_GREEN = '+g'


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
        self.withdetail = True
        self.ratio = 0.75
        self.set_seqs(a, b)
        self.diffmap = []

    def set_seqs(self, a, b):
        self.a = a
        self.b = b

    def compare(self):
        self.diffmap = []
        diff = SequenceMatcher(None, self.a, self.b)
        for tag, i1, i2, j1, j2 in diff.get_opcodes():
            delta = i1-i2-j1+j2
            if tag != 'equal':
                self.diffmap.append([i1, i2, j1, j2])
            if tag == 'delete':
                yield (B_GAP, j2, abs(delta))
                for y in range(i1, i2):
                    yield (A_LINE_DEL, y)
            elif tag == 'insert':
                yield (A_GAP, i2, delta)
                for y in range(j1, j2):
                    yield (B_LINE_ADD, y)
            elif tag == 'replace':
                if self.withdetail:
                    yield from self._fancy_replace(self.a, i1, i2,
                                                   self.b, j1, j2)
                else:
                    if delta > 0:
                        yield (A_GAP, i2, delta)
                    elif delta < 0:
                        yield (B_GAP, j2, abs(delta))

                    for y in range(i1, i2):
                        yield (A_LINE_CHANGE, y)
                        yield (A_DECOR_YELLOW, y)
                    for y in range(j1, j2):
                        yield (B_LINE_CHANGE, y)
                        yield (B_DECOR_YELLOW, y)

    def unidiff(self, a, b, f1, f2, n):
        return ''.join(unified_diff(a, b, f1, f2, n=n))

    def _fancy_replace(self, a, alo, ahi, b, blo, bhi):
        best_ratio, cutoff = self.ratio-0.01, self.ratio
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
            diff.set_seqs(aelt, belt)
            deca, decb = 0, 0
            for tag, ai1, ai2, bj1, bj2 in diff.get_opcodes():
                la, lb = ai2 - ai1, bj2 - bj1
                if tag == 'delete':
                    deca += 1
                    yield (A_SYMBOL_DEL, best_i, ai1, la)
                elif tag == 'insert':
                    decb += 1
                    yield (B_SYMBOL_ADD, best_j, bj1, lb)
                elif tag == 'replace':
                    deca += 1
                    decb += 1
                    yield (A_SYMBOL_DEL, best_i, ai1, la)
                    yield (B_SYMBOL_ADD, best_j, bj1, lb)
            yield (A_LINE_CHANGE, best_i)
            yield (B_LINE_CHANGE, best_j)
            yield (A_DECOR_YELLOW, best_i) if deca == 0 else \
                  (A_DECOR_RED, best_i)
            yield (B_DECOR_YELLOW, best_j) if decb == 0 else \
                  (B_DECOR_GREEN, best_j)
        yield from self._fancy_helper(a, best_i+1, ahi, b, best_j+1, bhi)

    def _fancy_helper(self, a, alo, ahi, b, blo, bhi):
        if alo < ahi:
            if blo < bhi:
                yield from self._fancy_replace(a, alo, ahi, b, blo, bhi)
            else:
                if ahi-alo > 0:
                    yield (B_GAP, blo, ahi-alo)
                for y in range(alo, ahi):
                    yield (A_LINE_DEL, y)
        elif blo < bhi:
            if bhi-blo > 0:
                yield (A_GAP, ahi, bhi-blo)
            for y in range(blo, bhi):
                yield (B_LINE_ADD, y)

    def _plain_replace(self, a, alo, ahi, b, blo, bhi):
        da, db = ahi-alo, bhi-blo
        if da > db:
            yield (B_GAP, bhi, da-db)
        elif db > da:
            yield (A_GAP, ahi, db-da)
        for y in range(blo, bhi):
            yield (B_LINE_ADD, y)
        for y in range(alo, ahi):
            yield (A_LINE_DEL, y)
