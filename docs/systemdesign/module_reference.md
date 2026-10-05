# Feature Documentation: CLI Behavior Scaffold

## Status

Complete

## Links & References
**Feature Requirements:** Scaffold requirements (ad-hoc)
**Task/Ticket:** None documented
**Pull Requests:** Pending current refactor
**Related Files:**

* src/finanzonline_databox/behaviors.py
* src/finanzonline_databox/cli/__init__.py
* src/finanzonline_databox/cli/_app.py
* src/finanzonline_databox/cli/_commands.py
* src/finanzonline_databox/cli/_error_handling.py
* src/finanzonline_databox/cli/_helpers.py
* src/finanzonline_databox/cli/_notifications.py
* src/finanzonline_databox/cli/typed_click.py
* src/finanzonline_databox/__main__.py
* src/finanzonline_databox/__init__.py
* src/finanzonline_databox/__init__conf__.py
* tests/test_cli.py
* tests/test_module_entry.py
* tests/test_behaviors.py

---

## Problem Statement

The original scaffold concentrated the greeting, failure trigger, and CLI
orchestration inside a single module, making it harder to explain module intent
and to guarantee that the console script and ``python -m`` execution paths stay
behaviourally identical. We needed clearer module boundaries and shared helpers
for traceback preferences without introducing the full domain/application
separation that would be overkill for this minimal template.

## Solution Overview

* Extracted the behaviour helpers into ``behaviors.py`` so both CLI and library
  consumers have a single cohesive module documenting the temporary domain.
* The ``cli`` package imports the behaviour helpers, provides explicit
  functions for applying and restoring traceback preferences, and centralises
  the exit-code handling used by both entry points.
* Reduced ``__main__.py`` to a thin wrapper delegating to the CLI helper while
  sharing the same traceback state restoration helpers.
* ``__init__.py`` exposes the package metadata, ``get_config`` and ``print_info``
  for library consumers.
* Documented the responsibilities in this module reference so future refactors
  have an authoritative baseline.

---

## Architecture Integration

**App Layer Fit:** This package remains a CLI-first utility; all modules live in
the transport/adapter layer, with ``behaviors.py`` representing the small
stand-in domain.

**Data Flow:**
1. CLI parses options with rich-click.
2. Traceback preferences are applied via ``apply_traceback_preferences``.
3. Commands delegate to behaviour helpers.
4. Exit codes and tracebacks are rendered by ``lib_cli_exit_tools``.

**System Dependencies:**
* ``rich_click`` for CLI UX
* ``lib_cli_exit_tools`` for exit-code normalisation and traceback output
* ``importlib.metadata`` via ``__init__conf__`` to present package metadata

---

## Core Components

### behaviors.emit_greeting

* **Purpose:** Write the canonical greeting used in smoke tests and
  documentation.
* **Input:** Optional text stream (defaults to ``sys.stdout``).
* **Output:** Writes ``"Hello World\n"`` to the stream and flushes if possible.
* **Location:** src/finanzonline_databox/behaviors.py

### behaviors.raise_intentional_failure

* **Purpose:** Provide a deterministic failure hook for error-handling tests.
* **Input:** None.
* **Output:** Raises ``RuntimeError('I should fail')``.
* **Location:** src/finanzonline_databox/behaviors.py

### behaviors.noop_main

* **Purpose:** Placeholder entry for transports expecting a ``main`` callable.
* **Input:** None.
* **Output:** Returns ``None``.
* **Location:** src/finanzonline_databox/behaviors.py

### cli (package layout)

* **Purpose:** ``cli/__init__.py`` re-exports the public surface
  (``CLICK_CONTEXT_SETTINGS``, ``TRACEBACK_SUMMARY_LIMIT``,
  ``TRACEBACK_VERBOSE_LIMIT``, ``CliContext``, ``cli``, ``main``,
  ``apply_traceback_preferences``, ``snapshot_traceback_state``,
  ``restore_traceback_state``) plus a few private helpers for tests, and imports
  ``_commands`` so its subcommands register on the ``cli`` group. Entry points
  reference ``finanzonline_databox.cli:main``.
