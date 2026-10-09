---
name: A Story Founder OS
description: The inherited Pitch OS visual system as implemented in the local Founder workspace.
colors:
  accent: "#176b63"
  accent-hover: "#125950"
  ink: "#182329"
  muted: "#59686b"
  line: "#dee5e4"
  bg: "#f8f9fa"
  paper: "#fff"
  sidebar: "#edf1f0"
  nav-text: "#4a5b59"
  nav-hover: "#e1e8e6"
  positive-surface: "#e6f1ef"
  review-surface: "#fff0da"
  review-text: "#805015"
  warn: "#855417"
  notice-surface: "#fff9ed"
  notice-line: "#ead8b8"
  notice-text: "#654c29"
typography:
  headline:
    fontFamily: "Segoe UI, Arial, sans-serif"
    fontSize: "30px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.035em"
  title:
    fontFamily: "Segoe UI, Arial, sans-serif"
    fontSize: "20px"
    fontWeight: 700
    lineHeight: 1.3
  body:
    fontFamily: "Segoe UI, Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
  control:
    fontFamily: "Segoe UI, Arial, sans-serif"
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1.5
  score:
    fontFamily: "Segoe UI, Arial, sans-serif"
    fontSize: "20px"
    fontWeight: 650
    lineHeight: 1.25
  label:
    fontFamily: "Segoe UI, Arial, sans-serif"
    fontSize: "12px"
    lineHeight: 1.5
rounded:
  tag: "4px"
  field: "6px"
  button: "7px"
  navigation: "8px"
  surface: "10px"
spacing:
  compact: "4px"
  control-gap: "9px"
  field-gap: "12px"
  panel-mobile: "18px"
  panel: "24px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.paper}"
    typography: "{typography.control}"
    rounded: "{rounded.button}"
    padding: "9px 15px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
    textColor: "{colors.paper}"
  button-secondary:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.button}"
    padding: "9px 15px"
  view-button:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    typography: "{typography.control}"
    rounded: "{rounded.button}"
    padding: "7px 10px"
  view-button-selected:
    backgroundColor: "{colors.positive-surface}"
    textColor: "{colors.accent}"
  input-filter:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "7px 9px"
  nav-link:
    textColor: "{colors.nav-text}"
    typography: "{typography.control}"
    rounded: "{rounded.navigation}"
    padding: "11px 12px"
  nav-link-selected:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.accent}"
  tag-review:
    backgroundColor: "{colors.review-surface}"
    textColor: "{colors.review-text}"
    rounded: "{rounded.tag}"
    padding: "4px 7px"
  tag-positive:
    backgroundColor: "{colors.positive-surface}"
    textColor: "{colors.accent}"
    rounded: "{rounded.tag}"
    padding: "4px 7px"
  panel:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.surface}"
    padding: "24px"
---

# Design System: A Story Founder OS

## Overview

**Creative North Star: "Inherited Pitch OS workspace"**

This is a scan of the finished Founder OS interface, preserving the established Pitch OS teal, light surfaces, sans typography and sidebar. The name describes the incumbent system; it does not introduce a new identity or an approved creative metaphor.

The interface uses flat work panels, compact data rows and readable labels. Brand expression comes from the teal actions and the A Story mark. Recommendation, uncertainty and evidence are presented as working information alongside the controls that act on them.

**Key Characteristics:**
- Teal actions on a light neutral workspace.
- Flat, bordered white work panels.
- A compact sans hierarchy with aligned numerals.
- Status words and explicit uncertainty alongside values.
- Sidebar navigation that becomes a horizontal mobile strip.

## Colors

The palette has one brand accent, cool neutrals and warm semantic review surfaces. The frontmatter records the implemented values; no secondary brand palette is inferred.

### Primary
- **Workspace Teal** (`accent`): primary actions, links, current navigation text, focus outlines and confirmed state text.
- **Deep Action Teal** (`accent-hover`): primary button hover.
- **Pale Teal State** (`positive-surface`): selected view buttons, positive recommendation tags and successful feedback.

### Neutral
- **Workspace Ink** (`ink`): headings, main content and secondary actions.
- **Quiet Text** (`muted`): supporting dates, labels and explanatory text.
- **Cool Field** (`bg`) and **White Paper** (`paper`): page ground and work panels.
- **Soft Sidebar** (`sidebar`): navigation ground, secondary hover, quiet row divisions, neutral tags and progress track.
- **Fine Divider** (`line`): major panel borders, input strokes and table headings.
- **Navigation Text** (`nav-text`) and **Navigation Hover** (`nav-hover`): sidebar navigation defaults and hover.

### Semantic review
- **Warm Review** (`review-surface`, `review-text`): REVIEW badges and error feedback.
- **Verification Warning** (`warn`): unknown eligibility status words.
- **Confirmation Notice** (`notice-surface`, `notice-line`, `notice-text`): the early notice that company facts need owner review.

**The Status Words Rule.** Color supports readable status text; eligibility remains labeled Meets, Fails or Unknown.

## Typography

**Body and interface font:** Segoe UI, Arial, sans-serif. The implementation uses the platform sans throughout and has no separate decorative display face.

The hierarchy is compact rather than a mathematical scale. Page headings use the frontmatter headline role; section headings use title. Third-level headings are bold (16px). Body paragraphs cap their measure (75ch). Data rows and buttons are slightly smaller (14px), while supporting labels are compact (12px); score captions are smaller (11px).

The page headline reduces on mobile (26px). Summary numbers are prominent (28px, weight 650), lead facts are medium (23px), and the mobile row score grows (22px). Tables, scores and summaries use tabular numerals. These are data emphasis treatments, not a new display typography identity.

