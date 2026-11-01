#---------------------------------------------------------------------
# APPLICATION VERSION
#
# The single source of truth in code. The badge in readme.md is bumped in
# the same commit - markdown cannot import this, so the two are kept in step
# by hand.
#
# Migration scripts carry their own RELEASE label (the version that shipped
# the schema change) and deliberately do not read this value: a database can
# be on an older schema than the code that is running against it.
#---------------------------------------------------------------------

__version__ = '0.5.0'
