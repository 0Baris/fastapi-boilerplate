class BaseAppError(Exception):
    def __init__(self, message: str = "An error occured"):
        self.message = message
        super().__init__(self.message)


class AppValueError(BaseAppError):
    pass


class BusinessRuleError(BaseAppError):
    pass


class NotFoundError(BaseAppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message)


class ValidationError(BaseAppError):
    pass


class AuthenticationError(BaseAppError):
    pass


class AuthorizationError(BaseAppError):
    pass


class SecurityError(BaseAppError):
    pass


class AppNetworkError(BaseAppError):
    pass


class WebSocketError(AppNetworkError):
    pass


class RedisError(AppNetworkError):
    pass


class GeminiError(BaseAppError):
    pass
