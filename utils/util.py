from random import choice
import string

import cPickle

from django.core.cache import cache

def deepish_copy(to_copy):

    c = cache.get("%s" % to_copy)
    if not c:
        cache.set("%s" % to_copy, to_copy)
        c = cache.get("%s" % to_copy)
    return c 
    
    # surpringly, this is actually 1-3x faster than deepcopy.
    # will obviously destroy everything if multiple threads
    # are running, so probably not a good think to bake in
    # cache.set("%s", to_copy)
    # return cache.get("temp") 

    # cpickle is not performing any faster than regular old deepcopy
    # return cPickle.loads(cPickle.dumps(to_copy, -1))


def one_level_deepcopy(to_copy):
    out = dict().fromkeys(to_copy)
    for k,v in to_copy.iteritems():
        try:
            out[k] = v.copy()   # dicts, sets
        except AttributeError:
            try:
                out[k] = v[:]   # lists, tuples, strings, unicode
            except TypeError:
                out[k] = v      # ints 
    return out




#return a randomized alphanumerical string with a
#number of characters equal to length
def rand_key(length=12):
    built = ''.join([choice(string.letters+string.digits) for i in range(length)])
    return built



def ordinal(n):
	"""from John Machin's python-list post.  Appends an
	ordinal suffix to a number.  For example, 1 becomes 1st,
	2 becomes 2nd, etc."""
	if 10 <= n % 100 < 20:
		return str(n) + 'th'
	else:
		return  str(n) + {1 : 'st', 2 : 'nd', 3 : 'rd'}.get(n % 10, "th")



