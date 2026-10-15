# How the Founder OS agents work together

Every piece of outward-facing writing (an application answer, a tailored pitch, a press pitch, a follow-up email) moves through the same assembly line. No single agent ships anything. Each one does one job, hands off, and can send work back. Bao is the last step every time, and nothing is submitted or sent without his explicit yes.

## The agents

| Layer | Agent | Job | Uses AI? | Web? |
|---|---|---|---|---|
| Find | **Funding Hunter** | Finds and verifies programs and money (19 search families) | Yes | Yes |
| Find | **Press Scout** | Finds gift guides, newsletters and outlets | Yes | Yes |
| Find | **Form Reader** | Opens official application forms and reads the questions | No | Yes (read-only) |
| Find | **Inbox Tracker** | Reads both inboxes for results (read-only) | No | No |
| Draft | **Application Drafter** | Answers form questions from approved facts | Yes | No |
| Draft | **Pitch Tailor** | Reads a program's rules and builds the program edition: slide plan, timed script, materials checklist, ask | Yes | Official rules page only |
| Draft | **Follow-up and Press Drafters** | Notes to people and outlets | Yes | No |
| Check | **Fact Guard** | Every number and claim traces to approved facts or the evidence table. Applies the team, traction and pricing rules. | No (rules) | No |
| Check | **Bao's Voice** | Rewrites wording into Bao's voice (BAO-VOICE.md). Never changes facts. | Yes | No |
| Check | **Pitch Coach** | YC-partner review: 10-point scorecard, hard questions, the three fixes that matter most | Yes | No |
| Check | **Format Check** | Word and character limits, time at 130–150 wpm, required sections | No (rules) | No |
| Decide | **Bao** | Edits, approves or rejects. Submits himself. | - | - |
| Learn | **Outcome Learner** | Turns results and Bao's edits into proposed lessons | Yes | No |
| Report | **Daily Report and Today** | One list of what needs Bao, every morning | No | No |

## The assembly line (one work item)

```
 Hunter / Form Reader / Scout          (find)
            │
            ▼
 Drafter / Pitch Tailor                (draft, round 1)
            │
            ▼
 Fact Guard ──── fails ───► back to the drafter with the exact issues
            │ passes
            ▼
 Bao's Voice                           (wording only)
            │
            ▼
 Fact Guard again                      (voice edits can't add claims)
            │
            ▼
 Pitch Coach ── any score < 4 and round < 3 ──► back to the drafter with the top 3 fixes
            │ all ≥ 4, or round 3 reached
            ▼
 Format Check                          (limits, timing)
            │
            ▼
 READY FOR BAO   → Today, the daily email, and the item's page
            │
   Bao edits ──► his edit becomes a voice example (feeds Bao's Voice and Coach)
   Bao approves and submits himself
            │
            ▼
 Inbox Tracker or Bao records the result
            │
            ▼
 Outcome Learner ──► proposed lessons in Decisions ──► approved lessons join the playbook context
```

**Stages** (stored on each work item): `DRAFT → FACT_CHECK → VOICE → FACT_RECHECK → COACH → (REVISE → DRAFT …) → FORMAT → READY → APPROVED → SUBMITTED → RESULT`.

**Loop limits.** At most two revision rounds. On round 3 the item goes to Bao anyway, with the Coach's open concerns attached. Bao's time is the bottleneck, so the system never loops silently forever, and never hides a weak score.

## The four feedback loops

1. **Quality loop (minutes).** Coach and Fact Guard send work back to the drafter with specific fixes, not general advice. The drafter must answer each fix or explain why not.
2. **Voice loop (every edit).** Bao's change from the final draft to his own version is saved as a voice example. Bao's Voice reads the ten newest examples on every run, so his corrections compound instead of repeating.
3. **Outcome loop (per result).** When a program accepts, rejects or gives feedback, the Outcome Learner links the result to the exact answers, deck edition and Coach scores used. It proposes lessons ("judges at voice-AI programs responded to the real-call demo"). Approved lessons are added to every future Tailor and Coach context. They also feed the Hunter, which ranks similar programs higher after a win and lower after repeated rejections.
4. **Playbook loop (weekly).** When the same lesson or voice pattern repeats three times, it's proposed as a permanent rule for PITCH-PLAYBOOK.md or BAO-VOICE.md. Bao approves it in Decisions. Nothing changes the playbook without him.

## Contracts between agents

- **Hand-offs are data, not prose.** Each agent returns JSON with a verdict, scores or issues, and the revised text. The next agent reads only that, plus approved facts and the playbook.
- **Facts only flow one way.** Only Bao can approve a fact (Decisions). Agents read approved facts; they never create them. Fact Guard blocks any number that isn't approved or in the evidence table.
- **Voice can't change facts; Coach can't add facts.** If the Coach wants a number that doesn't exist, it says "missing proof" and the item lists it under open questions for Bao.
- **Every review is kept.** Each work item shows its full history: who said what, at which round, with scores. Nothing is overwritten.
- **Cost guard.** One AI step per worker cycle (every 5 minutes), on the ChatGPT plan. No API keys. Coach and Voice skip items Bao already approved.
- **Safety.** Read-only on the web and in the inboxes. Agents never submit, send, pay or accept terms.

## Where Bao sees it

- **Today and the daily email:** items READY for him, and lessons waiting in Decisions.
- **Pitch Lab:** program editions, with the Coach scorecard, hard questions with suggested answers, the timed script and the slide plan.
- **Each application page:** answers with Fact Guard and Voice notes, plus the Coach's scorecard for the whole set.
- **Agent activity:** the assembly line, live: what each agent is doing and every item's stage.
