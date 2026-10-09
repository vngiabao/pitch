---
version: 1
slug: "founder-os-pitch-studio"
primary_target: "founder_os/ui/pitch.js"
related_targets: ["founder_os/ui/style.css", "founder_os/ui/index.html", "founder_os/ui/app.js", "founder_os/pitch_studio.py", "founder_os/server.py"]
---

# Pitch Studio

Mode: Operate. An ordinary extension inside the existing Founder OS; inherit root DESIGN.md and .impeccable/design.json. No new identity or visual-world tournament. The owner's monochrome email preference applies to email, not a requested app redesign.

## Direction contract

THESIS: Put editable pitch wording within reach of the founder's real audience and available time. Distinguish a spoken script from a working outline, preserve source context, and make practice a useful next step.

OWN-WORLD: Retain the app's Segoe UI, restrained teal, pale workspace, white sections, thin rules, native controls, and explicit states. No imagery, decorative cards, or new font system.

STORY: Choose a length, audience, and scenario; edit or duplicate the pitch; save without losing earlier wording; rehearse; and read the source before using historical claims.

FIRST VIEWPORT: Existing navigation adds Pitch Studio. The library leads with New pitch, native filters, then readable rows with timing. The editor places title and Save version above audience/scenario fields and text, with provenance alongside on desktop and below on mobile.

FORM: Code-led inherited library/editor extension; no new concept seed or approved comp. The signature interaction is edit-to-rehearse with current unsaved text and an elapsed timer. Motion is limited to native interaction, with no entrance animation.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

## Evidence and boundaries

Sources: preserved Pitch Competition material library, written pitch structure, September investor deck, original short pitch, and owner-confirmed family-biographer direction. Thirteen sourced starting drafts plus the original pitch are local working drafts. Longer entries are clearly labeled outlines. Original files and canonical company facts remain unchanged.

Save, restore, immutable versions, concurrency conflicts, source validation, custom choices, export and HTTP security have automated checks. Browser checks cover creating a custom audience/scenario pitch, a 95-second custom duration, save/reload persistence, archiving the verification draft, and start/pause rehearsal. No program submission or external communication occurs.

Required screenshots: .impeccable/review/pitch/desktop-library.jpg, desktop-editor.jpg, desktop-rehearsal.jpg at the user's 1280px CSS viewport, and mobile-library.jpg / mobile-editor.jpg at 390px. Full-page screenshots supplement readable viewport crops. No shipping raster assets were added.

Quality bar: task controls are discoverable, writing stays readable, sources remain traceable, saved/unsaved states are explicit, and a 390px phone requires no horizontal page scrolling.

## Verified extension notes — October 8, 2026

The shipped library and editor preserve the root system's teal actions, Segoe UI hierarchy, pale workspace, white bordered sections, native fields and visible keyboard focus. The extension adds no brand palette, font family, shadow, authored animation or shipping raster. Root DESIGN.md and its sidecar remain the app authority; email-local design authority does not govern this surface.

Library rows place wording and audience/scenario on the left and target length, estimated speech length and draft state on the right. At the inherited 720px breakpoint, metadata moves below the wording. The editor uses a wider writing track and narrower provenance/history track (1.8fr and 1fr, 24px gap); these stack at 1080px. Its two-column fields become one column at 720px. Context follows writing on phone.

Writing uses body-sized text (15px) with a comfortable line height (1.7); rehearsal enlarges the same family (20px, line height 1.7, 65ch maximum measure). The elapsed timer uses the inherited headline size (30px) and tabular numerals. These are surface-specific reading treatments, not a new global type system.

Keep target duration distinct from the 130-word-per-minute estimate. The 7-, 10-, 15- and 20-minute starters are working outlines with prompts and planned demonstrations. Preserve the visible saved/unsaved state, explicit historical-source boundary, current-text copy versus saved-TXT export wording, and restore-as-new-version explanation. Rehearsal reads the current editor wording, including unsaved edits, with start/pause/resume/reset controls.

Evidence: all five required full captures and four supplemental viewport clips were inspected alongside shipped source. The fresh finish review records SHIP with no material fixes. The functional verification report records 14 active drafts, preserved hashes for the two checked original source files, 136 passing fixture tests, custom 95-second editing/persistence, timer practice and no page overflow at the stated desktop/mobile viewports. This documentation pass reads those verification records; it does not rerun tests or certify external eligibility.

Inherited detector advisories remain reported rather than canonized: selection/link colors outside the recorded palette, secondary sizes partly described only in prose, and the incumbent mark's `ui` font-parser warning. These do not justify changing root authority during an ordinary extension.
