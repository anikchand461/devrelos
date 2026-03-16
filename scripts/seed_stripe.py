"""
Seed script — ingest the Stripe OpenAPI spec for demo purposes.
Run with: python scripts/seed_stripe.py
"""
import asyncio
import httpx

API_BASE = "http://localhost:8000"

# Minimal Stripe spec subset for fast demo seeding
STRIPE_MINI_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Stripe API", "version": "2024-06-20"},
    "paths": {
        "/v1/payment_intents": {
            "post": {
                "summary": "Create a PaymentIntent",
                "description": "Creates a PaymentIntent object. After creating a PaymentIntent, attach a payment method and confirm to continue the payment.",
                "tags": ["Payment Intents"],
                "operationId": "CreatePaymentIntent",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["amount", "currency"],
                                "properties": {
                                    "amount": {"type": "integer", "description": "Amount in smallest currency unit (e.g. cents). $50 = 5000"},
                                    "currency": {"type": "string", "example": "usd"},
                                    "payment_method_types": {"type": "array", "items": {"type": "string"}, "example": ["card"]},
                                    "description": {"type": "string"},
                                    "metadata": {"type": "object"},
                                },
                            }
                        }
                    }
                },
            },
            "get": {
                "summary": "List PaymentIntents",
                "description": "Returns a list of PaymentIntents.",
                "tags": ["Payment Intents"],
                "operationId": "ListPaymentIntents",
            },
        },
        "/v1/payment_intents/{intent}": {
            "get": {
                "summary": "Retrieve a PaymentIntent",
                "description": "Retrieves the details of a PaymentIntent.",
                "tags": ["Payment Intents"],
                "operationId": "RetrievePaymentIntent",
            },
            "post": {
                "summary": "Update a PaymentIntent",
                "description": "Updates properties on a PaymentIntent.",
                "tags": ["Payment Intents"],
                "operationId": "UpdatePaymentIntent",
            },
        },
        "/v1/payment_intents/{intent}/confirm": {
            "post": {
                "summary": "Confirm a PaymentIntent",
                "description": "Confirm that your customer intends to pay with current or provided payment method.",
                "tags": ["Payment Intents"],
                "operationId": "ConfirmPaymentIntent",
            }
        },
        "/v1/charges": {
            "post": {
                "summary": "Create a charge",
                "description": "To charge a credit card or other payment source, create a Charge object.",
                "tags": ["Charges"],
                "operationId": "CreateCharge",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["amount", "currency"],
                                "properties": {
                                    "amount": {"type": "integer"},
                                    "currency": {"type": "string"},
                                    "source": {"type": "string"},
                                    "description": {"type": "string"},
                                },
                            }
                        }
                    }
                },
            },
            "get": {
                "summary": "List all charges",
                "description": "Returns a list of charges previously created.",
                "tags": ["Charges"],
                "operationId": "ListCharges",
            },
        },
        "/v1/customers": {
            "post": {
                "summary": "Create a customer",
                "description": "Creates a new customer object.",
                "tags": ["Customers"],
                "operationId": "CreateCustomer",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "email": {"type": "string", "format": "email"},
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                    "metadata": {"type": "object"},
                                },
                            }
                        }
                    }
                },
            },
        },
    },
}

import json

async def seed():
    print("🌱 Seeding Stripe API spec...")
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
        resp = await client.post("/api/ingest/", json={
            "api_slug": "stripe",
            "spec_content": json.dumps(STRIPE_MINI_SPEC),
            "spec_format": "openapi",
        })
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Indexed {data['endpoints_indexed']} endpoints, {data['embedding_count']} embeddings")
        else:
            print(f"⚠ Ingest returned {resp.status_code}: {resp.text}")


if __name__ == "__main__":
    asyncio.run(seed())
