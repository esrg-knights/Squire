from abc import ABC, abstractmethod

class MailcowAPIResponse(ABC):
    """ Abstract base class for Mailcow API responses """

    @classmethod
    @abstractmethod
    def from_json(cls, json: dict) -> 'MailcowAPIResponse':
        """ Create a response object from a JSON response """
        raise NotImplementedError("Subclasses should define a `from_json` method")
