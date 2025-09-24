class UserServiceError(Exception):
    def __init__(self, message: str, error_code: str = None, context: dict = None):
        self.message = message
        self.error_code = error_code
        self.context = context or {}
        super().__init__(self.message)
    def __str__(self)->str:
        base_msg = self.message
        if self.error_code:
            message = f"[{self.error_code}]{base_msg}"
        return message
    
    def __repr__(self)->str:
        return f"{self.__class__.__name__}('{self.message}', error_code='{self.error_code}')"
        
class ValidationError(UserServiceError):
    def __init__(self, message: str, field: str = None, value = None, 
                 constraints: list = None, error_code: str = None, context: dict = None):
        self.field = field
        self.value = value
        self.constraints = constraints or []
        enhanced_context = context or {}
        if field:
            enhanced_context['field'] = field
        if value is not None:
            enhanced_context['value'] = value
        if constraints:
            enhanced_context['constraints'] = constraints
        
        super().__init__(message, error_code or "VALIDATION_ERROR", enhanced_context)



class DatabaseError(UserServiceError):
    def __init__(self, message: str, operation: str = None, table: str = None, original_error: Exception = None, error_code: str = None, context: dict = None):
        self.operation = operation
        self.table = table 
        self.original_error = original_error
        enhanced_context = context or {}

        if operation:
            enhanced_context['operation'] = operation
        if table:
            enhanced_context['table'] = table
        if original_error: 
            enhanced_context['original_error'] = str(original_error)

        super().__init__(message, error_code or "DATABASE_ERROR", enhanced_context)



class UserNotFoundError(UserServiceError):
    def __init__(self, message: str = None, user_id = None, search_criteria: dict = None, error_code: str = None, context: dict = None):
        if not message:
            message = f"User not found"
            if user_id:
                message += f"User not Found"
        
        self.user_id = user_id
        self.search_criteria = search_criteria

        enchanced_context = context or {}
        if user_id:
            enchanced_context['user_id'] = user_id
        if search_criteria:
            enchanced_context['search_criteria'] = search_criteria

        super().__init__(message, error_code or "USER_NOT_FOUND", enchanced_context)


class AuthenticationError(UserServiceError):
    def __init__(self, message: str = "Authentication failed", username: str = None,
                 auth_method: str = None, error_code: str = None, context: dict = None):
        self.username = username
        self.auth_method = auth_method
        
  
        enhanced_context = context or {}
        if username:
            enhanced_context['username'] = username
        if auth_method:
            enhanced_context['auth_method'] = auth_method
        
        super().__init__(message, error_code or "AUTH_ERROR", enhanced_context)


class AuthorizationError(UserServiceError): 
    def __init__(self, message: str = "Insufficient permissions", user_id = None,
                 required_permission: str = None, operation: str = None,
                 error_code: str = None, context: dict = None):
        self.user_id = user_id
        self.required_permission = required_permission
        self.operation = operation
        
        enhanced_context = context or {}
        if user_id:
            enhanced_context['user_id'] = user_id
        if required_permission:
            enhanced_context['required_permission'] = required_permission
        if operation:
            enhanced_context['operation'] = operation
        
        super().__init__(message, error_code or "AUTHORIZATION_ERROR", enhanced_context)