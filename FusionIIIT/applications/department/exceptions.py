"""
Custom exception classes for the Department module.

These exceptions improve error categorization and enable better error handling
across API views while maintaining clean separation of concerns.
"""


class DepartmentModuleException(Exception):
    """Base exception for all department module errors."""
    
    def __init__(self, message, error_code=None, http_status=400):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.http_status = http_status
        super().__init__(self.message)


class AuthorizationException(DepartmentModuleException):
    """Raised when user lacks required permissions."""
    
    def __init__(self, message="Insufficient permissions", error_code="FORBIDDEN"):
        super().__init__(message, error_code, 403)


class ValidationException(DepartmentModuleException):
    """Raised when input validation fails."""
    
    def __init__(self, message="Invalid input", errors=None, error_code="VALIDATION_ERROR"):
        self.errors = errors or {}
        super().__init__(message, error_code, 400)


class ResourceNotFound(DepartmentModuleException):
    """Raised when requested resource doesn't exist."""
    
    def __init__(self, message="Resource not found", error_code="NOT_FOUND"):
        super().__init__(message, error_code, 404)


class ConstraintViolation(DepartmentModuleException):
    """Raised when a business rule constraint is violated."""
    
    def __init__(self, message="Constraint violated", error_code="CONSTRAINT_VIOLATION"):
        super().__init__(message, error_code, 400)


class StateTransitionException(DepartmentModuleException):
    """Raised when an invalid state transition is attempted."""
    
    def __init__(self, message="Invalid state transition", error_code="INVALID_STATE_TRANSITION"):
        super().__init__(message, error_code, 400)


class DepartmentException(DepartmentModuleException):
    """Raised when department access/information is invalid."""
    
    def __init__(self, message="Invalid department", error_code="DEPARTMENT_ERROR"):
        super().__init__(message, error_code, 400)


class IntegrityException(DepartmentModuleException):
    """Raised when data integrity is compromised."""
    
    def __init__(self, message="Data integrity error", error_code="INTEGRITY_ERROR"):
        super().__init__(message, error_code, 400)


class OperationFailedException(DepartmentModuleException):
    """Raised when an operation fails unexpectedly."""
    
    def __init__(self, message="Operation failed", error_code="OPERATION_FAILED"):
        super().__init__(message, error_code, 500)
