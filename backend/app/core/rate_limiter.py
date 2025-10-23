"""Rate limiting configuration for the application."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Create rate limiter instance
# key_func determines the key for rate limiting (by default, uses client IP)
limiter = Limiter(key_func=get_remote_address)
