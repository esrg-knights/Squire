from utils.testing.view_test_utils import TestMixinMixin


class TestMixinWithMemberMiddleware:
    """Mixin to be used with TestMixinMixin that imitates the member middleware"""

    def __init__(self, *args, **kwargs):
        if not isinstance(self, TestMixinMixin):
            raise TypeError(
                f"{self.__class__.__name__} uses TestMixinWithMemberMiddleware mixin but not the "
                f"TestMixinMixin. Ensure that TestMixinMixin is in the inheritencelist to make this work"
            )
        super(TestMixinWithMemberMiddleware, self).__init__(*args, **kwargs)

    def _imitiate_request_middleware(self, request, **kwargs):
        super(TestMixinWithMemberMiddleware, self)._imitiate_request_middleware(request, **kwargs)
        if hasattr(request.user, "member"):
            request.member = request.user.member
