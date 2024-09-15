import os
import re
from django.conf import settings
from django.views.generic import TemplateView

from django.utils.safestring import SafeText
from django.utils.html import escape

from core.status_collective import AdminStatusViewMixin


class LogFileView(AdminStatusViewMixin, TemplateView):
    """
    A simple page that allows viewing the content of rotating log files in `/squire/logs/squire.log.<number>`
    """

    tags = {
        "&lt;[a-z0-9_\-:\s]*&gt;": "text-danger",
        "[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}(,[0-9]{3})?": "far fa-clock text-muted",
        re.escape("[debug]"): "text-secondary font-weight-bold",
        re.escape("[info]"): "text-info font-weight-bold",
        re.escape("[warning]"): "text-warning font-weight-bold",
        re.escape("[error]"): "text-danger font-weight-bold",
        re.escape("JSONParseError"): "font-weight-bold",
        re.escape("(mailcow_api)"): "far fa-envelope text-primary",
    }

    template_name = "core/admin_status/log.html"
    log_location = os.path.join(settings.BASE_DIR, "squire", "logs", "squire.log")

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._logfile1 = None
        self._logfile2 = None
        self._logfile1_name = None
        self._logfile2_name = None

        # Open both logfiles, reverse the log's lines (most recent at the top),
        #   and make sure the most recent rotating logfile appears first.
        try:
            with open(self.log_location, "r") as fl:
                data = "".join(reversed(fl.readlines()))
                # The log format is known; the first 23 chars are an ISO-timestamp
                log1_peek = data[:23]
                self._logfile1 = self._format_logfile(data)
                self._logfile1_name = os.path.join("squire", "logs", "squire.log")
        except OSError:
            pass
        try:
            with open(self.log_location + ".1", "r") as fl:
                data = "".join(reversed(fl.readlines()))
                if data[:23] > log1_peek:
                    self._logfile2 = self._logfile1
                    self._logfile1 = self._format_logfile(data)
                    self._logfile1_name = os.path.join("squire", "logs", "squire.log.1")
                    self._logfile2_name = os.path.join("squire", "logs", "squire.log")
                else:
                    self._logfile2 = self._format_logfile(data)
                    self._logfile2_name = os.path.join("squire", "logs", "squire.log.1")
        except OSError:
            pass

    def _format_logfile(self, data: str) -> SafeText:
        """Formats a logfile by adding 'syntax' highlighting to specific keywords defined in this class's `tags`."""
        text = escape(data)
        for string, classes in self.tags.items():
            text = SafeText(
                re.sub(
                    rf"(?i)(\b|(?!\w))({string})(\b|(?!\w))",
                    rf"\g<1><span class='{classes}'>\g<2></span>\g<3>",
                    text,
                )
            )
        text = SafeText(re.sub("(\r\n|\r|\n)", "<br>", text))
        return text

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["log1"] = self._logfile1
        context["log2"] = self._logfile2
        context["log1_name"] = self._logfile1_name
        context["log2_name"] = self._logfile2_name
        return context
