---
version: 1
slug: "founder-os-report-email"
primary_target: "founder_os/email_design.py"
related_targets: ["founder_os/report_email.py", "founder_os/connector_outbox.py", "reports/email-preview/index.html"]
---

# Founder OS report email

Mode: Read. Owner-only opportunity report email. Email-local normative tokens live in `.impeccable/email/DESIGN.md`, with extension metadata in `.impeccable/email/design.json`.

Owner requested a professional, clearly divided report with highlighting, then explicitly chose "Black and white - formal and minimal." This preference applies to email, not the teal Founder OS application.

## Direction contract

A restrained editorial brief: black A Story masthead, large plain headline, numbered opportunity sections separated by rules, pale benefit/deadline bands, dark review links, and separate agent work versus owner action. Name, practical relevance, useful benefit, deadline, requirements and catches remain visible. Conditional opportunities remain REVIEW and unknown eligibility stays explicit. Full private application drafts remain in the authorized TXT attachment. No fake fit scores, invented company facts, application submission or approval by email.

This is a code-led narrow extension of an existing report; no comp or visual-world tournament. Email-safe presentation tables, inline CSS and Segoe UI/Arial follow delivery constraints; no JavaScript, animation, web fonts, remote imagery, or decorative raster assets. Baseline is readable without media queries. Desktop 1280px and mobile 390px checked. Maximum width 680px, 36px desktop and 22px mobile padding. Text 15px/1.6, headings 40px desktop / 32px mobile and 25px section titles.

Email-local colors: ink #171717, body #333333, supporting #454545 and #595959, white #ffffff, borders #d8d8d8 and #a8a8a8, panels #f2f2f2 / #fafafa / #f5f5f5, outer #eeeeee, masthead date #d6d6d6. The detector's off-palette/type advisories reflect this explicit owner-approved email direction; root DESIGN.md and .impeccable/design.json stay unchanged.

Primary source: founder_os/email_design.py. Integration: founder_os/report_email.py and founder_os/connector_outbox.py. Real-data preview: reports/email-preview/index.html. Screenshots: .impeccable/review/email/desktop.jpg and mobile.jpg.

Final headings lead each opportunity region, with category metadata below the name. Additional user-panel evidence is user-950.jpg, named for its measured captured width of 950px. The app panel changed size during capture; do not infer a fixed 700px CSS viewport from the earlier filename. Desktop1280 and mobile390 were explicitly controlled, and the mobile document had no horizontal overflow.

Delivery uses persisted body_html plus UTF-8 SHA-256 inside the exact claimed message. Daily HTML freezes when sending begins; supplement messages are immutable. Daily and sample share one renderer. Existing sent reports are preserved. Only the authorized owner receives the sample; Runway stays on hold.

Verification scope: local desktop/mobile render and real Gmail delivery. Native Outlook/dark-mode clients not independently captured.

Documentation verification distinguishes the retained local screenshots from transport evidence. Gmail receipt/inbox rendering is recorded by the delivery workflow; a local preview or design review alone does not establish inbox receipt. Legacy `user-700.jpg` and `user-966.jpg` filenames are not viewport evidence; `user-950.jpg` is the authoritative user-panel capture for the measured 950px image width.
