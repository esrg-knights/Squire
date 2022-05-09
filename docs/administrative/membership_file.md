# Membership file

## Members
Members instances is the de-facto member administration of the Knights. This is where current
(and possibly older) Knights are registered. In the Admin, under members you can find all members and adjust
them accordingly. The information found here contains:
- Personal contact information
- Room and card access information
- Legal information
- Notes (private for admins only)

Note that a user is the account used to access Squire and could theoretically not be a member. Similarly
a member does not necessarily have to have a user account.

## MemberYear
A memberyear is a period without strict dates that define a year for membership. Thus it is possible to have
member information stored and still accessible for older members. With the boolean is_active an year can
be marked as the one that is currently active. In this regard it is also possible to enable multiple years
at the same time. This can be useful during transitional periods such as in september where new members sign
up, but old members are not yet rejected access.

Any member that has a membership linked with an active year is treated by the site as an active member. 
When no year is active, any user with a member account that is not deregistered is treated as an active member.

Note: For clarity in administration and ordering, please write the name as YYYY - YYYY (eg 2020 - 2021)


## Memberships
A membership is the link of a member to a certain memberyear. It also contains information related to that
specific year the member is an active member. At time of writing this is solely financially focussed
- If contribution has been paid for this year
- The date on which contribution has been paid


## Active user-based membership extention
In Global Preferences the year for sign-up promotion can be set. While this is set on a year, all members 
who are not a member of that year gain a message on their home and membership page to extend their membership.
This message contains a link to a page where the user can press a button to extend their membership for that
new year. Afterwards they are guided to a new page with a thank you message at `/continue_membership/success/`.

If the board wants to customise that page, please inform the UUPS so we can adjust it as it is hardcoded.

