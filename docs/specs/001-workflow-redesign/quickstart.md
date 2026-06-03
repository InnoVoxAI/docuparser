# Quickstart: Manual Validation of Workflow Redesign

**Branch**: `001-workflow-redesign` | **Date**: 2026-06-02

---

## Prerequisites

1. Docker and Docker Compose installed and running.
2. Ollama running locally (optional — only needed for DeepSeek extraction).
3. Run from the repository root:
   ```bash
   bash run-pipe.sh
   ```
4. Open `http://localhost:5173` in a browser.

---

## Test Plan

### US1: Inbox filtered + Upload button + navigation to Validation

1. Ensure some documents exist with non-pending statuses (APPROVED, REJECTED).
2. Open **Inbox** in the sidebar.
3. **Verify**: Only documents with status `RECEIVED`, `OCR_COMPLETED`,
   `EXTRACTION_COMPLETED`, or `VALIDATION_PENDING` appear in the list.
   Approved/rejected documents MUST NOT be listed.
4. **Verify**: An "Enviar Documento" button appears ABOVE the document list.
5. Click **Enviar Documento** → must navigate to the Upload screen.
6. Go back to **Inbox**.
7. Click any document in the list.
8. **Verify**: The app navigates to the **Validacao** screen showing only the
   clicked document (no lateral document list).

---

### US1 (RF-10): Direct access to Validation blocked

1. While on any screen other than Inbox, click **Validacao** in the sidebar
   (without having first selected a document via Inbox).
2. **Verify**: The Validacao screen shows an empty state with a message like
   "Selecione um documento no Inbox para iniciar a validação" and a button
   to go back to Inbox.
3. Click the **Ir para o Inbox** button → must navigate to Inbox.

---

### US2: Validation screen shows single document + metadata

1. From Inbox, click a document that has extraction results.
2. **Verify**: The Validacao screen shows only that document (no list on the
   left).
3. **Verify**: Extracted fields (non-empty) are displayed in the fields panel.
4. **Verify**: Fields with `null` or empty values are NOT shown.

---

### US3: Reject a document and verify Rejected list

1. From Inbox, click a pending document → navigates to Validation.
2. Fill in the **Notas de validação** field with a rejection reason (e.g.,
   "Teste de rejeição").
3. Click **Rejeitar**.
4. **Verify**: The document disappears from the Inbox (status is no longer
   pending).
5. Navigate to **Rejeitados** in the sidebar.
6. **Verify**: The rejected document appears in the list with the rejection
   reason "Teste de rejeição" visible.

---

### US3: Reprocess a rejected document

1. In the **Rejeitados** screen, find the document rejected in the previous step.
2. Click **Reprocessar**.
3. **Verify**: The document disappears from the Rejected list.
4. Navigate to **Inbox**.
5. **Verify**: The document reappears in the Inbox (status = RECEIVED or
   VALIDATION_PENDING).

---

### US3: Delete a rejected document

1. In the **Rejeitados** screen, find a rejected document.
2. Click **Excluir** and confirm the dialog.
3. **Verify**: The document is removed from the Rejected list.
4. **Verify**: Refreshing the page confirms the document no longer exists.
