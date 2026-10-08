# Product research notes

Working notes behind the MVP's scope. These are **assumptions to validate** with renters, agents and landlords in Lagos, Port Harcourt, Enugu, Awka/Onitsha and Owerri, not measured findings. No market statistics are quoted here. Add sources as interviews and data come in.

## The problem we're designing for

- Renters often pay a full year (sometimes two) of rent up front, plus agency, legal/agreement and caution fees, which can add up to a large share of the rent on top.
- Listings circulate on social media and WhatsApp, and the person advertising is often not the owner. Renters struggle to tell whether that person may let the property at all.
- Common harms the product addresses: fake or duplicated listings, "agents" with no authority from the owner, photos that don't match the property, fees that appear only at payment, pressure to pay "inspection" or "holding" fees before seeing the place, and properties already let to someone else.

## Design responses (and the assumption behind each)

| Response | Assumption to test |
|---|---|
| Separate **agent** and **property** verification with different badges | Renters will read badge wording carefully if it is distinct, and conflating the two is a real risk |
| Publish **what was not checked** and an **expiry date** | Honesty about limits builds more trust than a bare "verified" tick, and protects PropCheck legally |
| Full **fee breakdown** with a server-computed total | Surprise fees are a top complaint, and agents will accept a standard breakdown |
| **Authority to market** as a mandatory check | An owner's authority letter (or owner contact) is obtainable for most legitimate listings |
| **Human reviewers** with an audit log | At pilot volume, manual review is affordable and more trustworthy than automation |
| Contact details **only with consent** | Agents worry about spam and poaching; renters still want WhatsApp-first contact |
| **WhatsApp** links rather than in-app chat | WhatsApp is the default channel for both sides |
| **Inspection booking** before any payment | A booked, confirmed inspection is the natural step before money changes hands |
| **Test-mode reservation** only | Holding rent safely needs licensing and partners. The demo exists to test whether renters want a "pay on keys" flow at all |
| Five launch states: Lagos, Rivers (Port Harcourt), Enugu, Anambra, Imo | Lagos for volume; the South-East and Port Harcourt for strong rental demand from students, workers and returnees. Northern states are deliberately out of the first release |
| **What is nearby?** (markets, restaurants, churches, clubs) | Renters judge a neighbourhood by everyday amenities before inspecting. These four categories matter most at first |

## Open questions for the pilot

1. Will agents pay for verification after the pilot, and at what price per year or per listing?
2. What share of listings can produce an owner authority letter within a few days?
3. How long does a property inspection take a reviewer, including travel? This drives the cost per verification.
4. How long should a property verification stay valid? (MVP: 6 months; agents: 12 months.)
5. Do renters trust a platform-assigned agent more than browsing the directory themselves?
6. Which report reasons come up most often, and how many lead to suspension?
7. Is there demand for a regulated escrow or "pay on keys" partner, and which licensed partners exist?

## Things deliberately out of scope

- Title, survey or land-registry searches, and any legal opinion on ownership. These need lawyers and official registries.
- Real payments or escrow.
- Automated or AI approval of documents. If added later, AI may only assist reviewers.

## Research log (to complete)

Nothing below has been gathered yet. Fill each item in from real sessions and sources. Do not paraphrase from memory or invent quotes, prices or statistics.

### Renter interviews

| # | Who (role, city; no names) | Date | Key findings | Quote (with consent) |
|---|---|---|---|---|
| R1 | TODO | TODO | TODO | TODO |
| R2 | TODO | TODO | TODO | TODO |

### Agent or landlord interviews

| # | Who (role, city; no names) | Date | Key findings | Willingness to share an authority letter |
|---|---|---|---|---|
| A1 | TODO | TODO | TODO | TODO |
| A2 | TODO | TODO | TODO | TODO |

### Competitors and workarounds

| # | Product or workaround | What it does | Gap PropCheck addresses | Source / date checked |
|---|---|---|---|---|
| C1 | TODO | TODO | TODO | TODO |
| C2 | TODO | TODO | TODO | TODO |

Do not record competitor prices unless they are taken from a dated, cited source.

### Cited sources

1. TODO: source on Nigerian rental practice (fees, upfront rent).
2. TODO: source on rental fraud patterns or consumer complaints.
3. TODO: source on agent regulation or registration in a launch state.

### Nigerian rental and verification considerations to research

- TODO: which agent registrations or licences (state-level or professional bodies) can reasonably be checked in each launch state.
- TODO: what an "authority to let" usually looks like in practice, and who issues it.
- TODO: the legal limits of a platform describing a property as "verified"; get legal review before scaling.
- TODO: data-protection obligations for storing ID documents (NDPA 2023); confirm with counsel.

### Paystack documentation

The MVP uses test mode only (`sk_test_…`; live keys are refused at startup). To review and record what was confirmed, with dates:

- TODO: Accept Payments / Initialize Transaction: https://paystack.com/docs/api/transaction/
- TODO: Test payments and test cards: https://paystack.com/docs/payments/test-payments/
- TODO: Webhooks and signature verification: https://paystack.com/docs/payments/webhooks/
- TODO: whether a split, subaccount or licensed escrow partner is needed for any real "pay on keys" flow.

### Design decisions based on the research

Each line should be completed once evidence exists, or the decision reversed.

1. TODO: separate agent and property badges. Evidence: …
2. TODO: authority to market is mandatory. Evidence: …
3. TODO: WhatsApp-first contact, shown only with consent. Evidence: …

### Technical spike: riskiest integration

**Question:** can a reservation be paid, released or refunded exactly once, even with retries and concurrent requests?

**What exists:** a payment-provider interface (`app/services/payments.py`) with a simulator and a Paystack test-mode provider; row locking plus a data-driven state machine; tests for duplicate pay, release and refund (`tests/test_reservations.py`); and `scripts/e2e_journey.py`, which runs the full journey against a live stack.

**Still TODO:** run the Paystack provider against a real test-mode account (initialize, then verify with a test card), record the result here, and confirm webhook handling before any non-test use.

## Next research steps

- 10–15 renter interviews (recent movers in each launch city): how they found the place, what they paid, what went wrong.
- 5–10 agent interviews: willingness to share authority letters, fee transparency, pricing.
- Shadow 5 real inspections to time the checklist and refine the check definitions.
