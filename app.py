"""
Proposal PDF Service
=====================
A tiny HTTP wrapper around generate_proposal.py so Make.com (which
can't execute Python directly) can call it as a webhook step.

ENDPOINT
--------
POST /generate-proposal
Body (JSON), keys match the Quote Builder columns 1:1:

{
  "proposal_ref": "WE.9056",
  "prepared_by": "Katherine Bulaon",
  "prepared_by_title": "Client Relationship Manager",
  "date_prepared": "30 June 2026",
  "quote_valid_days": 28,
  "client_name": "Sarah Prentice",
  "organisation": "Blue Apple Contract Catering",
  "telephone": "020 3452 2222",
  "email": "sarah@blue-apple.co.uk",
  "event_type": "Summer Event",
  "event_date_requested": "Saturday 6 June 2026 (Date TBC)",
  "event_timings": "13:00hrs - 17:00hrs (TBC)",
  "duration_note": "Duration of hire can be amended upon request",
  "guest_range": "45 guests",
  "guest_quote_note": "Quote based on 45 guests at £65.00 per head = £2,925.00",
  "location": "London: River Thames"
}

Response: the generated PDF file (application/pdf), streamed back.
Make.com's HTTP module saves this directly as a file, which you then
feed into Google Drive / Gmail modules.

RUN LOCALLY
-----------
pip install flask --break-system-packages
python3 app.py
# -> listens on http://0.0.0.0:8080

DEPLOY (so Make.com on the internet can reach it)
--------------------------------------------------
Easiest free options: Render.com, Railway.app, Fly.io, or a small
EC2/DigitalOcean box. All of these work the same way:
  1. Push this folder (app.py, generate_proposal.py, assets/) to a
     GitHub repo.
  2. Connect the repo on Render/Railway, set the start command to
     `gunicorn app:app` (add gunicorn to requirements.txt).
  3. Deploy. You'll get a public URL like
     https://westend-proposals.onrender.com
  4. In Make.com, your HTTP module POSTs to
     https://westend-proposals.onrender.com/generate-proposal

SECURITY
--------
Add a shared-secret header check (see API_KEY below) so randoms can't
hit your endpoint and burn your compute. Set the same value in Make's
HTTP module headers.
"""

import os
import io
import tempfile
from flask import Flask, request, send_file, jsonify
from generate_proposal import generate_proposal_pdf, ProposalData

app = Flask(__name__)

API_KEY = os.environ.get("PROPOSAL_API_KEY", "")  # set this in your hosting env vars

REQUIRED_FIELDS = [
    "proposal_ref", "prepared_by", "prepared_by_title", "date_prepared",
    "quote_valid_days", "client_name", "organisation", "telephone", "email",
    "event_type", "event_date_requested", "event_timings", "duration_note",
    "guest_range", "guest_quote_note", "location",
]


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/generate-proposal", methods=["POST"])
def generate_proposal():
    # --- auth check ---
    if API_KEY:
        if request.headers.get("X-API-Key") != API_KEY:
            return jsonify({"error": "unauthorized"}), 401

    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "expected JSON body"}), 400

    missing = [f for f in REQUIRED_FIELDS if f not in payload]
    if missing:
        return jsonify({"error": f"missing fields: {missing}"}), 400

    try:
        data = ProposalData(
            proposal_ref=str(payload["proposal_ref"]),
            prepared_by=str(payload["prepared_by"]),
            prepared_by_title=str(payload["prepared_by_title"]),
            date_prepared=str(payload["date_prepared"]),
            quote_valid_days=int(payload["quote_valid_days"]),
            client_name=str(payload["client_name"]),
            organisation=str(payload["organisation"]),
            telephone=str(payload["telephone"]),
            email=str(payload["email"]),
            event_type=str(payload["event_type"]),
            event_date_requested=str(payload["event_date_requested"]),
            event_timings=str(payload["event_timings"]),
            duration_note=str(payload["duration_note"]),
            guest_range=str(payload["guest_range"]),
            guest_quote_note=str(payload["guest_quote_note"]),
            location=str(payload["location"]),
        )
    except (KeyError, ValueError) as e:
        return jsonify({"error": f"bad field value: {e}"}), 400

    # generate to an in-memory-ish temp file, then stream back
    safe_ref = "".join(c for c in data.proposal_ref if c.isalnum() or c in "-_") or "proposal"
    out_path = os.path.join(tempfile.gettempdir(), f"{safe_ref}.pdf")
    generate_proposal_pdf(data, out_path)

    return send_file(
        out_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{safe_ref}-proposal.pdf",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)