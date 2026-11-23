# Decisions log

## 2026-11-22: inter-annotator check 1 (50 comments, A vs B)

Agreement: relevance 90% (kappa 0.83); context_type 90% (kappa 0.86); keep vs drop 92% (kappa 0.84).
Caveats: only 50 comments, 5 relevance disagreements, only 5 `relevant` in the subset. The subset was enriched for hard cases, so this kappa is a hard-case estimate.

Resolved (approved by the research group):

| Comment | A | B | Decision |
|---|---|---|---|
| Send him a message to help you | irrelevant | partial | irrelevant (SPAM referral) |
| Jubilee insurance fraud, "I am one of the victim" | partial | irrelevant | partial (explicit fraud and victim) |
| "give me your address there". LoL | partial | irrelevant | irrelevant (reaction) |
| Recovery scam warning naming Reclamio | partial | irrelevant | irrelevant (SPAM promo) |
| Similar call, confirmed with a friend | relevant | partial | partial (no loss) |

Consistency changes: SkyNet joke and "She's a little dim" -> irrelevant; TruthScan comment -> irrelevant (SPAM).

Result: labels v1.1 = irrelevant 198, partially_relevant 47, relevant 3, uncertain 1 (249 comments).
