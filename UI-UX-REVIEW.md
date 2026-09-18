# DriveDesk: UI/UX audit and redesign brief

Date: 2026-09-18

## Implementation progress

The working tree now contains the first redesign: a light macOS-inspired theme, a simplified painted brand mark, sidebar navigation, collapsible folder tree, Back/Forward history, larger file rows, selection summaries, explicit upload/download buttons, resizable and expandable Transfers, long-text details, concurrency/bandwidth controls and an optional Windows keep-awake control.

Mounted monitoring now uses authenticated background POST requests and reads VFS queue/cache state. Unknown state remains visible. Closing or unmounting prompts before interrupting work. Standalone rclone jobs have same-process suspend/resume controls; shared API uploads pause between chunks. Long pauses can expire remote sessions. This is not recovery after restart and does not pause mounted filesystem operations.

Validation: 43 tests passed outside the restricted filesystem sandbox, including local child-process suspension/resumption, cancellation while paused, and VFS queue/error interpretation. Offline populated visual fixtures were inspected at 1380x820 and 1100x740. Real Google transfer performance, WinFsp mount execution, high-DPI/native macOS appearance and restart recovery remain unverified. No new release has been published for this redesign.

Remaining roadmap: independent cloud/cloud panes, durable restart recovery, complete Drive capability coverage, saved sync/schedules, broader accessibility and platform verification. The existing audit below records the baseline and planned outcomes; it is not a claim that every item has been implemented.

## Scope and evidence

This is a source-based review of app.py, drive_backend.py, google_api.py, tests, and the release workflow, informed by the user's upload and mount experience. It is not a live visual, accessibility, throughput, or cross-platform certification. Recommendations below are proposed work, not shipped functionality.

Preserve the useful foundations: dual panes, drag-and-drop, multiple account connections, shared-folder browsing, saved links, conflict choices, and structured rclone progress. Keep the DriveDesk branding and use consistent icons.

## Priority findings

| Priority | Evidence / current behavior | User impact | Required change |
| --- | --- | --- | --- |
| P0 | refresh_mount_stats requests core/stats?short=true, then reads transferring | Active filenames are omitted by the requested stats format | Authenticated POST requests with full stats, tested against bundled rclone |
| P0 | Mount monitor ignores vfs/stats and vfs/queue; polling failures are silently ignored | Idle/stale status can conceal pending uploads | Track queued, uploading, retrying, errored, unknown, and confirmed drained states |
| P0 | closeEvent cancels workers and terminates mounts immediately | Closing the window interrupts work | Close-to-tray option; pending-work prompt; explicit quit/unmount with upload state checks |
| P0 | Mount HTTP polling runs synchronously on the Qt timer thread | Navigation can freeze for each unavailable mount | Background polling with bounded timeouts, no overlapping polls, timestamps and stale state |
| P0 | Mount starts with rc-no-auth; stderr is piped but not continuously drained | Unnecessary local control exposure and potential process blocking | Loopback authentication and continuously consumed, bounded logs |
| P0 | Direct shared uploads differ from regular rclone uploads; settings only apply to regular transfers | Inconsistent limits, retries and performance | Common transfer service with explicit backend capabilities; verified resumable upload recovery |
| P0 | Download range retries lack robust range/length validation | A successful-looking copy is not enough evidence of file integrity | Validate offsets, response lengths and final file integrity; test interrupted transfers |
| P1 | Cloud location field is read-only; navigation mainly supports Up | Repeated browsing is cumbersome | Breadcrumbs, Back/Forward, editable location mode and per-pane history |
| P1 | Panes are fixed to local vs cloud | Cannot use the same interaction for account-to-account work | Each pane selects a local location or cloud account independently |
| P1 | Search and sync explicitly reject shared/link views | Features disappear exactly where user works | Capability-aware search and sync support for each Drive location |
| P1 | File rows are rebuilt item-by-item; no sort setup in FilePane | Large folders need performance and ordering improvements | Model/view table, incremental population, numeric/date sorting, retain selection and scroll |
| P1 | Transfer panel capped at 232 pixels; nine columns | Queue is cramped and filenames compete with controls | Resizable bottom drawer plus full Transfers page; expandable file details |
| P1 | Options use free-text fields for rates and concurrency | Invalid values and unclear units | Validated numeric controls, explicit units and separate upload/download limits |
| P1 | Reported speed can be a whole-job average; binary sizing is labelled MB | Comparisons with Explorer are confusing | Current smoothed rate and separately labelled average; consistent MB/s or MiB/s, optional Mbps |
| P1 | State is held in memory and actions focus on cancel | No dependable recovery/history workflow | Durable queue, retry failed, recover after restart; pause semantics defined per backend |
| P1 | Sync mixes copy, destructive mirror, move and bisync in a dropdown | Consequences are hard to assess | Saved sync profiles with a changes table and explicit deletion/conflict review |
| P1 | Workflow builds/publishes each platform independently without a test gate | Tags/queued runs have been mistaken for completed releases | Test, build all required assets, verify them, then publish one completed release |
| P2 | Hard-coded dark colors, 13px text and small icon buttons | Readability and scaling need verification | Semantic theme tokens, system/light/dark, visible focus, density options, keyboard and high-DPI checks |

