from django import forms

from .mailing import SimpleMessageEmail


class MailForm(forms.Form):
    """A simple form to construct and send_to e-mails"""
    to = forms.EmailField()
    subject = forms.CharField(max_length=128)
    text = forms.CharField(widget=forms.Textarea)

    def send_email(self):
        """Sends the constructed e-mail"""
        if self.is_valid():
            SimpleMessageEmail(
                message=self.cleaned_data['text'],
                subject=self.cleaned_data['subject']
            ).send_to([self.cleaned_data['to']])
        else:
            raise forms.ValidationError("Form not valid yet")
