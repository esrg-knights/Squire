# Membership_file module





## Accessing memberships
All request instances contain the parameter `member` which retrieves the  member of the current session.
It is possible that the current session has no member connected. If you want to restrict access to (active) members
only. Please use the `MembershipRequiredMixin` class in your view.