## Proposed workspace

```text
DriveDesk                         Search current location        Settings
--------------------------------------------------------------------------
Navigation     | Left pane                     | Right pane
 Files         | Account/location selector     | Account/location selector
 Transfers (3) | Back Forward Up  breadcrumbs  | Back Forward Up breadcrumbs
 Mounted drives| Filter / sort / view          | Filter / sort / view
 Sync & backup | Files                         | Files
 Accounts      |                               |
 Favorites     | Selection summary             | Selection summary
--------------------------------------------------------------------------
Transfer drawer: Active | Queued | Needs attention | Completed
 File / folder    Direction    Progress    Current speed    ETA    Actions
--------------------------------------------------------------------------
Upload / download totals        3 uploads pending · Keep laptop awake
```

Use a small persistent navigation sidebar. Account and location selection belong to each pane. Separate global settings from actions on selected files. Allow a single-pane mode on small windows. Save splitter sizes, visible columns, tabs, selection and last locations per account.

Use subtle 120–180 ms transitions for drawer and selection changes, disabled under reduced motion. Smoothness primarily requires nonblocking I/O and incremental rendering. Loading placeholders must differ from empty folders and errors. Stale requests must never replace a newer location.

## Controls: toggles, sliders and selectors

| Setting | Control | Behavior |
| --- | --- | --- |
| Limit upload / download | Separate toggles + slider + numeric field | Show units and exact value; disabled limit means unlimited; communicate active-job applicability |
| Concurrent files | Stepper, proposed 1–16 range | Default 4, bounded by backend and resource limits; benchmark before raising defaults |
| Keep awake during transfers | Toggle | Cover queued mounted uploads and retries; release wake request when work drains; do not claim to override lid-close policy |
| Close to tray | Toggle | Explain that app and transfer engine remain running |
| File selection | Optional checkboxes | Use checkboxes, not switches, for selecting multiple items |
| Mount source | Selector | My Drive / Shared with me / specific linked folder; clear incompatible path when source changes |
| Auto-mount saved drive | Toggle per mount profile | Validate account, drive letter, cache and dependency before mounting |
| Notifications | Separate completion/error toggles | Errors remain visible in the queue even with notifications off |
| Appearance | System / Light / Dark selector | Comfortable / Compact density and text scaling |
| Conflict handling | Ask / Skip / Replace / Keep both selector | Preview actual affected items; do not make destructive behavior a casual toggle |

A slider must never imply that moving it increases internet speed. Upload chunk size and checker counts belong in Advanced until benchmarks justify exposing them.

## Google Drive coverage

