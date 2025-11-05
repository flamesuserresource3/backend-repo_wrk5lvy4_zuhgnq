"""
Database Schemas for Tirupati Balaji Ticket Booking

Each Pydantic model represents a MongoDB collection.
Collection name is the lowercase of the class name (e.g., Booking -> "booking").
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional


class Booking(BaseModel):
    """
    Bookings collection schema
    Collection name: "booking"
    """
    name: str = Field(..., description="Devotee full name", min_length=2)
    email: EmailStr = Field(..., description="Contact email")
    phone: str = Field(..., description="Contact phone number", min_length=8, max_length=15)
    date: str = Field(..., description="Darshan date in YYYY-MM-DD format")
    slot: str = Field(..., description="Time slot window e.g. 06:00-08:00")
    tickets: int = Field(..., ge=1, le=10, description="Number of tickets")
    darshan_type: str = Field(
        "Sarva Darshan",
        description="Darshan type (e.g., Sarva Darshan, Special Entry, VIP)",
    )


# Example schemas (kept for reference and potential future expansion)
class User(BaseModel):
    name: str
    email: EmailStr
    address: Optional[str] = None
    age: Optional[int] = Field(None, ge=0, le=120)
    is_active: bool = True


class Product(BaseModel):
    title: str
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    category: str
    in_stock: bool = True