## Layout

The desktop shell has a fixed sidebar (236px) and a flexible content track. The sidebar is sticky, reaches the viewport height and uses a cool neutral ground. A white top bar separates workspace context from the main content. Content is centered with a maximum width (1440px) and desktop padding (32px 36px 60px).

Panels use generous internal padding and a repeated separation (24px). The summary is a four-column grid. The detail page uses a wider narrative column and a narrower readiness/decision column (1.5fr and 1fr, with a 280px minimum on the latter); paired panels use equal tracks. Buttons and filters wrap as space changes.

At a maximum width (1080px), the sidebar narrows (205px), content padding reduces (26px 24px), and detail becomes one column. At a maximum width (720px), the shell becomes a vertical flow, the sidebar loses sticky positioning, the side note and top bar hide, and navigation becomes a horizontally scrollable strip. Main content padding is compact (24px 16px), panels reduce padding, summary becomes two columns and paired panels stack.

On mobile, opportunity table headings hide and each row becomes a two-column record with its program name spanning both columns. Fit captions remain self-contained. Value, Deadline and Founder work gain visible labels. Detail sections reorder so Application readiness appears before fit and eligibility, followed by scoring, sources, decision and history. This ordering is implemented for the current detail structure and must be reconsidered if sections change.

## Elevation & Depth

The implemented system has no box shadows. White panels, sidebar tone, warm notices and fine borders establish depth. Hover changes background or text color without movement. There are no authored animation or transition tokens.

**The Flat Workspace Rule.** Reuse the existing tonal surfaces and fine borders when extending this workspace.

## Shapes

Small rounded rectangles establish the form language. Panels and the A Story mark share the surface radius; navigation, buttons, fields and tags use the smaller frontmatter steps. Panel and control borders are fine (1px). Notices remain rectangular. Progress tracks are compact (9px high) with rounded ends (4px).

## Components

### Buttons

Compact and direct. Primary actions use white text on teal with a darker teal hover. Secondary actions use white paper, ink text and a divider border; hover shifts to the sidebar tone. View buttons have transparent default backgrounds and pale teal selected backgrounds. Buttons use the inherited control typography. Disabled action buttons reduce opacity (.55) and show the waiting cursor during a request.

Interactive buttons, links and fields show a visible teal keyboard outline (2px) with an offset (4px). Action groups wrap; mobile action controls grow to use available width.

### Chips

Tags are compact status labels (11px, weight 700, letter spacing .025em) with no pill shape. Neutral, review and positive treatments repeat the semantic palette. Tags remain words rather than replacing state with a color or icon.

### Cards / Containers

Work panels use white paper, the surface radius and a divider border. Desktop and mobile padding follows the panel spacing tokens. Section titles align the heading with its related link or action. Records use dividing lines, and the final record removes its trailing divider.

### Inputs / Fields

Filters use visible labels, white fields, a fine border and the field radius. Desktop filter fields have a minimum width (110px) and maximum width (170px); mobile labels flex with a minimum width (125px), and controls fill their tracks. Decision selects and textareas fill the panel width; the reason textarea is required. Native select, number and date controls retain their browser behavior. Input and textarea caret color is teal.

### Navigation

Navigation links use medium-weight control text, soft corners and a tonal hover. The selected link uses white paper and teal text. Navigation is a semantic nav with the accessible name Founder OS; the mobile strip preserves the same destinations with smaller text and padding. Current selection is implemented by visual active styling.

### Opportunity scores and evidence

Fit values use aligned numerals with an explicit A Story fit caption. Unresolved fit displays the actual lower–upper range and the explanation “Range includes unknown points.” Detail scoring retains reasons, component weights, evidence coverage and unknown component points. Eligibility is separately labeled; a range is never represented as a confirmed score.

Opportunity rows include official verification state and a last-checked date. Source details include linked evidence and readable timestamps; the time element retains the exact timestamp in its datetime attribute and title. Known benefit descriptions remain separate from usable value; unknown usable amounts remain visible rather than becoming zero or invented funding.

**The Visible Uncertainty Rule.** Keep unknown fit, eligibility, readiness, effort and usable value explicit in the relevant working component.

### Readiness and owner decisions

Readiness uses native progress with an accessible label only when a percentage is known. Unknown requirements show explanatory text without a fabricated progress value. Materials are grouped as Ready, Needs adaptation and Missing.

Owner proposals show the exact proposal, evidence status and verification context; raw evidence is behind optional disclosure. Approval controls name the exact proposal and use a native confirmation dialog. The Start application action is followed by text explaining that it creates an internal draft and that submission requires a separate owner action. Feedback is delivered through a polite live status region. These are documented UI boundaries; service enforcement, scheduling and research execution are outside design scope.

## Do's and Don'ts

### Do:
- **Do** preserve the inherited teal, ink, light field, white panels and cool sidebar.
- **Do** keep supporting status text beside semantic colors.
- **Do** preserve unknown values, score ranges and the explanation of unresolved points.
- **Do** show readable evidence dates while retaining exact timestamps.
- **Do** keep owner proposal wording and the internal draft boundary visible beside the action.
- **Do** retain visible keyboard focus, labeled fields and live action feedback.

### Don't:
- **Don't** promote advertised benefits into confirmed usable value.
- **Don't** hide uncertainty when replacing a table with mobile records.
- **Don't** treat a design review as evidence that research or scheduling runs correctly.
- **Don't** introduce a new brand identity or decorative display face into this ordinary extension.
