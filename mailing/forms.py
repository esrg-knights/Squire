from django import forms

from .mailing import SimpleMessageMail


class MailForm(forms.Form):
    """ A simple form to construct and send_to e-mails """
    to = forms.EmailField()
    subject = forms.CharField(max_length=128)
    text = forms.CharField(widget=forms.Textarea)
    use_bcc = False

    # Ingore the to-field in cleaning. This way the field can be used for symbolised targets
    ignore_to_field = False

    def _clean_fields(self):
        super(MailForm, self)._clean_fields()
        if self.ignore_to_field:
            if 'to' in self.errors.keys():
                del self.errors['to']

    def send_email(self):
        """ Sends the constructed e-mail """
        if self.is_valid():
            mail = SimpleMessageMail(
                message=self.cleaned_data['text'],
                subject=self.cleaned_data['subject'])
            mail.send_to([self.cleaned_data['to']])
        else:
            raise forms.ValidationError("Form not valid yet")

    def get_to_adresses(self):
        return self.cleaned_data['to']
