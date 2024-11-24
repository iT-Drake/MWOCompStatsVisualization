DEFAULT_CACHE_TTL = 180
CACHE_TTL = DEFAULT_CACHE_TTL

def disable_caching():
    global CACHE_TTL
    CACHE_TTL = 0

def enable_caching():
    global CACHE_TTL
    CACHE_TTL = DEFAULT_CACHE_TTL
