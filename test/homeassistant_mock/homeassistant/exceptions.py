class ServiceValidationError(Exception):
    def __init__(self, message="", translation_domain="", translation_key=""):
        super().__init__(message)
        self.translation_domain = translation_domain
        self.translation_key = translation_key


class HomeAssistantError(Exception):
    pass
