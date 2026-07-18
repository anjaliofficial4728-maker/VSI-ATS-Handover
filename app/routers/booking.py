# app/routers/booking.py
"""
Interview booking page (Phase 3 - Step 3).

Routes:
  GET  /api/booking/{token}        -> the HTML booking page
  POST /api/booking/{token}/book   -> book a slot (form submit)

The page is served directly by FastAPI (no separate frontend) so the
whole flow lives on one domain with no CORS or extra deploy.
"""

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse

from app.services.booking_service import BookingService

router = APIRouter(
    prefix="/api/booking",
    tags=["Interview Booking"],
)


def _page(title: str, body: str) -> str:
    """Wrap body content in a simple styled HTML shell."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #f4f6fb;
            color: #222; display: flex; justify-content: center;
            padding: 40px 16px; }}
    .card {{ background: #fff; max-width: 480px; width: 100%; border-radius: 12px;
             box-shadow: 0 4px 20px rgba(0,0,0,.08); overflow: hidden; }}
    .header {{ background: linear-gradient(135deg,#667eea,#764ba2); color: #fff;
               padding: 28px 24px; }}
    .header h1 {{ font-size: 20px; }}
    .header p {{ opacity: .9; margin-top: 6px; font-size: 14px; }}
    .content {{ padding: 24px; }}
    .content p.lead {{ margin-bottom: 18px; font-size: 15px; }}
    .slot {{ display: block; width: 100%; text-align: left; padding: 14px 16px;
             margin-bottom: 12px; border: 2px solid #e3e7f0; border-radius: 8px;
             background: #fff; font-size: 16px; cursor: pointer; }}
    .slot:hover {{ border-color: #667eea; }}
    .slot.taken {{ background: #f0f0f0; color: #aaa; cursor: not-allowed;
                   border-color: #eee; text-decoration: line-through; }}
    .banner {{ padding: 16px; border-radius: 8px; margin-bottom: 18px; font-size: 15px; }}
    .banner.ok {{ background: #e7f7ec; color: #1a7f3c; }}
    .banner.err {{ background: #fdecec; color: #c0392b; }}
    .foot {{ padding: 16px 24px; font-size: 12px; color: #888;
             border-top: 1px solid #eee; }}
    form {{ margin: 0; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>Schedule Your Interview</h1>
      <p>Virtual Solutions India</p>
    </div>
    <div class="content">{body}</div>
    <div class="foot">If you have any questions, just reply to our email.</div>
  </div>
</body>
</html>"""


@router.get("/{token}", response_class=HTMLResponse)
def booking_page(token: str):
    """Render the booking page for the candidate identified by token."""
    candidate = BookingService.get_candidate_by_token(token)
    if candidate is None:
        return HTMLResponse(
            _page("Invalid link", "<p class='lead'>This booking link is not valid. "
                  "Please use the link from your interview email.</p>"),
            status_code=404,
        )

    info = BookingService.get_availability(candidate)

    # Already booked -> show their confirmed slot, no picker.
    if info["already_booked"]:
        body = (
            f"<div class='banner ok'>You're already booked for "
            f"<strong>{info['already_booked']}</strong> on {info['date']}.</div>"
            f"<p class='lead'>Your interview slot is confirmed. "
            f"We look forward to speaking with you.</p>"
        )
        return HTMLResponse(_page("Interview booked", body))

    # Build the slot buttons.
    buttons = ""
    for slot in info["slots"]:
        if slot["available"]:
            buttons += (
                f"<form method='post' action='/api/booking/{token}/book'>"
                f"<button class='slot' type='submit' name='slot_time' "
                f"value='{slot['time']}'>{slot['time']}</button></form>"
            )
        else:
            buttons += f"<div class='slot taken'>{slot['time']} — taken</div>"

    body = (
        f"<p class='lead'>Hi {candidate['name']}, please choose an interview "
        f"time for <strong>{info['date']}</strong>:</p>{buttons}"
    )
    return HTMLResponse(_page("Choose a slot", body))


@router.post("/{token}/book", response_class=HTMLResponse)
def book(token: str, slot_time: str = Form(...)):
    """Handle a slot selection."""
    candidate = BookingService.get_candidate_by_token(token)
    if candidate is None:
        return HTMLResponse(
            _page("Invalid link", "<p class='lead'>This booking link is not valid.</p>"),
            status_code=404,
        )

    result = BookingService.book_slot(candidate, slot_time)

    if result["success"]:
        body = (
            f"<div class='banner ok'>{result['message']}</div>"
            f"<p class='lead'>Thank you, {candidate['name']}. "
            f"A confirmation email is on its way.</p>"
        )
        return HTMLResponse(_page("Interview confirmed", body))

    # Already booked earlier -> treat as a friendly confirmation, not an error.
    if result.get("already"):
        body = (
            f"<div class='banner ok'>{result['message']}</div>"
            f"<p class='lead'>Your slot is already confirmed.</p>"
        )
        return HTMLResponse(_page("Already booked", body))

    # Slot taken or other failure -> show error + link back to pick again.
    body = (
        f"<div class='banner err'>{result['message']}</div>"
        f"<p class='lead'><a href='/api/booking/{token}'>Back to available slots</a></p>"
    )
    return HTMLResponse(_page("Try again", body))