# Iconography
Squire uses [fontawesome.com](https://fontawesome.com/) to display icons in text that automatically align with
the text color. This is done through css classes in `<i>` or `<span>` elements. However, for continuation there are
a few guidelines:

0. Whenever anything fits better contextually, use it (e.g. register icon on activity registration button)
1. Whenever a button changes something it needs to contain the `fas fa-edit` classes
2. Whenever a button refers to an edit page, it needs to contain the `fas fa-pen` classes
3. Whenever a link goes to an external site, it needs to contain the `fas fa-external-link-alt` classes
4. Whenever a link goes to a non-edit page and no better icon is availlable, use `fas fa-arrow-right` classes
5. Whenever a link goes to a page that creates an instance, use `fas fa-plus` classes
6. Whenever a link on a form page returns to the previous page (i.e. cancel editing) use `fas fa-times`
