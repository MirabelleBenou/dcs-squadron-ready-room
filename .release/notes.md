Every time now reads in the wing's time zone, the Pilot Manual gains a Help annex, and four fixes.

**A Help annex in the Pilot Manual**
- The Pilot Manual has a new Help annex: a glossary of the Ready Room's words, each pointing to the page that explains it, and answers to the most common difficulties, from a refused sign-in to a missing flight.

**Pilot Manual brought up to date**
- The Pilot Manual now explains that times are read in the wing's time zone, with your own time added in the event sheet and form, and shown on hover in the Command Centre.
- Its Configuration chapter describes the read-only Server folders block, and its Rights chapter notes that the list of access roles is managed on that screen.

**Command Centre times in the wing's time zone**
- The Command Centre (members, archives and backups, journal, server agent, settings) and invitations show their dates and times in the wing's time zone, whatever the time zone of your device.
- Where your own time differs, hovering over a time shows it.

**Wing dates in the wing's time zone**
- The Wing home page, member files, the pilots' logbook and campaigns show their dates in the wing's time zone, whatever the time zone of your device.

**Forward after a link from an event**
- Fixed: after opening a debrief from an event sheet and changing tab, the browser's Forward button no longer brings back a screen you had left, and ‹ returns to the event sheet.

**An ACMI file that cannot be read**
- Fixed: uploading as ACMI a file that is not a Tacview archive is now refused with a clear message instead of a server error.

**Discord messages after a restart**
- Fixed: when the server restarted, an event's Discord message could keep its old answers until the next change; the Ready Room now follows Discord's sending limits.

**Times in the wing's time zone**
- The Board, the Weekly Table and the event sheet show every time in the wing's time zone, whatever the time zone of your device; when it differs, the event sheet and the event form also give your local time.
- Fixed: an event created or edited from a device in another time zone was saved at the wrong time.

**Access rights checked by a test**
- Nothing visible changes: an automated test now checks, for every address of the application and every kind of member, who gets in and who is refused.

## Version numbers

Each release is a GitHub release tagged `RR-V<major>.<minor>.<patch>`:

- **Major** (**x**.0.0): a redesign, or a file format that breaks.
- **Minor** (1.**x**.0): a new tool, screen or feature, or a change visible everywhere.
- **Patch** (1.2.**x**): fixes.

The footer of the home page shows the version the server runs: `RR-V1.2.0` for a release, `RR-V1.2.0+3` for the third update installed on the server since that release.
