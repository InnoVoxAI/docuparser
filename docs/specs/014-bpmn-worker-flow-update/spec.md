# Feature Specification: DocuParse Pipeline — Updated BPMN Flow & Worker Reconciliation

**Feature Branch**: `014-bpmn-worker-flow-update`

**Created**: 2026-07-19

**Status**: Draft

**Input**: User description: "Update the DocuParse Camunda workers to match the updated BPMN flow at docuparse-project/bpmn/flow_updated.bpmn. The BPMN process (docuparse-pipeline) now defines service/user tasks with Zeebe job types and I/O mappings (e.g. docuparse-register-document, docuparse-process-ocr, docuparse-classify-layout, docuparse-extract-fields), gateways for validity/readability/confidence checks, retry/reprocess loops, human validation via a user task, and error-reporting service tasks. The existing worker implementations live in docuparse-project/camunda-workers/src/workers and need to be reconciled with this new flow: new/renamed job types, new I/O variables, new gateways and branches (e.g. document validity check, image reprocess-after-3x logic, layout/document-type configuration check, confidence threshold branch, human validation approve/reject with reprocess-or-delete outcome)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reject unprocessable files early (Priority: P1)

An analyst sends a document by email or WhatsApp. Before any OCR or AI processing is
attempted, the system checks whether the file is even valid for processing (recognized
format, not corrupted, not password-protected). If it isn't, the analyst is told why and
the failure is logged for operations visibility, without wasting downstream processing.

**Why this priority**: This is the entry point of the pipeline. Every document flows
through this gate first, and getting it wrong either blocks valid documents or lets broken
files consume expensive OCR/LLM resources.

**Independent Test**: Submit a corrupted or password-protected file through email intake
and verify the submitter receives a rejection reason, the failure appears in the
observability platform, and no OCR job is created.

**Acceptance Scenarios**:

1. **Given** a valid, readable PDF is submitted, **When** the ingestion/validity check runs,
   **Then** the document proceeds to OCR.
2. **Given** a corrupted or unsupported file is submitted, **When** the validity check runs,
   **Then** the submitter is notified with the rejection reason, the failure is recorded in
   the observability platform, and processing ends for that submission.

---

### User Story 2 - Automatically recover from poor-quality scans (Priority: P1)

A document is valid but the OCR pass produces unreliable text (e.g., a skewed or low-contrast
scan). Instead of immediately failing, the system automatically pre-processes/cleans the image
and retries OCR, up to 3 attempts, before giving up and asking the submitter for a new file.

**Why this priority**: Transient scan-quality issues are common and auto-recoverable; without
this, otherwise-good documents would be rejected unnecessarily, creating avoidable manual work.

**Independent Test**: Submit a low-quality scan that becomes readable only after image
clean-up; verify the system retries pre-processing and OCR automatically (without any human
involvement) and the document proceeds once readable.

**Acceptance Scenarios**:

1. **Given** OCR output is not legible, **When** the document has been retried fewer than 3
   times, **Then** the system pre-processes the image and re-attempts OCR automatically.
2. **Given** OCR output is still not legible after 3 pre-processing retries, **When** the
   retry limit is reached, **Then** the submitter is notified a new document is needed, the
   failure is recorded in the observability platform, and processing ends for that submission.
3. **Given** OCR output becomes legible on a retry attempt, **When** that attempt succeeds,
   **Then** the document proceeds to document-type classification.

---

### User Story 3 - Classify document type and resolve an extraction template (Priority: P1)

Once OCR text is available, the system classifies the document's type/layout (boleto, NF,
recibo, contrato, conta de água, conta de energia, etc.) and checks whether an extraction
template is already configured for that type. If one exists, extraction proceeds
automatically; if not, an operator creates or selects the appropriate extraction template
(via a manual template-resolution task) before the document moves to field extraction.

**Why this priority**: Extraction cannot run reliably without knowing which fields/schema
apply to a document, so this gate directly determines whether automated extraction is even
possible for a given document type.

**Independent Test**: Submit a document type with a pre-existing template and verify it
proceeds straight to extraction; submit a document type with no template and verify the
document is routed to an operator to create/select a template before extraction begins.

**Acceptance Scenarios**:

1. **Given** a document's classified type already has a configured template, **When**
   classification completes, **Then** the document proceeds directly to field extraction.
2. **Given** a document's classified type has no configured template, **When**
   classification completes, **Then** the document is routed to an operator task where the
   operator creates a new template or selects an existing one, and only then does the
   document proceed to field extraction.

---

