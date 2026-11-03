class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class EntityNotFoundException(AppException):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message=message, status_code=404)


class UserAlreadyExistsException(AppException):
    def __init__(self, message: str = "User already exists") -> None:
        super().__init__(message=message, status_code=409)
