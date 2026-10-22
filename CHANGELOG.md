# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/) and the project uses
[semantic versioning](https://semver.org/).

## [0.2.2]

This entry includes the changes of 0.2.0 and 0.2.1.

### Added
- One calendar per activity type (for example Træning, Kamp, Social aktivitet), created
  automatically when a new type appears.
- Buttons to sign up for or decline the team's next activity.
- *Activities* sensor lists the upcoming activities, *Notes* sensor lists the newest notes.
- Sign-up details on the *Next activity* sensor (`my_status`, counts, `max_attendees`, pickup).
- Brand icons, HACS and hassfest validation workflows, release workflow, issue template.
- Debug logging and a troubleshooting guide in the README.

### Changed
- The *Notes* sensor state is now the title of the newest note; the number of notes is the
  `count` attribute.
- The user sensor no longer exposes addresses and birthday, and the *Next activity* sensor no
  longer lists people who have not responded (only the count).
- Activities without an end time are shown as one-hour events.
- Tasks are only fetched for the next three activities.
- Activity names and places are trimmed of stray whitespace.

### Fixed
- Options flow crashed when opened.
- Team devices are linked with `via_device_id`; the deprecated `via_device` made sensors fail to
  load in Home Assistant 2026.9.
- Only the first page of activities was read if the server limited the page size.
- Calendar events with timezone-less times, and wrong credentials now report an
  authentication error.
- Sign-up requests only send the fields the API documents.
- Removed the invalid `domains` key from `hacs.json`; sorted manifest keys for hassfest.

## [0.1.0]

- Initial version by [MrMEEE](https://github.com/MrMEEE/ha-holdsport).