### User Story 4 - Auto-approve high-confidence extractions, route the rest to review (Priority: P1)

After AI extraction runs, the system checks the confidence score. Documents extracted with
greater than 95% confidence are marked processed and sent onward automatically. Documents at
or below that threshold are routed to an operator queue for manual validation.

**Why this priority**: This is the core cost/quality trade-off of the pipeline — it
determines how much of the volume can flow through untouched versus how much requires paid
operator time, directly affecting both throughput and accuracy.

**Independent Test**: Run extraction on a document with known high-confidence output and
verify it is marked processed and delivered without operator involvement; run extraction on
a low-confidence document and verify it lands in the operator validation queue.

**Acceptance Scenarios**:

1. **Given** extraction confidence is greater than 95%, **When** the confidence check runs,
   **Then** the document is marked processed and the submitter is informed it was sent
   successfully, with no operator action required.
2. **Given** extraction confidence is 95% or below, **When** the confidence check runs,
   **Then** the document is routed to the operator validation queue.

---

### User Story 5 - Operator resolves low-confidence extractions (Priority: P2)

An operator opens a document routed for manual validation, reviews the AI-extracted fields,
and either approves them (with or without corrections) or rejects them. If rejected, the
operator must choose whether the document should be reprocessed (sent back through
extraction) or permanently deleted.

**Why this priority**: This closes the loop for the ~5%-or-below-confidence documents that
User Story 4 routes for review; without it, those documents would have no path to
completion.

**Independent Test**: As an operator, open a document in the validation queue, correct a
field, and approve it — verify the document is marked processed and the submitter is
notified. Separately, reject a document and verify the operator is prompted to choose
reprocess or delete, and that each choice produces the expected outcome.

**Acceptance Scenarios**:

1. **Given** an operator approves a document (with or without corrections), **When** the
   approval is submitted, **Then** the document is marked processed and the submitter is
   notified it was sent successfully.
2. **Given** an operator rejects a document, **When** the rejection is submitted, **Then**
   the document status is set to rejected and the operator is prompted to choose between
   reprocessing and deleting it.
3. **Given** an operator chooses to reprocess a rejected document, **When** that choice is
   submitted, **Then** the document returns to the field-extraction step.
4. **Given** an operator chooses to delete a rejected document, **When** that choice is
   submitted, **Then** the document is marked deleted/archived (its record and stored file
   are retained, not physically erased) and processing ends for that document.

---

### User Story 6 - Operations visibility into terminal failures (Priority: P2)

Whenever a document's processing ends in failure (invalid file, or unreadable after 3
retries), the failure is recorded in the observability platform so operations staff can
monitor and troubleshoot pipeline health without needing to contact the submitter.

**Why this priority**: Without centralized failure visibility, silent or hard-to-trace
failures accumulate and operational issues (e.g., a spike in corrupted uploads) go
unnoticed until a customer complains.

**Independent Test**: Trigger each terminal failure path (invalid file, unreadable after 3
retries) and verify a corresponding entry appears in the observability platform with enough
detail to identify the document and failure reason.

**Acceptance Scenarios**:

1. **Given** a document fails the initial validity check, **When** the submitter is
   notified, **Then** a failure record is also written to the observability platform.
2. **Given** a document is still unreadable after 3 pre-processing retries, **When** the
   submitter is notified, **Then** a failure record is also written to the observability
   platform.

---

### Edge Cases

- What happens if a document already exists (duplicate submission by content hash) — is it
  still subject to the new validity/readability gates, or short-circuited earlier?
- Is there a cap on how many times a document can be sent back through the reprocess loop
  after repeated operator rejections, or can it cycle indefinitely?
- What happens if an operator is unavailable/no candidate exists in the `operators` group —
  does the document wait indefinitely in the validation queue?
- How does the system behave if the observability platform itself is unreachable when a
  terminal failure needs to be logged?
- What happens to a document that is mid-flow (e.g., queued for OCR) when its extraction
  template is reconfigured or removed?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST validate every ingested document for basic processability
  (recognized format, not corrupted, not password-protected) before OCR is attempted.
- **FR-002**: System MUST reject documents that fail the validity check, notify the
  submitter with a specific rejection reason, and record the failure in the observability
  platform without proceeding to OCR.
- **FR-003**: System MUST assess whether OCR output is legible/readable.
- **FR-004**: When OCR output is not legible and fewer than 3 pre-processing retries have
  occurred, system MUST automatically pre-process the image and re-attempt OCR.