* **Submodules:** ``_app`` (root group, traceback state, ``main``),
  ``_commands`` (``config``, ``config-deploy``, ``list``, ``download``,
  ``sync``), ``_error_handling`` (exception to exit-code mapping and error
  notifications), ``_helpers`` (date ranges, chunking, aggregation, filtering,
  formatting, output paths), ``_notifications`` (sync and document notification
  mails), ``typed_click`` (typed facade over the rich-click decorators).
* **Location:** src/finanzonline_databox/cli/

### cli.apply_traceback_preferences

* **Purpose:** Synchronise traceback configuration between the CLI and ``python -m`` paths.
* **Input:** Keyword-only boolean ``enabled`` flag enabling rich tracebacks.
* **Output:** Updates ``lib_cli_exit_tools.config.traceback`` and
  ``traceback_force_color``.
* **Location:** src/finanzonline_databox/cli/_app.py

### cli.snapshot_traceback_state / cli.restore_traceback_state

* **Purpose:** Capture and reapply the traceback configuration around a run.
* **Input:** ``restore_traceback_state`` takes the ``(traceback, force_color)``
  tuple returned by ``snapshot_traceback_state``.
* **Output:** The tuple, respectively ``None`` after updating
  ``lib_cli_exit_tools.config``.
* **Location:** src/finanzonline_databox/cli/_app.py

### cli.main

* **Purpose:** Execute the click command group with shared exit handling.
* **Input:** Optional argv and a keyword-only ``restore_traceback`` flag.
* **Output:** Integer exit code (0 on success, mapped error codes otherwise).
  Restores the previous traceback state and shuts down ``lib_log_rich``
  afterwards.
* **Location:** src/finanzonline_databox/cli/_app.py

### cli.cli (root group) / cli._run_cli / cli.cli_main

* **Purpose:** The root group stores the global ``--traceback`` and
  ``--profile`` options in a ``CliContext``, loads configuration, initialises
  locale and logging, and mirrors the traceback flag into
  ``lib_cli_exit_tools.config``. A bare invocation prints the command help;
  passing ``--traceback`` explicitly without a subcommand runs ``cli_main``
  (the ``noop_main`` placeholder). ``_run_cli`` delegates execution to
  ``lib_cli_exit_tools.run_cli`` and renders any escaping exception with the
  summary or verbose traceback limit.
* **Input:** Click context and global options, respectively optional argv.
* **Output:** Command side effects, respectively the integer exit code.
* **Location:** src/finanzonline_databox/cli/_app.py

### cli._commands

* **Purpose:** Register the ``config``, ``config-deploy``, ``list``,
  ``download`` and ``sync`` subcommands on the ``cli`` group; the ``info``,
  ``hello`` and ``fail`` subcommands live next to the group in ``_app.py``.
* **Location:** src/finanzonline_databox/cli/_commands.py

### cli._error_handling

* **Purpose:** Map domain and filesystem exceptions to user-facing messages and
  exit codes (``_get_error_info``, ``_get_databox_error_info``), show
  configuration help, and send error notifications
  (``_handle_databox_error``, ``_handle_command_exception``).
* **Location:** src/finanzonline_databox/cli/_error_handling.py

### cli._helpers

* **Purpose:** Date parsing and range chunking, aggregation of chunked list and
  sync results, read/unread/reference filtering, result formatting, and output
  directory and filename resolution for the commands.
* **Location:** src/finanzonline_databox/cli/_helpers.py

### cli._notifications

* **Purpose:** Resolve recipients and send sync and per-document notification
  mails when enabled in the configuration.
* **Location:** src/finanzonline_databox/cli/_notifications.py

### cli.typed_click

* **Purpose:** Typed facade over the rich-click ``option``, ``argument`` and
  ``version_option`` decorators so call sites are fully typed.
* **Location:** src/finanzonline_databox/cli/typed_click.py

