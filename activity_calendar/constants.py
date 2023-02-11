##############################################################################
##                                                                          ##
##  This file contains constant values that are used throughout the module  ##
##  To prevent circular loops these are defined here                        ##
##                                                                          ##
##############################################################################


ACTIVITY_PUBLIC = "PUBLIC"
ACTIVITY_MEETING = "MEETING"

SLOT_CREATION_STAFF = "CREATION_STAFF"
SLOT_CREATION_AUTO = "CREATION_AUTO"
SLOT_CREATION_USER = "CREATION_USER"
SLOT_CREATION_NONE = "CREATION_NONE"

# The status of the activity, continuing, cancelled or removed entirely (used for recurrent events)
STATUS_NORMAL = "GO"
STATUS_CANCELLED = "STOP"
STATUS_REMOVED = "RMV"
