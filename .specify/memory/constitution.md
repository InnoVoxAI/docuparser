<!--
SYNC IMPACT REPORT
==================
Version change: (template / unversioned) → 1.0.0

Modified principles:
  - [PRINCIPLE_1_NAME] → I. Code Quality (new)
  - [PRINCIPLE_2_NAME] → II. Testing Standards (new)
  - [PRINCIPLE_3_NAME] → III. User Experience Consistency (new)
  - [PRINCIPLE_4_NAME] → IV. Performance Requirements (new)
  - [PRINCIPLE_5_NAME] → removed (user requested 4 principles)

Added sections:
  - Development Workflow (replaces [SECTION_2_NAME])
  - Technology Standards (replaces [SECTION_3_NAME])

Removed sections:
  - None (template placeholders replaced)

Templates reviewed:
  - ✅ .specify/templates/plan-template.md — Constitution Check gate is dynamic; no update needed
  - ✅ .specify/templates/spec-template.md — Success Criteria section aligns with Performance Requirements principle
  - ✅ .specify/templates/tasks-template.md — Polish phase includes performance, security, and testing tasks; aligned
  - ✅ No commands/ directory found; skipped

Deferred TODOs:
  - None; all placeholders resolved
-->

# DocuParse Constitution

## Core Principles

### I. Code Quality

All code MUST meet the following quality standards before merging:

- **Readability**: Functions MUST be single-purpose and no longer than 50 lines;
  files MUST not exceed 400 lines.
- **Type Safety**: Python code MUST use type hints throughout; TypeScript is
  preferred over plain JavaScript for frontend components.
- **No Dead Code**: Unused imports, variables, and functions MUST be removed
  before merging.
- **Linting**: All code MUST pass configured linting rules (ruff/flake8 for
  Python, ESLint for JavaScript/TypeScript) with zero violations.
- **Security**: Code MUST NOT introduce SQL injection, XSS, command injection,
  or other OWASP Top 10 vulnerabilities. Input from users and external APIs
  MUST be validated at system boundaries.
- **Complexity**: Any function with cyclomatic complexity above 10 MUST include
  an explicit inline rationale comment.

*Rationale*: DocuParse processes sensitive documents across three microservices
integrating multiple OCR engines and AI models. Consistent code quality reduces
debugging time, eases onboarding, and prevents silent failures in processing
pipelines.

### II. Testing Standards

- **Integration Tests REQUIRED** for: OCR engine integrations, inter-service API
  contracts (Backend Core ↔ Backend OCR), document processing pipelines, and
  authentication flows.
- **Unit Tests REQUIRED** for: classification logic, document parsing utilities,
  API endpoint handlers, and any function with non-trivial business logic.
- **Coverage Minimum**: All new features MUST maintain ≥ 80% line coverage;
  critical pipelines (classification, OCR dispatch) MUST reach ≥ 90%.
- **Test Isolation**: Unit tests MUST NOT make network calls or write to disk.
  External services MUST be mocked or injected.
- **Contract Testing**: Any API contract change between Backend Core and Backend
  OCR MUST include a failing contract test written before the implementation.
- **Regression Policy**: Every reported bug MUST have a failing regression test
  added before the fix is applied.

*Rationale*: With multiple async OCR engines and AI integrations, silent
regressions are a high risk. Tests serve as the primary safety net against
breaking changes in processing pipelines.

### III. User Experience Consistency

- **API Response Envelope**: All endpoints MUST return JSON following the
  envelope: `{ "data": ..., "error": null | {...}, "meta": {...} }`.
- **Error Messages**: All user-facing error messages MUST be human-readable,
  actionable, and free of internal stack traces or raw exception text.
- **Async Feedback**: All async operations in the frontend MUST have explicit
  loading, success, and error states visible to the user.
- **Accessibility**: New frontend components MUST meet WCAG 2.1 Level AA
  compliance.
- **Responsive Design**: The React frontend MUST be usable on screens from
  320px to 1920px wide.
- **Consistent Terminology**: The terms "document", "extraction",
  "classification", and "engine" MUST be used consistently across UI labels,
  API field names, and documentation — no synonyms within the same context.

*Rationale*: DocuParse surfaces complex OCR and AI operations to end users.
Inconsistent feedback erodes trust in extraction results; unified language
across services prevents confusion when triaging processing issues.

### IV. Performance Requirements

- **API Response Times**: Backend Core non-processing endpoints MUST respond
  within 200 ms (p95). Backend OCR processing requests MUST respond within
  30 seconds (p95) for standard documents.
- **Throughput**: The OCR service MUST handle ≥ 10 concurrent document
  processing requests without measurable throughput degradation.
- **Resource Limits**: Individual containers MUST NOT exceed 2 GB RAM under
  normal load. Alerts MUST be configured at 80% usage.
- **Startup Time**: All services MUST be ready to accept requests within
  60 seconds of container startup.
- **AI Integration Timeout**: All requests to the DeepSeek/Ollama integration
  MUST have a configured timeout of 120 seconds with an explicit fallback
  behavior (e.g., return partial result or surface a user-visible error).

*Rationale*: Document processing is inherently resource-intensive. Without
defined performance budgets, individual service degradation cascades across
the microservices architecture and results in data loss or poor user outcomes.

## Development Workflow

All feature work MUST follow this process:

1. **Specification First**: Features MUST have a `spec.md` reviewed before
   implementation begins.
2. **Branch Naming**: Feature branches MUST follow `feat/###-short-description`;
   hotfixes use `fix/###-short-description`.
3. **Pull Request Requirements**: Every PR MUST include a description of the
   change, a test plan, and a reference to the relevant spec or task ID.
4. **Code Review**: All PRs MUST have at least one reviewer approval before
   merging to `main`. Self-merges on `main` are prohibited.
5. **CI Gate**: Merging to `main` MUST require passing lint, all unit tests,
   and all integration tests.
6. **Commit Messages**: MUST follow Conventional Commits format (`feat:`,
   `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).

## Technology Standards

The following stack is locked for this project. Deviations MUST be proposed
as constitution amendments before implementation:

- **Backend Core**: Django (latest stable), PostgreSQL
- **Backend OCR**: FastAPI (latest stable), Python 3.11+
- **Frontend**: React + Vite; TypeScript preferred over plain JavaScript
- **OCR Engines**: Tesseract, EasyOCR, Docling, LlamaParse — no new engines
  without an amendment
- **AI Integration**: DeepSeek via Ollama only; no direct cloud AI API keys
  in production without a security review
- **Infrastructure**: Docker + Docker Compose; all services MUST be
  containerized

## Governance

This constitution supersedes all other development practices and guidelines
for the DocuParse project.

- **Amendment Procedure**: Any principle change MUST be proposed via a PR to
  `.specify/memory/constitution.md`, reviewed by at least one team member,
  and merged with a version bump following the policy below.
- **Versioning Policy**:
  - **MAJOR**: Removal or backward-incompatible redefinition of any principle.
  - **MINOR**: Addition of new principles or materially expanded guidance.
  - **PATCH**: Clarifications, wording corrections, non-semantic refinements.
- **Compliance Review**: All PRs MUST verify compliance with Core Principles.
  The Constitution Check section in `plan.md` serves as the formal gate.
- **Conflict Resolution**: In case of conflict between this constitution and
  any other document, this constitution takes precedence.
- **Runtime Guidance**: Refer to `CLAUDE.md` for agent-specific development
  guidance.

**Version**: 1.0.0 | **Ratified**: 2026-06-02 | **Last Amended**: 2026-06-02
