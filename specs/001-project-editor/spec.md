# Feature Specification: Project Editor

**Feature Branch**: `001-project-editor`

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "Project editor for a research team, in front of an upstream records API we cannot change. P1 – List projects. P1 – Edit a project (name, sector, country, stage, key dates); fields not shown in the form must survive every save intact. P1 – Safe concurrent editing: different fields both survive; same field, the second saver is shown their value vs. the current value and decides; also holds when the record was changed by the nightly import. P2 – Unreliable upstream: slow reads show a loading state; an ambiguous save is never reported as success or failure without checking the record's actual state. P3 – (cut candidates) auth/user identity, audit history, real-time presence. Success: no lost updates in the two-editor scenarios; a timed-out save ends in a definite state; linked companies are never dropped."

## Clarifications

### Session 2026-10-07

- Q: When two people edit the key dates of the same project, what counts as "the same field"? → A:
  Each key date is a field, identified by its label (case- and whitespace-insensitive). Renaming a
  label is deleting one field and adding another. If a project has duplicate labels, its entire
  list is treated as a single field. (Confirms FR-015 and FR-016 as written.)
- Q: Between re-reading the record and writing it, another write can land and be overwritten
  unnoticed; is that gap accepted or must this version close it? → A: Accepted. Keep it as short
  as possible, document it in `DECISIONS.md`, and re-read the record after every write; if it does
  not match what was written, tell the editor. No new shared infrastructure.
- Q: When a save times out and the check shows it was not applied, does the tool retry by itself
  or tell the editor? → A: One automatic retry, after re-evaluating the save against the record's
  current state. If that also times out and is still not applied, the editor is told "not saved".
- Q: If a save times out and the tool cannot read the record to check what happened, what is the
  editor told? → A: An explicit third outcome, "unconfirmed": edits are kept in the form and the
  editor can check again. (Confirms FR-021 and User Story 4 scenario 6 as written.)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - List projects (Priority: P1)

An editor opens the tool and sees every project in the records system with its id, name, sector,
country and stage, and opens one of them to edit it.

**Why this priority**: It is the entry point to everything else; without it no project can be
reached.

**Independent Test**: With the records system running on its seed data, open the tool and confirm
all 30 projects are listed with the five columns, and that selecting one opens that project.

**Acceptance Scenarios**:

1. **Given** the records system holds 30 projects, **When** the editor opens the tool, **Then**
   all 30 are listed, each showing id, name, sector, country and stage.
2. **Given** the list is shown, **When** the editor selects a project, **Then** that project's
   edit form opens with its current values.
3. **Given** the records system cannot be reached, **When** the editor opens the tool, **Then**
   they see a clear error with a way to retry, not an empty list.

---

### User Story 2 - Edit a project (Priority: P1)

An editor opens a project, changes any of its name, sector, country, stage and key dates (adding,
editing or removing dates), and saves. Everything about the project that the form does not show,
such as its linked companies, is exactly as it was before the save.

**Why this priority**: Keeping records accurate is the purpose of the tool.

**Independent Test**: Edit each core field and add, change and remove a key date on one project,
save, reload, and confirm the changes are stored and the project's linked companies are unchanged.

**Acceptance Scenarios**:

1. **Given** a project is open, **When** the editor changes its name and stage and saves, **Then**
   the stored project has the new name and stage and every other field is unchanged.
2. **Given** a project with three key dates, **When** the editor changes one date, removes
   another, adds a new one and saves, **Then** the stored project has exactly the resulting set of
   key dates.
3. **Given** a project with linked companies, **When** the editor saves any change, **Then** the
   stored linked companies are identical to what the records system held at the moment of saving.
4. **Given** the editor has cleared the name or entered a key date with no label or no valid date,
   **When** they try to save, **Then** the save is refused with a message on the offending field
   and nothing is sent.
5. **Given** the editor has made no changes, **When** they save, **Then** nothing is written.

---

### User Story 3 - Safe concurrent editing (Priority: P1)

Two editors have the same project open. Each saves without knowing about the other. Changes to
different fields are both kept. When both changed the same field, the editor who saves second is
shown their value next to the value now stored, and chooses. The same protection applies when the
record was changed by the nightly import instead of by another editor.

