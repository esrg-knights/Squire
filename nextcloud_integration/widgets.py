from django.forms.widgets import ChoiceWidget


class NextcloudFileSelectWidget(ChoiceWidget):
    template_name = "nextcloud_integration/widgets/nextcloud_file_select_widget.html"
