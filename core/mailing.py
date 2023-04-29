from mailing.mailing import Email, UserEmailMixin


class PasswordResetEmail(UserEmailMixin, Email):
    template_name = "core/password_reset"
    subject = "Squire | Password Reset"

    def __init__(self, uid, token):
        self.uid = uid
        self.token = token
        super(PasswordResetEmail, self).__init__()

    def get_context_data(self):
        context = super(PasswordResetEmail, self).get_context_data()
        context["uid"] = self.uid
        context["token"] = self.token
        return context
