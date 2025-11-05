import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Booking as BookingSchema

app = FastAPI(title="Tirupati Balaji Ticket Booking API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Utility ----------
SLOTS: List[str] = [
    "06:00-08:00",
    "08:00-10:00",
    "10:00-12:00",
    "12:00-14:00",
    "16:00-18:00",
    "18:00-20:00",
]
SLOT_CAPACITY = 200  # capacity per slot per day


def total_tickets_booked(date: str, slot: str) -> int:
    """Return total tickets booked for a given date+slot using aggregation."""
    pipeline = [
        {"$match": {"date": date, "slot": slot}},
        {"$group": {"_id": None, "total": {"$sum": "$tickets"}}},
    ]
    try:
        result = list(db["booking"].aggregate(pipeline))
        if result:
            return int(result[0].get("total", 0))
        return 0
    except Exception:
        # Fallback to counting documents (less accurate) if aggregation fails
        return db["booking"].count_documents({"date": date, "slot": slot})


# ---------- Models ----------
class AvailabilityItem(BaseModel):
    slot: str
    capacity: int
    booked: int
    remaining: int


class BookingCreate(BookingSchema):
    pass


# ---------- Routes ----------
@app.get("/")
def read_root():
    return {"message": "Tirupati Balaji Booking Backend Running"}


@app.get("/api/temple/info")
def temple_info():
    return {
        "name": "Sri Venkateswara Swami Temple (Tirupati Balaji)",
        "location": "Tirumala, Andhra Pradesh, India",
        "darshan_types": ["Sarva Darshan", "Special Entry", "VIP"],
        "slots": SLOTS,
        "slot_capacity": SLOT_CAPACITY,
    }


@app.get("/api/availability", response_model=List[AvailabilityItem])
def get_availability(date: str = Query(..., description="YYYY-MM-DD")):
    if not date:
        raise HTTPException(status_code=400, detail="date is required (YYYY-MM-DD)")
    items: List[AvailabilityItem] = []
    for slot in SLOTS:
        booked = total_tickets_booked(date, slot)
        remaining = max(0, SLOT_CAPACITY - booked)
        items.append(
            AvailabilityItem(slot=slot, capacity=SLOT_CAPACITY, booked=booked, remaining=remaining)
        )
    return items


@app.post("/api/bookings")
def create_booking(payload: BookingCreate):
    # Basic sanity check for date format
    try:
        datetime.strptime(payload.date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    if payload.slot not in SLOTS:
        raise HTTPException(status_code=400, detail="Invalid slot selected")

    # Check availability
    booked = total_tickets_booked(payload.date, payload.slot)
    remaining = max(0, SLOT_CAPACITY - booked)
    if payload.tickets > remaining:
        raise HTTPException(
            status_code=409,
            detail=f"Only {remaining} tickets remaining for {payload.slot} on {payload.date}",
        )

    # Create booking document
    booking_id = create_document("booking", payload)
    return {"ok": True, "booking_id": booking_id}


@app.get("/api/bookings")
def list_bookings(email: Optional[str] = None):
    filter_q = {"email": email} if email else {}
    docs = get_documents("booking", filter_q)
    # Sort by created_at desc if available
    try:
        docs.sort(key=lambda d: d.get("created_at"), reverse=True)
    except Exception:
        pass
    # Convert ObjectId to string if present
    for d in docs:
        if "_id" in d:
            d["_id"] = str(d["_id"])
    return {"items": docs}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, "name") else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Env
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
