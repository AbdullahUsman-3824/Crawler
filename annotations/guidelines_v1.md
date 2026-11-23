# Relevance Annotation Guidelines v1

Project: AI/deepfake-enabled financial fraud (IIO study). Applies to the relevance pilot sample.

## 1. What you are labelling

For every comment, fill these columns in the CSV:

| Column | What to write |
|---|---|
| `relevance_label` | one of: `relevant`, `partially_relevant`, `irrelevant`, `uncertain` |
| `context_type` | one of: `personal_experience`, `news_reporting`, `advice_prevention`, `general_discussion`, `hypothetical`, `unclear` |
| `reason` | one short sentence: why this label |
| `evidence_text` | the exact words copied from the comment that support the label (leave empty for `irrelevant`) |
| `reviewer_notes` | optional; anything doubtful |

Read the comment together with `parent_comment_text` (for replies). Do not label a reply in isolation.

## 2. The two tests

Ask two questions about the comment (and its parent):

- **AI link?** The text explicitly mentions AI-generated or cloned voice, video, image, profile, or a deepfake, or an AI-based scam. General opinions about AI (LLMs, jobs, danger of AI) do NOT count.
- **Fraud link?** The text is about money-related scams or fraud: a victim's experience, reporting a fraud, preventing or verifying against it, recovering money, or discussing scammers and the response to them.

| AI link | Fraud link | Label |
|---|---|---|
| yes | yes | `relevant` |
| yes | no | `partially_relevant` (tag `ai_no_fraud` in notes) |
| no | yes | `partially_relevant` (tag `fraud_no_ai` in notes) |
| no | no | `irrelevant` |

`uncertain` is only for a comment whose meaning you cannot understand even after reading the parent comment. Do not use it to avoid a hard decision.

## 3. Approved decisions (v1)

1. **Video title is context only.** Use it to understand a vague comment, but it can never be the only reason for `relevant`. If the AI or fraud link comes only from the video title, label `partially_relevant` and add `BOUNDARY:video_context` in notes. Exception: the comment itself points to the video's scam with words like "this exact scam" or "similar call", plus a loss or action. That can be `relevant`.
2. **AI-made blackmail** (for example AI-edited nude images, no money mentioned): `partially_relevant`, note `ai_extortion`.
3. **Spam** (templated recovery-service testimonials, scam promotions, ads, links): always `irrelevant`, note `SPAM`, even if it mentions scams or AI.
4. **Political or entertainment deepfakes** with no fraud: `partially_relevant`, note `ai_no_fraud`.
5. **English only.** If the meaning-carrying part of the comment is not English (Urdu, Roman Urdu, Hindi, Malayalam), label `irrelevant` and note `NON_ENGLISH`. A mostly English comment with one or two foreign words is English.

## 4. Other rules

- **Generic praise, emoji, jokes, one-word reactions** ("good video", "Right 👍"): `irrelevant`. A reaction that judges a victim or scammer with some content ("She's a little dim") is `partially_relevant` with `BOUNDARY:video_context`.
- **Fraud that is not an AI scam** (bank fraud, loan apps, crypto, insurance disputes): needs a real scam or fraud. Insurance claim disputes, job-recruitment scandals, mistaken payments are `irrelevant`.
- **Replies** that only say "yes", "right", "How" with nothing else: `irrelevant`. If the parent gives the meaning, judge the pair.
- **Names of private individuals**: label normally; add note `names_individual`.

## 5. Context type (pick one)

| Type | Use when |
|---|---|
| `personal_experience` | the writer or someone they know was targeted, lost money, or reported |
| `news_reporting` | the writer reports an event or story from news |
| `advice_prevention` | the writer tells others what to do or avoid; verification tips; reporting steps |
| `general_discussion` | opinions, questions, blame, criticism, reactions |
| `hypothetical` | what could or would happen |
| `unclear` | cannot tell (emoji, spam, generic praise) |

If two fit, prefer `personal_experience`, then `advice_prevention`, then the others.

## 6. Examples

| Comment (shortened) | Label | Context | Why |
|---|---|---|---|
| "I was just a victim of this exact scam... out $15k" (AI voice scam video) | relevant | personal_experience | loss, scam named by "this exact scam" |
| "Safe words are no longer safe... voice was cloned with AI. Hang up and call directly." | relevant | advice_prevention | AI voice clone and prevention advice |
| "Same happened with us... their profile mostly are ai generated" (scam calls demanding money) | relevant | personal_experience | AI profiles, money demand |
| "Like a safe word?" (reply under a code-word tip) | partially_relevant | advice_prevention | AI link only through the video: BOUNDARY |
| "I got the Zelle scam call... hang up and call your bank" | partially_relevant | personal_experience | fraud, no AI: fraud_no_ai |
| "We can no longer trust anything on the internet" (deepfake video) | partially_relevant | general_discussion | AI, no fraud: ai_no_fraud |
| "Thank you, VALUE RECOUP, for helping me get my money back" | irrelevant | unclear | SPAM |
| "Good video sir" | irrelevant | unclear | generic praise |
| Roman Urdu complaint about fraud | irrelevant | unclear | NON_ENGLISH |
| "Americans sent Deepfake fraud Donald Trump to the White House" | irrelevant | general_discussion | word "deepfake" used as an insult |

## 7. Working rules for the second annotator

- Do not look at the first annotator's labels before you finish.
- Do not discuss specific comments with the first annotator until both files are submitted.
- If a rule is unclear, write your best guess and put the doubt in `reviewer_notes`. Do not ask during labelling; the doubts help improve these guidelines.