Make an explicit capability matrix for My Drive, Shared with me, Shared Drives (a distinct Google feature), shortcuts and linked folders. Verify list/search/upload/download/rename/delete/move/copy/export/mount/sync independently for each. Represent files by account + file ID, not display path alone; duplicate names and shortcuts make path-only routing ambiguous.

Required: owner and permission badges, disabled actions with reasons, share-link opening, Shared Drives navigation, Google Docs export-format selection, account quota display, reconnect flow, and correct destination account labels. A transfer must retain its original account even when the user switches panes.

Add next: Drive-to-Drive copy/move with capability checks, bookmarks, recent locations, tabs, quick image/PDF previews, filename/type/date/size filters and search scope selection. Explain whether a cloud copy is server-side or passes through this computer; never promise universal server-side copying.

Later: saved backup schedules, versioned backups, integrity verification reports, optional encryption with recovery-key onboarding, bandwidth schedules and diagnostic export with secrets removed. Broad provider support comes after reliable Google Drive coverage.

## Transfer center contract

Every operation has a persistent ID, origin (app or mount), account, source, destination, state, bytes, current rate, average rate, ETA and last update. Mounted writes distinguish copying into local cache from uploading to Google. Never label every rclone transfer an upload.

Use core/stats for current transfer details, vfs/stats for cache queue/error counters, and vfs/queue for pending writeback entries. Missing telemetry means Unknown, never Idle. Zero active files alone does not establish completion. A completion indicator requires fresh successful telemetry, no pending/in-progress writebacks, no unresolved errors, and consideration of files still being written. Scope the message to monitored drives, not the entire laptop.

Provide retry failed, retry one, clear completed, open source/destination, details/logs and persistent history. Queue-level pause stops new jobs; in-flight pause/resume needs explicit backend support and must not be faked by cancelling. Show cache space and upload backlog. Warn before quitting or unmounting with pending/unknown state. A keep-awake switch complements status visibility; lid-close behavior remains OS-controlled.

## Implementation sequence and acceptance

1. Reliability foundation: fix mount telemetry, shutdown, authenticated background polling, and transfer state persistence. Verify real queued/retrying writes, lost telemetry and process exit. Do not release a safe-to-close claim before these pass.
2. Workspace redesign: sidebar, independent panes, breadcrumbs/history, resizable transfer drawer, selection actions and typed settings. Verify navigation during polling and transfers, back/forward state, keyboard paths and 125–200% scaling.
3. Drive completeness: permission-aware ID-based operations, Shared Drives, shared search, exports and account-to-account transfers. Verify duplicate names, shortcuts, limited permissions and large folders against test accounts.
4. Transfer recovery and sync: durable queue, backend-supported resume, failure details, preview-first saved sync profiles, schedules and wake/tray integration. Test network loss, restart, expired authentication, full cache and interrupted sync.
5. Compatibility and release: Windows app and WinFsp mount tests; separate macOS Intel/Apple Silicon app checks. Treat macOS mounting as a separate integration, not an existing promise. Require tested downloadable installers and updater checks before declaring a release available.

Keep PyQt6 and rclone initially. Extract the large MainWindow responsibilities into navigation, transfer, mount and settings services, then move file lists to Qt models. A framework rewrite is not necessary to deliver this UX.

Measure large-file upload/download and many-small-file workloads against Air Explorer using the same account, folder, local disk and time window. Measure actual remote completion, not Explorer cache-copy completion. No throughput improvement has been established by this audit.

## Reference sources

- Air Explorer features and workflow benchmark: https://www.airexplorer.net/en/ and https://www.airexplorer.net/en/help/
- Rclone remote-control schema, full stats, VFS queue and cache counters: https://rclone.org/rc/
- Rclone mount and VFS writeback behavior: https://rclone.org/commands/rclone_mount/

Air Explorer is a workflow benchmark; these references do not certify DriveDesk parity. A live visual pass and representative transfer testing remain required before implementation can be called complete.
