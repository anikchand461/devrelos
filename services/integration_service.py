"""
services/integration_service.py – External Integration Service
Sends notifications to Slack, Discord, and Email.
All webhook URLs and SMTP config come from .env.
"""

import os
import json
import asyncio
import httpx
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

TIMEOUT = httpx.Timeout(15.0)


# ── Slack ─────────────────────────────────────────────────────────────────────

async def send_slack(message: str, details: Dict = None) -> Dict:
    """Send a message to Slack via Incoming Webhook."""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")
    if not webhook_url or webhook_url.startswith("https://hooks.slack.com/services/YOUR"):
        return {"success": False, "error": "SLACK_WEBHOOK_URL not configured"}

    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*DevRelOS Notification*\n{message}"}
        }
    ]
    if details:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"```{json.dumps(details, indent=2)[:1500]}```"}
        })

    payload = {"blocks": blocks}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(webhook_url, json=payload)
        if resp.status_code == 200:
            return {"success": True, "channel": "slack"}
        return {"success": False, "error": resp.text, "status": resp.status_code}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ── Discord ───────────────────────────────────────────────────────────────────

async def send_discord(message: str, details: Dict = None) -> Dict:
    """Send a message to Discord via Webhook."""
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL", "")
    if not webhook_url or "YOUR" in webhook_url:
        return {"success": False, "error": "DISCORD_WEBHOOK_URL not configured"}

    content = f"**DevRelOS Notification**\n{message}"
    if details:
        content += f"\n```json\n{json.dumps(details, indent=2)[:1500]}\n```"

    payload = {"content": content}

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(webhook_url, json=payload)
        if resp.status_code in (200, 204):
            return {"success": True, "channel": "discord"}
        return {"success": False, "error": resp.text, "status": resp.status_code}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ── Email ─────────────────────────────────────────────────────────────────────

async def send_email(
    to_email: str,
    subject:  str,
    message:  str,
    details:  Dict = None,
) -> Dict:
    """Send an email via SMTP (aiosmtplib)."""
    smtp_host = os.getenv("SMTP_HOST", "")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")
    from_addr = os.getenv("SMTP_FROM", smtp_user)

    if not all([smtp_host, smtp_user, smtp_pass, to_email]):
        return {"success": False, "error": "SMTP not fully configured (check SMTP_HOST, SMTP_USER, SMTP_PASSWORD)"}

    # Build email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject or "DevRelOS Notification"
    msg["From"]    = from_addr
    msg["To"]      = to_email

    body_text = message
    if details:
        body_text += f"\n\nDetails:\n{json.dumps(details, indent=2)}"

    body_html = f"""<html><body>
    <h2 style="color:#4f46e5;">DevRelOS</h2>
    <p>{message.replace(chr(10), '<br>')}</p>
    {"<pre style='background:#f3f4f6;padding:12px;border-radius:6px;'>" + json.dumps(details, indent=2) + "</pre>" if details else ""}
    </body></html>"""

    msg.attach(MIMEText(body_text, "plain"))
    msg.attach(MIMEText(body_html, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname  = smtp_host,
            port      = smtp_port,
            username  = smtp_user,
            password  = smtp_pass,
            start_tls = True,
        )
        return {"success": True, "channel": "email", "to": to_email}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ── Dispatcher ────────────────────────────────────────────────────────────────

async def send(
    channel:  str,
    message:  str,
    subject:  Optional[str] = None,
    to_email: Optional[str] = None,
    details:  Optional[Dict] = None,
) -> Dict:
    """Route to the correct integration channel."""
    ch = channel.lower()
    if ch == "slack":
        return await send_slack(message, details)
    elif ch == "discord":
        return await send_discord(message, details)
    elif ch == "email":
        return await send_email(to_email or "", subject or "DevRelOS", message, details)
    else:
        return {"success": False, "error": f"Unknown channel: {channel}"}


async def broadcast(
    message: str,
    details: Optional[Dict] = None,
) -> Dict:
    """Send to all configured channels simultaneously."""
    tasks   = [send_slack(message, details), send_discord(message, details)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return {
        "slack":   results[0] if not isinstance(results[0], Exception) else {"success": False, "error": str(results[0])},
        "discord": results[1] if not isinstance(results[1], Exception) else {"success": False, "error": str(results[1])},
    }
