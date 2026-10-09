# Pitch Studio

Open http://127.0.0.1:8765/pitches on this PC, or select Pitch Studio in Founder OS. If the site is stopped, use `Open-Founder-OS.ps1`.

## Work with a pitch

1. Filter by length, audience or scenario, then open a pitch. All audience and scenario names can be changed or replaced with your own.
2. Use Make a variant to create a separate variant. Change its audience, setting, speaker, length, wording and notes.
3. Save pitch to retain the edited script. Earlier versions remain in Version history. Restore as new version keeps both the earlier wording and intervening edits.
4. Practice aloud uses the current editor text, including unsaved edits. Start, pause, resume or reset the timer. Timing estimates assume 130 words per minute; demonstrations, questions and pauses need actual rehearsal.
5. Copy current text copies the editor wording. Download saved TXT exports the saved version with notes, version ID and source references. Save first if you want the download to contain recent edits.

Write a new pitch starts a blank draft. Choose a preset from 30 seconds through 20 minutes, or enter a custom length of 10 seconds to 120 minutes. Use Archived to hide a pitch from the default library without losing its history; Include archived makes it visible again.

The 16 active drafts include the preserved original short pitch and 15 curated drafts. The 7-, 10-, 15- and 20-minute entries are timed session plans with demonstrations and discussion, rather than finished speeches of that duration. The YC founder-video version uses talking points. They remain editable working drafts. Historical claims are not current company facts.

## Use the pitch folder

Materials keeps original source paths and searchable extracted text from the Pitch Competition folder. Open a material and use Adapt in Pitch Studio to start a source-linked draft. Text longer than 40,000 characters is explicitly truncated in the editor; the complete source remains in Materials. A file without extracted text remains a reference for manual adaptation. Decks and binaries are not silently copied or rewritten.

The original folder is `C:\Users\vngia\OneDrive - Umich\Desktop\My startups\Pitch Competition`. This feature writes only to Founder OS. `reports/pitch-studio-manifest.json` links starting drafts to preserved source versions. Source paths remain visible on each draft.

## Persistence and recovery

The existing `pitches` table remains the identity anchor. `pitch_documents` points to the current immutable `pitch_versions` entry. Every save records its parent, sources and an activity event. Original pitches are never rewritten. New legacy agent pitches appear when the library is read. Starter import keys prevent duplicates if `tools/seed_pitch_studio.py` is run again.

If another tab saves first, the editor reports a conflict and keeps your unsaved text. Copy it, reload the latest saved version, then merge the wording. Leaving the page with unsaved edits invokes the browser's leave warning. Immutable versions are retained rather than deleted.

Back up `data/founder.sqlite` consistently using the existing OS backup workflow. The original source paths remain necessary for binary references. No API key is needed for manual editing, curated starting drafts, saving or rehearsal. This studio does not claim to generate arbitrary new pitches automatically.

## Verification

Fixture tests cover immutable history, restore, stale edits, source validation, custom choices, archive filtering, repeat-safe starter keys, legacy agent drafts and HTTP session/CSRF protection. Browser checks cover creating a custom pitch, saving a 95-second duration, reloading the wording, archiving the verification draft and running/pausing the rehearsal timer. Desktop 1280px and phone 390px views were checked for page overflow and console errors. Evidence lives under `.impeccable/review/pitch/` and `reports/pitch-studio-verification.json`.

## October 9 workspace repair

The protected live studio is https://pitch.gbaonvo.com/pitches. Existing starter wording was revised as new immutable versions. There are 15 curated drafts plus the preserved legacy pitch: audience-specific introductions, family invitations, partner arguments, competition and investor scripts, timed session plans, YC founder-video talking points and the owner's Runway exploration. See PITCH_WRITING.md and seed-data/pitch-editorial-2026-10-09.json for editorial direction and replay provenance.

The current action labels are Save pitch, Make a variant and Practice aloud. Spoken wording is above delivery settings. Sources and history expand when needed. Length links and filters retain the return context. Unsaved wording is kept in sessionStorage for the same browser tab, with an explicit restore-or-discard choice when you return. This is temporary recovery, not a backup; save to retain wording permanently. Ctrl+S saves the current pitch.

The default Materials view excludes generated intermediate/build files and ranks named source files ahead of text-only matches. Archived / generated and All materials keep every source accessible. Original categories, paths and files are preserved.

Applications has separate drafts, email reports and agent-settings tabs. The grouped sidebar selects the parent page on detail routes, and the header search is functional. Today uses the same saved sourced shortlist as the daily report; it does not imply fresh verification.

Verification: 146 automated tests passed, including three repair-specific tests for material filtering/ranking and editorial version preservation. Live checks verified save/history, rehearsal, same-tab unsaved recovery, search query handling, filtered-library return, mobile menu, report/settings separation and no horizontal overflow in the 390px pitch views. The private consistent database and pre-edit UI backups are under data/repair-backups/2026-10-09. No application was submitted or approved by this repair.
