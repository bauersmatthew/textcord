import sys

def remove_spaces(s):
    return ''.join([c for c in s if c != ' '])

def get_frags(s):
    for spos in range(len(s)):
        for sublen in range(1, len(s)-spos):
            yield s[spos:spos+sublen]

def score(q, o):
    score = 0
    for frag in get_frags(q):
        if frag in o:
            score += len(frag)
    return score

def fuzzyrank(query, options):
    mod_query = remove_spaces(query).lower()
    return sorted(sorted(options, key=lambda o: len(o)),
                  key=lambda option: score(
                      mod_query, remove_spaces(option).lower()),
                  reverse=True)

if __name__ == '__main__':
    print('\n'.join(fuzzyrank(sys.argv[1], sys.argv[2:])))
