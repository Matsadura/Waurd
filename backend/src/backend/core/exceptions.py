class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class BadRequestException(AppException):
    def __init__(self, message: str = "Invalid request") -> None:
        super().__init__(message=message, status_code=400)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message=message, status_code=401)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Access denied") -> None:
        super().__init__(message=message, status_code=403)


class EntityNotFoundException(AppException):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message=message, status_code=404)


class UserAlreadyExistsException(AppException):
    def __init__(self, message: str = "User already exists") -> None:
        super().__init__(message=message, status_code=409)


class TooManyRequestsException(AppException):
    def __init__(self, message: str = "Too many requests") -> None:
        super().__init__(message=message, status_code=429)


class ServiceUnavailableException(AppException):
    def __init__(self, message: str = "Service unavailable") -> None:
        super().__init__(message=message, status_code=503)


class BadGatewayException(AppException):
    def __init__(self, message: str = "External service request failed") -> None:
        super().__init__(message=message, status_code=502)
