from css_inline import CSSInliner


__all__ = ["MailInliner"]

"""
Contains the logic for inlining files

"""


class MailInliner:
    """ A shell for the inliner library used """

    @classmethod
    def inline(cls, layout):
        """
        Inlines the css styling options defined in the head
        :param layout: The html layout that needs to be inlined
        :return:
        """
        return CSSInliner().inline(layout)
