import re
from typing import Optional, Union, Any
from datetime import datetime, date
from centralisedErrorHandling.ErrorHandling import ValidationError

def sanitize_string(
        value: Any, 
        max_length: int = 255,
        allow_none: bool = True,
        goofy_values_which_should_not_be_in: bool = True,
        allowed_chars: Optional[str] = None
)-> Optional[str]:
    if value is None:
        return None if allow_none else ""
    if not isinstance(value, (str, int, float)):
        if allow_none:
            return None
        raise ValidationError(f"Ye allowed nahi hai bhai change kardo isko, got {type(value)}")
    sanitized = str(value).strip()
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    if goofy_values_which_should_not_be_in:
        sanitized = re.sub(r'[<>"\';\\]', '', sanitized) 
        sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', sanitized)

    if allowed_chars and sanitized:
        if not re.match(f'^[{allowed_chars}]*$', sanitized):
            raise ValidationError(f"String contains invalid characters. Allowed: {allowed_chars}")
    
    return sanitized if sanitized else (None if allow_none else "")

def sanitize_email(email: Any) -> Optional[str]:
    if email is None:
        return None
    
    sanitized = sanitize_string(email, max_length=320, allow_none=False)
    return sanitized.lower() if sanitized else None


def sanitize_phone(phone: Any) -> Optional[str]:
    if phone is None:
        return None
    
    # Remove all non-digit characters except + and spaces
    sanitized = re.sub(r'[^\d\+\s\-\(\)]', '', str(phone).strip())
    return sanitize_string(sanitized, max_length=20, allow_none=True)


def sanitize_numeric(value: Any, allow_none: bool = True) -> Optional[Union[int, float]]:

    if value is None:
        return None if allow_none else 0
    
    if isinstance(value, (int, float)):
        return value
    
    if isinstance(value, str):
        value = value.strip()
        try:
            if '.' not in value:
                return int(value)
            return float(value)
        except (ValueError, TypeError):
            if allow_none:
                return None
            raise ValidationError(f"Invalid numeric value: {value}")
    
    raise ValidationError(f"Cannot convert {type(value)} to number")


def validate_required(value: Any, field_name: str = "Field") -> Any:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"{field_name} is required")
    return value


def validate_email(email: Any, required: bool = True) -> Optional[str]:

    if email is None:
        if required:
            raise ValidationError("Email is required")
        return None
    
    sanitized = sanitize_email(email)
    if not sanitized:
        if required:
            raise ValidationError("Email is required")
        return None
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, sanitized):
        raise ValidationError("Invalid email format")
    
    return sanitized


def validate_password(password: Any, min_length: int = 8, max_length: int = 128) -> str:

    if not password:
        raise ValidationError("Password is required")
    
    if not isinstance(password, str):
        raise ValidationError("Password must be a string")
    
    if len(password) < min_length:
        raise ValidationError(f"Password must be at least {min_length} characters long")
    
    if len(password) > max_length:
        raise ValidationError(f"Password cannot exceed {max_length} characters")
    """
    decided to keep them commented for ease of use and convinces will uncomment them though 
    """
    # Optional: Add complexity requirements
    # if not re.search(r'[A-Z]', password):
    #     raise ValidationError("Password must contain at least one uppercase letter")
    # if not re.search(r'[a-z]', password):
    #     raise ValidationError("Password must contain at least one lowercase letter")
    # if not re.search(r'\d', password):
    #     raise ValidationError("Password must contain at least one number")
    
    return password


def validate_username(username: Any, min_length: int = 3, max_length: int = 50) -> str:
    if not username:
        raise ValidationError("Username is required")
    
    sanitized = sanitize_string(username, max_length, allow_none=False)
    
    if len(sanitized) < min_length:
        raise ValidationError(f"Username must be at least {min_length} characters long")
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', sanitized):
        raise ValidationError("Username can only contain letters, numbers, underscores, and hyphens")
    
    return sanitized


def validate_phone(phone: Any, required: bool = False) -> Optional[str]:
    if phone is None:
        if required:
            raise ValidationError("Phone number is required")
        return None
    
    sanitized = sanitize_phone(phone)
    if not sanitized:
        if required:
            raise ValidationError("Phone number is required")
        return None
    phone_pattern = r'^[\+]?[\d\s\-\(\)]{7,20}$'
    if not re.match(phone_pattern, sanitized):
        raise ValidationError("Invalid phone number format")
    
    return sanitized


def validate_name(name: Any, field_name: str = "Name", required: bool = False, max_length: int = 100) -> Optional[str]:

    if name is None:
        if required:
            raise ValidationError(f"{field_name} is required")
        return None
    
    sanitized = sanitize_string(name, max_length, allow_none=not required)
    if not sanitized and required:
        raise ValidationError(f"{field_name} is required")
    
    if sanitized and not re.match(r"^[a-zA-Z\s\-'\.]+$", sanitized):
        raise ValidationError(f"{field_name} can only contain letters, spaces, hyphens, and apostrophes")
    
    return sanitized

def validate_date_string(date_str: Any, field_name: str = "Date", required: bool = False) -> Optional[date]:
    if date_str is None:
        if required:
            raise ValidationError(f"{field_name} is required")
        return None
    
    if isinstance(date_str, date):
        return date_str
    
    if not isinstance(date_str, str):
        raise ValidationError(f"{field_name} must be a string in YYYY-MM-DD format")
    
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError(f"{field_name} must be in YYYY-MM-DD format")