**Why this priority**: The records system silently keeps only the last save. Preventing lost
updates is the core value of this tool.

**Independent Test**: Open the same project in two browser windows, make edits in both, save one
then the other, and check the stored project against the scenarios below.

**Acceptance Scenarios**:

1. **Given** editors A and B opened the same project, **When** A changes the name and saves, and
   B then changes the country and saves, **Then** the stored project has A's name and B's country
   and B is told the record had changed and was merged.
2. **Given** A and B opened the same project, **When** A changes the stage and saves, and B then
   changes the stage to a different value and saves, **Then** B's save is not applied; B is shown
   their stage next to the stored stage and must choose one before anything is written.
3. **Given** B is resolving a conflict on one field and also changed other, non-conflicting
   fields, **When** B makes their choice and confirms, **Then** the chosen value and all of B's
   non-conflicting changes are stored, along with A's non-conflicting changes.
4. **Given** A and B opened the same project, **When** A changes the date of "Financial close" and
   B changes the date of "Tender launch", **Then** both changes are stored.
5. **Given** A and B opened the same project, **When** both change the date of "Financial close"
   to different dates, **Then** the second saver gets a conflict on that key date only.
6. **Given** A and B opened the same project, **When** A removes a key date and B changes that
   same key date's date, **Then** the second saver gets a conflict on that key date.
7. **Given** A and B opened the same project, **When** both make the identical change to a field,
   **Then** the second save succeeds with no conflict.
8. **Given** an editor opened a project and the nightly import then changed its stage directly in
   the records system, **When** the editor changes the name and saves, **Then** the import's stage
   and the editor's name are both stored; and if the editor had also changed the stage, they get
   a conflict exactly as in scenario 2.
9. **Given** B resolved a conflict and confirms, **When** the record has changed yet again in the
   meantime, **Then** the check runs again against the newest state and any new conflict is shown.

---

### User Story 4 - Unreliable records system (Priority: P2)

The records system is sometimes slow to return a project and sometimes answers a save with a
gateway timeout that does not say whether the save happened. The editor always knows what is going
on: a slow load looks like loading, and a timed-out save is checked before anything is reported.

**Why this priority**: Roughly one save in ten times out. Reporting those wrongly either loses
work (false success) or causes duplicate or conflicting retries (false failure).

**Independent Test**: Force the slow path and both timeout outcomes (save applied, save not
applied) and confirm what the editor is told matches the stored record each time.

**Acceptance Scenarios**:

1. **Given** the records system takes about two seconds to return a project, **When** the editor
   opens it, **Then** a loading state is shown until the form is ready.
2. **Given** a save times out but was in fact applied, **When** the outcome is checked, **Then**
   the editor is told the save succeeded and sees the stored values.
3. **Given** a save times out and was not applied, **When** the outcome is checked, **Then** the
   save is re-evaluated against the record's current state and attempted once more without the
   editor doing anything; if that attempt succeeds the editor is simply told the save succeeded.
4. **Given** a save timed out, was not applied, and the single automatic retry also times out
   without being applied, **When** the outcome is checked, **Then** the editor is told the save
   did not happen, their edits are still in the form, and they can save again.
5. **Given** a save timed out and was not applied, **When** the re-evaluation before the automatic
   retry finds a conflict, **Then** nothing is written and the editor is shown the conflict.
6. **Given** a save times out and the outcome cannot be checked because the records system stays
   unreachable, **When** the checking gives up, **Then** the editor is told plainly that the
   outcome is unconfirmed, their edits are kept, and they can check again. It is never shown as
   success or as failure.

---

### Edge Cases

- A project is opened by its id but no longer exists: the editor sees "not found" and a way back
  to the list.
- The records system rejects a save as invalid: the editor sees the reason; their edits are kept.
- An editor renames a key date's label while another editor changes that key date's date: treated
  as one editor removing the entry and the other editing it, so the second saver gets a conflict.
- Two editors each add a key date with the same label but different dates: conflict on that key
  date for the second saver. Same label and same date: no conflict.
