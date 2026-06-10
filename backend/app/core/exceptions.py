from fastapi import HTTPException, status


class AnimateAIException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AnimateAIException):
    def __init__(self, resource: str, resource_id: str = ""):
        msg = f"{resource} not found" if not resource_id else f"{resource} with id '{resource_id}' not found"
        super().__init__(msg, status_code=404)


class UnauthorizedError(AnimateAIException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)


class ForbiddenError(AnimateAIException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403)


class ValidationError(AnimateAIException):
    def __init__(self, message: str):
        super().__init__(message, status_code=422)


class ConflictError(AnimateAIException):
    def __init__(self, message: str):
        super().__init__(message, status_code=409)


class StorageError(AnimateAIException):
    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class AIGenerationError(AnimateAIException):
    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class RenderError(AnimateAIException):
    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class RateLimitError(AnimateAIException):
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, status_code=429)


def http_exception_handler(exc: AnimateAIException) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)