- **FR-005**: When OCR output remains illegible after 3 pre-processing retries, system MUST
  notify the submitter that a new document is required and record the failure in the
  observability platform, without further automatic retries.
- **FR-006**: System MUST classify the document's type/layout once OCR output is legible.
- **FR-007**: System MUST determine whether an extraction template/schema is already
  configured for the classified document type.
- **FR-008**: When no extraction template is configured for the classified type, system
  MUST route the document to an operator task where the operator creates a new template or
  selects an existing one before field extraction runs.
- **FR-009**: System MUST extract structured fields from the document via AI once a
  template is resolved.
- **FR-010**: System MUST evaluate the extraction confidence score after field extraction.
- **FR-011**: When extraction confidence is greater than 95%, system MUST mark the document
  processed and notify the submitter it was sent successfully, without operator
  intervention.
- **FR-012**: When extraction confidence is 95% or below, system MUST route the document to
  the operator validation queue (candidate group `operators`).
- **FR-013**: System MUST allow an operator to review extracted fields, apply corrections,
  and record an approve or reject decision for documents in the validation queue.
- **FR-014**: When an operator approves a document, system MUST mark it processed and
  notify the submitter it was sent successfully.
- **FR-015**: When an operator rejects a document, system MUST set the document status to
  rejected and require the operator to choose between reprocessing and deleting it.
- **FR-016**: When reprocessing is chosen after rejection, system MUST return the document
  to the field-extraction step.
- **FR-017**: When deletion is chosen after rejection, system MUST mark the document
  deleted/archived (retaining its record and stored file rather than physically erasing
  them) and end processing for that document.
- **FR-018**: System MUST record a failure entry in the observability platform for every
  terminal failure path (invalid file, unreadable after 3 retries), including enough detail
  to identify the document and the failure reason.
- **FR-019**: System MUST continue to accept documents via the existing email and WhatsApp
  intake channels as entry points into this flow.
- **FR-020**: System's automated pipeline MUST NOT perform ERP export as part of this flow;
  the ERP integration step present in the previous flow is intentionally removed from this
  pipeline, and its corresponding worker is decommissioned/unused going forward.

### Key Entities

- **Document**: A submitted file moving through the pipeline; tracks status (received,
  processing, rejected, processed, deleted), validity outcome, OCR readability/retry count,
  classified type, resolved extraction template, extraction confidence, and links to the
  submitter/channel it arrived from.
- **Extraction Template**: Defines the fields/schema for a given document type; has a
  configuration state (configured/unconfigured) that determines whether extraction can run
  automatically or requires the template-resolution path first.
- **Validation Decision**: The operator's outcome for a document routed to manual review —
  records approve/reject, any field corrections, and (on rejection) the chosen reprocess-or-
  delete outcome.
- **Failure Record**: An entry written to the observability platform for a terminal
  processing failure, capturing the document identifier, the failure reason, and the step at
  which it occurred.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of documents that fail the validity check are rejected with a specific,
  understandable reason delivered to the submitter — none are silently dropped.
- **SC-002**: 100% of illegible documents are automatically retried through image
  pre-processing up to 3 times before any manual intervention is requested, eliminating
  unnecessary manual work for transient scan-quality issues.
- **SC-003**: Documents extracted with greater than 95% confidence reach a processed state
  and are delivered to the submitter with zero operator involvement.
- **SC-004**: Every document routed to manual validation reaches a final resolved state
  (processed, or rejected-and-reprocessed, or rejected-and-deleted) — none remain
  indefinitely pending in the validation queue.
- **SC-005**: 100% of terminal processing failures (invalid file, unreadable after retries)
  are visible in the observability platform, allowing operations staff to detect and
  diagnose pipeline issues without contacting the submitter.

## Assumptions

- The document intake channels (email, WhatsApp) and the document-registration/duplicate-
  detection behavior of the existing ingestion step remain unchanged by this update.
- "Confiança > 95%" refers to the same extraction-confidence score already produced by the
  existing field-extraction step.
- The `operators` candidate group used for manual validation today remains the group
  responsible for the new validation and delete/reprocess decisions.
- Failure records are written to the observability tool already in use in production (e.g.
  Grafana), consistent with the flow diagram's annotations.
- The reprocess loop for rejected documents has no additional attempt cap beyond normal
  service-level retry policies; the flow diagram does not define one.
- ERP export (`docuparse-export-erp`) is out of scope for this pipeline going forward; the
  existing `erp.py` worker is left decommissioned/unused rather than removed outright.
- "Delete" for a rejected document means marking it deleted/archived; the document record
  and stored file are retained rather than physically erased.
