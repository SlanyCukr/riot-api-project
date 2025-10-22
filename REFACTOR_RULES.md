8. Schema-Driven Development
Make schemas your source of truth:

python# backend/core/schemas/base.py
"""
Base schemas with rich documentation.
These drive both API contracts and database models.
"""

from pydantic import BaseModel, Field, ConfigDict

class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""
    created_at: datetime = Field(
        description="When this record was created"
    )
    updated_at: datetime = Field(
        description="When this record was last modified"
    )

class UserBase(BaseModel):
    """
    Base user schema - shared fields.

    Used by:
    - UserCreate (input)
    - UserUpdate (input)
    - UserResponse (output)

    Database: maps to users table
    """
    email: str = Field(
        description="User email (unique identifier)",
        examples=["user@example.com"]
    )
    full_name: str | None = Field(
        None,
        description="User's full name (optional)"
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "full_name": "Jane Doe"
            }
        }
    )


### 5. **Feature-Based Organization**

Structure by domain, not by technical layer:
```
backend/
  features/
    auth/
      __init__.py           # Public API exports
      router.py             # FastAPI routes
      service.py            # Business logic
      models.py             # SQLAlchemy models
      schemas.py            # Pydantic schemas
      tests/
        test_auth_flow.py
      README.md             # Feature documentation

    users/
      ... (same structure)

    projects/
      ... (same structure)

frontend/
  features/
    auth/
      components/
      hooks/
      utils/
      index.ts              # Public exports
    users/
    projects/