- A project holds two key dates with the same label (possible in the records system): its key
  dates cannot be told apart individually, so for that project the whole list of key dates is
  treated as a single field.
- The order of key dates is not a field: reordering alone is never a conflict and never a change.
- Linked companies were changed by the nightly import while the editor had the form open: the
  import's linked companies are kept by the editor's save.
- Another write lands in the instant between the tool's check and its own write: the tool's write
  wins in the records system. If a later write then changes the record before the tool reads it
  back, the editor is warned (FR-025). An overwrite that leaves no visible trace is not detected;
  this is the accepted limit described in Assumptions.
- After a timed-out save, the record differs both from what the editor tried to save and from what
  it was before (someone else wrote in between): the save is treated as not confirmed and goes
  through the normal merge and conflict check against the newest state.

## Requirements *(mandatory)*

### Functional Requirements

**Listing and viewing**

- **FR-001**: The system MUST list all projects, showing id, name, sector, country and stage.
- **FR-002**: Editors MUST be able to open one project from the list and see its current name,
  sector, country, stage and key dates.
- **FR-003**: The system MUST show only the fields an editor needs; other fields held by the
  records system are not displayed.

**Editing and saving**

- **FR-004**: Editors MUST be able to change a project's name, sector, country and stage, where
  sector and stage are chosen from the values the records system allows.
- **FR-005**: Editors MUST be able to add, edit (label and date) and remove key dates.
- **FR-006**: The system MUST refuse a save when the name or country is empty, or a key date has
  an empty label or an invalid date, and MUST say which field is wrong. It MUST also refuse a save
  in which two key dates share a label, but only when the editor changed the key dates: a project
  that already holds repeated labels in the records system can still have its other fields edited.
- **FR-007**: Every save MUST leave all fields that the form does not show, including linked
  companies, equal to their value in the records system at the moment of saving.
- **FR-008**: A save with no changes MUST NOT write anything.

**Concurrent editing**

- **FR-009**: Every save MUST be evaluated against the record's state at the moment of saving,
  not the state the editor loaded, by comparing three things: what the editor loaded, what the
  editor submitted, and what is stored now.
- **FR-010**: A field the editor did not change MUST keep its currently stored value, whoever
  changed it and by whatever route (another editor or the nightly import).
- **FR-011**: A field the editor changed and nobody else changed since the editor loaded it MUST
  take the editor's value.
- **FR-012**: A field changed both by the editor and by someone else since loading, to different
  values, is a conflict. On a conflict the system MUST write nothing and MUST show the editor,
  for each conflicting field, their value and the currently stored value.
- **FR-013**: The editor MUST choose, per conflicting field, between their value and the stored
  value; only after that MAY the save proceed, and it MUST be evaluated again under FR-009.
- **FR-014**: A field changed by both sides to the same value MUST NOT be treated as a conflict.
- **FR-015**: For conflict purposes the fields are: name, sector, country, stage, and **each key
  date individually, identified by its label** (compared ignoring case and surrounding spaces).
  Adding, removing, or changing the date of the key date with a given label is a change to that
  one field. Renaming a label is removing one key date and adding another.
- **FR-016**: When a project's stored or loaded key dates contain a repeated label, the system
  MUST treat that project's whole key-date list as one field.
- **FR-017**: When a save was merged with someone else's changes, the editor MUST be told, and the
  form MUST then show the stored result.
- **FR-018**: The guarantees in FR-009 to FR-017 MUST NOT depend on anything remembered by the
  tool between requests: they must hold when consecutive requests are handled by different
  instances of the tool and when the record is changed without the tool's involvement.
- **FR-025**: After every write the system MUST read the record back and compare it with what it
  wrote. If they differ, the editor MUST be told that the record changed during their save and
  MUST be shown the stored state; the save MUST NOT be reported as a plain success. If the write
  was acknowledged by the records system but the read-back itself cannot be completed, the
  acknowledgement is confirmation enough and the save is reported as saved.

**Unreliable records system**

- **FR-019**: While a project or the list is loading, the system MUST show a loading state.
- **FR-020**: When a save gets an ambiguous answer (gateway timeout), the system MUST determine
  the record's actual state before telling the editor anything about the outcome.
