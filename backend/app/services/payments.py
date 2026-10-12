"""Payment providers — TEST MODE ONLY.

PropCheck's MVP never processes real money. `get_provider()` returns:
* `PaystackTestProvider` when PAYSTACK_SECRET_KEY is set (config refuses anything but sk_test_ keys);
* `SimulatedProvider` otherwise, which generates a PCK-TEST-... reference and succeeds immediately.
"""

import secrets
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.config import settings
from app.errors import BadRequest

PAYSTACK_BASE = "https://api.paystack.co"


@dataclass
class PaymentInit:
    reference: str
    authorization_url: str | None  # where to send the renter (Paystack checkout); None for simulated


@dataclass
class PaymentResult:
    reference: str
    success: bool
    provider: str
    message: str = ""


class PaymentProvider(Protocol):
    name: str

    async def initialize(self, *, email: str, amount_naira: int, reservation_id: int) -> PaymentInit: ...

    async def verify(self, reference: str) -> PaymentResult: ...


def new_reference(reservation_id: int) -> str:
    return f"PCK-TEST-{reservation_id}-{secrets.token_hex(5).upper()}"


class SimulatedProvider:
    name = "simulated"

    async def initialize(self, *, email: str, amount_naira: int, reservation_id: int) -> PaymentInit:
        return PaymentInit(reference=new_reference(reservation_id), authorization_url=None)

    async def verify(self, reference: str) -> PaymentResult:
        ok = reference.startswith("PCK-TEST-")
        return PaymentResult(
            reference, ok, self.name, "Simulated test payment" if ok else "Unknown reference"
        )


class PaystackTestProvider:
    name = "paystack_test"

    def __init__(self, secret_key: str):
        if not secret_key.startswith("sk_test_"):
            raise RuntimeError("Refusing to use a non-test Paystack key.")
        self._headers = {"Authorization": f"Bearer {secret_key}"}

    async def initialize(self, *, email: str, amount_naira: int, reservation_id: int) -> PaymentInit:
        reference = new_reference(reservation_id)
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{PAYSTACK_BASE}/transaction/initialize",
                headers=self._headers,
                json={
                    "email": email,
                    "amount": amount_naira * 100,  # Paystack expects kobo
                    "reference": reference,
                    "currency": "NGN",
                    "callback_url": settings.paystack_callback_url,
                    "metadata": {"reservation_id": reservation_id, "mode": "propcheck-demo"},
                },
            )
        body = resp.json()
        if resp.status_code != 200 or not body.get("status"):
            raise BadRequest("Could not start the Paystack test payment.")
        return PaymentInit(reference=reference, authorization_url=body["data"]["authorization_url"])

    async def verify(self, reference: str) -> PaymentResult:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(f"{PAYSTACK_BASE}/transaction/verify/{reference}", headers=self._headers)
        body = resp.json()
        ok = resp.status_code == 200 and body.get("data", {}).get("status") == "success"
        return PaymentResult(reference, ok, self.name, body.get("message", ""))


def get_provider() -> PaymentProvider:
    if settings.paystack_secret_key:
        return PaystackTestProvider(settings.paystack_secret_key)
    return SimulatedProvider()