### __main__ (module entry)

* **Purpose:** Provide the ``python -m finanzonline_databox`` entry point by
  running ``cli.main``, the function the console scripts run, so exit codes
  and traceback handling are identical across both transports.
* **Input:** ``sys.argv``.
* **Output:** ``SystemExit`` carrying the exit code returned by ``cli.main``.
* **Location:** src/finanzonline_databox/__main__.py

### __init__conf__.print_info

* **Purpose:** Render the statically-defined project metadata for the CLI ``info`` command.
* **Input:** None.
* **Output:** Writes the hard-coded metadata block to ``stdout``.
* **Location:** src/finanzonline_databox/__init__conf__.py

### Package Exports

* ``__init__.py`` exposes the package metadata dunders, ``get_config`` and
  ``print_info`` for library consumers. Behaviour helpers are imported from
  ``finanzonline_databox.behaviors``.

---

## Implementation Details

**Dependencies:**

* External: ``rich_click``, ``lib_cli_exit_tools``
* Internal: ``behaviors`` module, ``__init__conf__`` static metadata constants

**Key Configuration:**

* No environment variables required.
* Traceback preferences controlled via CLI ``--traceback`` flag.

**Database Changes:**

* None.

**Error Handling Strategy:**

* ``lib_cli_exit_tools`` centralises exception rendering.
* ``apply_traceback_preferences`` ensures colour output for ``--traceback``.
* ``restore_traceback_state`` restores previous preferences after each run.
* ``cli._error_handling`` maps domain errors to exit codes before
  ``lib_cli_exit_tools`` renders anything unhandled.

---

## Testing Approach

**Manual Testing Steps:**

1. ``finanzonline_databox`` -> prints CLI help (no default action).
2. ``finanzonline_databox hello`` -> prints greeting.
3. ``finanzonline_databox fail`` -> prints truncated traceback.
4. ``finanzonline_databox --traceback fail`` -> prints full rich traceback.
5. ``python -m finanzonline_databox --traceback fail`` -> matches console output.

**Automated Tests:**

* ``tests/test_cli.py`` exercises the help-first behaviour, failure path,
  metadata output, and invalid command handling for the click surface.
* ``tests/test_module_entry.py`` ensures ``python -m`` entry mirrors the console
  script, including traceback behaviour.
* ``tests/test_behaviors.py`` verifies greeting/failure helpers against custom
  streams.
* Doctests embedded in behaviour and CLI helpers provide micro-regression tests
  for argument handling.

**Edge Cases:**

* Running without subcommand prints the help; with an explicit ``--traceback``
  it delegates to ``noop_main`` (no output).
* Repeated invocations respect previous traceback preference thanks to
  restoration helpers.

**Test Data:**

* No fixtures required; tests rely on built-in `CliRunner` and monkeypatching.

---

## Known Issues & Future Improvements

**Current Limitations:**

* Behaviour module still contains placeholder logic; real logging helpers will
  replace it in future iterations.

**Future Enhancements:**

* Introduce structured logging once the logging stack lands.
* Expand the module reference when new commands or behaviours are added.

---

## Risks & Considerations

**Technical Risks:**

* Traceback behaviour depends on ``lib_cli_exit_tools``; upstream changes may
  require adjustments to the helper functions.

**User Impact:**

* None expected; CLI surface and public imports remain backward compatible.

---

## Documentation & Resources

**Internal References:**

* README.md - usage examples
* INSTALL_en.md - installation options
* DEVELOPMENT.md - developer workflow

**External References:**

* rich-click documentation
* lib_cli_exit_tools project README

---

**Created:** 2025-09-26 by Codex (automation)
**Last Updated:** 2025-09-26 by Codex
**Review Cycle:** Evaluate during next logging feature milestone

---

## Instructions for Use

1. Trigger this document whenever CLI behaviour helpers change.
2. Keep module descriptions in sync with code during future refactors.
3. Extend with new components when additional commands or behaviours ship.