- **FR-021**: Once checking and the single automatic retry (FR-022) are over, the editor MUST be
  told exactly one of: saved (stored record equals what was being saved); not saved (edits kept in
  the form, ready to save again); or unconfirmed
  (the check itself could not be completed; edits kept; the editor can check again).
- **FR-022**: When the check shows a timed-out save was not applied, the system MUST retry it
  automatically exactly once, and only after re-evaluating it against the record's current state
  under FR-009 to FR-016. If that re-evaluation finds a conflict, nothing is written and the
  conflict is shown. The system MUST NOT retry more than once per save request.
- **FR-023**: When the records system is unreachable or reports an error, the editor MUST see a
  clear message and MUST NOT lose what they typed.

**Boundary**

- **FR-024**: The editor's browser MUST communicate only with this tool, never with the records
  system, and the records system's access key MUST NOT be exposed to the browser.

### Key Entities

- **Project**: an infrastructure project record owned by the records system. Has an id; editable
  core fields (name, sector, country, stage); a list of key dates; a list of linked companies;
  and about fifteen further fields owned by other systems that this tool neither shows nor changes.
- **Key date**: a labelled milestone of a project (label, calendar date). Has no identifier of its
  own in the records system; this tool identifies it by its label within its project.
- **Linked company**: a company and its role on a project. Not editable here; must pass through
  every save untouched.
- **Edit**: one editor's intended change to one project — the state they loaded plus the state
  they submitted. Exists only for the duration of a save.
- **Conflict**: a field of an edit where the editor's value and the stored value both differ from
  what the editor loaded, and from each other. Carries both values for the editor to choose from.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In every two-editor scenario of User Story 3, where the two saves do not overlap in
  time, zero changes are lost: each change either ends up stored or is shown to the second saver
  as a conflict to decide. Saves that overlap within the accepted check-then-write window (see
  Assumptions) are outside this guarantee.
- **SC-002**: Zero conflicts are resolved without the second saver's explicit choice.
- **SC-003**: The same outcomes hold when the other change comes from a direct write to the
  records system, and when the two editors' requests are handled by different instances.
- **SC-004**: 100% of timed-out saves end with the editor being told one of saved, not saved or
  unconfirmed, and what they are told matches the stored record whenever it could be read.
- **SC-005**: Across all saves in all scenarios, a project's linked companies and non-displayed
  fields are never altered or dropped by this tool.
- **SC-006**: An editor can find a project in the list, change a field and a key date, and have it
  saved in under one minute when there is no conflict.
- **SC-007**: A slow load never shows a blank or frozen screen: a loading state is visible within
  one second of opening a project.

## Assumptions

- **What "the same field" means for key dates** is decided here as *one key date, identified by
  its label* (FR-015), because the records system gives key dates no identifier, position changes
  whenever anyone adds or removes an entry, and the label is what an editor means by "the
  Financial close date". Treating the whole list as one field would raise a conflict whenever two
  editors touch different milestones, which is the common case. The cost is that a rename is seen
  as remove-plus-add. This choice and its reasoning are to be restated in `DECISIONS.md`.
- **A small window remains** between checking the record's current state and writing to it, in
  which another write could land and be overwritten, because the records system offers no
  conditional write. It cannot be closed without a change to the records system or shared
  coordination between instances, and no coordination between instances would cover the nightly
  import. It is accepted for this version, kept as short as possible, partly detected by reading
  the record back after each write (FR-025), and documented in `DECISIONS.md`.
- **Out of scope (cut)**: sign-in and user identity, so conflicts say "someone else" rather than a
  name; audit history of who changed what; real-time presence or live updates showing that another
  editor has the project open. Also out of scope: creating or deleting projects, editing linked
  companies, and search, filtering or paging of the list (about 30 projects).
- **A timed-out save is assumed to have been applied, or not, by the time the timeout is
  received.** That is how the records system behaves today. If it could apply a write later, a
  check made right after the timeout could report "not saved" for a save that then lands.
- All editors are trusted internal staff with equal rights to edit every project.
- The set of allowed sectors and stages is fixed and known in advance.
- The records system's data resets when it restarts; this tool keeps no data of its own.
