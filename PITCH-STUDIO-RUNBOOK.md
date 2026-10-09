# Pitch Studio

Open http://127.0.0.1:8765/pitches on this PC, or select Pitch Studio in Founder OS. If the site is stopped, use `Open-Founder-OS.ps1`.

## Work with a pitch

1. Filter by length, audience or scenario, then open a pitch. All audience and scenario names can be changed or replaced with your own.
2. Use Duplicate & adapt to create a separate variant. Change its audience, setting, speaker, length, wording and notes.
3. Save version to retain the edited script. Earlier versions remain in Version history. Restore as new version keeps both the earlier wording and intervening edits.
4. Rehearse uses the current editor text, including unsaved edits. Start, pause, resume or reset the timer. Timing estimates assume 130 words per minute; demonstrations, questions and pauses need actual rehearsal.
5. Copy current text copies the editor wording. Download saved TXT exports the saved version with notes, version ID and source references. Save first if you want the download to contain recent edits.

New pitch starts a blank draft. Choose a preset from 30 seconds through 20 minutes, or enter a custom length of 10 seconds to 120 minutes. Use Archived to hide a pitch from the default library without losing its history; Include archived makes it visible again.

The 14 active starting drafts include the original short pitch and 13 sourced adaptations. The 7-, 10-, 15- and 20-minute entries are timed working outlines, not finished speeches of that duration. Bracketed prompts mark missing evidence, demonstrations, asks or presenter details. They are editable private drafts. Historical claims are not current company facts.

## Use the pitch folder

Materials keeps original source paths and searchable extracted text from the Pitch Competition folder. Open a material and use Adapt in Pitch Studio to start a source-linked draft. Text longer than 40,000 characters is explicitly truncated in the editor; the complete source remains in Materials. A file without extracted text remains a reference for manual adaptation. Decks and binaries are not silently copied or rewritten.

The original folder is `C:\Users\vngia\OneDrive - Umich\Desktop\My startups\Pitch Competition`. This feature writes only to Founder OS. `reports/pitch-studio-manifest.json` links starting drafts to preserved source versions. Source paths remain visible on each draft.

## Persistence and recovery

The existing `pitches` table remains the identity anchor. `pitch_documents` points to the current immutable `pitch_versions` entry. Every save records its parent, sources and an activity event. Original pitches are never rewritten. New legacy agent pitches appear when the library is read. Starter import keys prevent duplicates if `tools/seed_pitch_studio.py` is run again.

If another tab saves first, the editor reports a conflict and keeps your unsaved text. Copy it, reload the latest saved version, then merge the wording. Leaving the page with unsaved edits invokes the browser's leave warning. Immutable versions are retained rather than deleted.

Back up `data/founder.sqlite` consistently using the existing OS backup workflow. The original source paths remain necessary for binary references. No API key is needed for manual editing, curated starting drafts, saving or rehearsal. This studio does not claim to generate arbitrary new pitches automatically.

## Verification

Fixture tests cover immutable history, restore, stale edits, source validation, custom choices, archive filtering, repeat-safe starter keys, legacy agent drafts and HTTP session/CSRF protection. Browser checks cover creating a custom pitch, saving a 95-second duration, reloading the wording, archiving the verification draft and running/pausing the rehearsal timer. Desktop 1280px and phone 390px views were checked for page overflow and console errors. Evidence lives under `.impeccable/review/pitch/` and `reports/pitch-studio-verification.json`.
