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

## Next research steps

- 10–15 renter interviews (recent movers in each launch city): how they found the place, what they paid, what went wrong.
- 5–10 agent interviews: willingness to share authority letters, fee transparency, pricing.
- Shadow 5 real inspections to time the checklist and refine the check definitions.
