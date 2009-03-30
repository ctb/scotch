"""
Utility functions to compare response objects from the recorder.
"""

import sets

def is_same_response(response1, response2):
    """
    Compare the status, output, and headers; return True if the same,
    return False otherwise.
    """
    if response1.status != response2.status or \
       response1.get_output() != response2.get_output():
        return False

    (same, diff12, diff21) = compare_headers(response1, response2)

    if diff12 or diff21:
        return False

    return True

def compare_headers(h1, h2, omit_date=True):
    """
    Compare the given header lists; return three dictionaries,
    containing those items that are the same, those items that are in
    h1 but not in h2, and vice versa.

    The dictionaries are indexed by (lower-case) header names, and the
    values are sets of items.

    The optional omit_date=True will omit the 'date' header from the
    comparison.

    For example,
    
    >>> h1 = [ ('A', 'x'), ('a', 'y'), ('b', 'c') ]
    >>> h2 = [ ('a', 'x'), ('A', 'z'), ('d', 'e') ]
    >>> same, d12, d21 = compare_headers(h1, h2)
    >>> same
    {'a': Set(['x'])}
    >>> d12
    {'a': Set(['y']), 'b': Set(['c'])}
    >>> d21
    {'a': Set(['z']), 'd': Set(['e'])}

    >>> h1 = [ ('date', 'x') ]
    >>> h2 = [ ('date', 'y') ]
    >>> compare_headers(h1, h2)
    ({}, {}, {})
    >>> compare_headers(h1, h2, omit_date=False)
    ({}, {'date': Set(['x'])}, {'date': Set(['y'])})
    """

    #
    # first, convert the header lists into dictionaries
    #
    
    h1_dict = {}
    for (h, v) in h1.headers:
        h = h.lower()
        if omit_date and h == 'date':
            continue
        
        l = h1_dict.get(h, sets.Set())
        l.add(v)
        h1_dict[h] = l

    h2_dict = {}
    for (h, v) in h2.headers:
        h = h.lower()
        if omit_date and h == 'date':
            continue
        
        l = h2_dict.get(h, sets.Set())
        l.add(v)
        h2_dict[h] = l

    #
    # now compare & sort into same, diff12, and diff21.
    #

    same_dict = {}
    diff12_dict = {}
    diff21_dict = {}

    # for all header names in the first dictionary,
    for (h, v1) in h1_dict.items():
        v2 = h2_dict.get(h, sets.Set())

        # calculate the intersection of the items...
        same = v1.intersection(v2)

        # ... remove items in common ...
        for item in same:
            v1.remove(item)
            v2.remove(item)

        # ...and save the intersection and both differences.
        if same:
            same_dict[h] = same
        if v1:
            diff12_dict[h] = v1
        if v2:
            diff21_dict[h] = v2

        # also remove the header from the second dictionary.
        if h2_dict.has_key(h):
            del h2_dict[h]

    # anything left over in the second dictionary is also unique.
    diff21_dict.update(h2_dict)

    # return as dicts
    return (same_dict, diff12_dict, diff21_dict)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
