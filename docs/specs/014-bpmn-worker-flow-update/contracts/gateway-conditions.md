# Contract: Gateway FEEL Conditions

**Feature**: `014-bpmn-worker-flow-update`

Per Decision 8 in `research.md`, none of these exclusive gateways currently carry executable
`<bpmn:conditionExpression>` elements in `flow_updated.bpmn` — only visual "Sim"/"Não"
labels. This is the required companion change to `docuparse-pipeline`'s BPMN so the process
actually routes using the variables the reconciled workers now produce (see
`job-types.md`). Each gateway must also get exactly one default flow.

| Gateway | Sequence Flow | FEEL Condition | Default? |
|---|---|---|---|
| `Gateway_1hajqec` | `Flow_171awgt` ("Sim") | `=fileValid = true` | |
| `Gateway_1hajqec` | `Flow_1r61p02` ("Não") | *(default)* | ✅ |
| `Gateway_0lylr3v` | `Flow_0jd71mf` ("Sim") | `=ocrReadable = true` | |
| `Gateway_0lylr3v` | `Flow_1ue6to2` ("Não") | *(default)* | ✅ |
| `Gateway_19gkipo` | `Flow_1qjry7k` ("Não") | `=ocrRetryCount < 3` | ✅ |
| `Gateway_19gkipo` | `Flow_0l3firy` ("Sim") | `=ocrRetryCount >= 3` | |
| `Gateway_01v609m` | `Flow_0qi77rt` ("Sim") | `=documentConfigured = true` | |
| `Gateway_01v609m` | `Flow_1597b5e` ("Não") | *(default)* | ✅ |
| `Gateway_0kaeakc` | `Flow_1tw1rhb` ("Sim") | `=extractionConfidence > 0.95` | |
| `Gateway_0kaeakc` | `Flow_1g56dbe` ("Não") | *(default)* | ✅ |
| `Gateway_0vi5mc1` | `Flow_1n0hpsg` ("Sim (Aprovado)") | `=approved = true` | |
| `Gateway_0vi5mc1` | `Flow_1w5ymsj` ("Não (Rejeitado)") | *(default)* | ✅ |
| `Gateway_1qmnvbm` | `Flow_1cioit5` (reprocessar) | `=reprocessChoice = "reprocess"` | |
| `Gateway_1qmnvbm` | `Flow_18bua8t` (apagar) | *(default)* | ✅ |

**Naming note**: `extractionConfidence` is read as a decimal fraction (`0.95`), matching
`ExtractionResult.confidence`'s existing representation in backend-core
(`documents/models.py`) and the worker's existing `extraction_confidence` output — **not**
a `0–100` percentage. The spec's ">95%" is `> 0.95` in this representation.

**Default-flow rationale**: A default flow on every gateway prevents the process instance
from throwing an unhandled `NO_MATCHING_CONDITION` incident if a worker fails to set the
expected variable (e.g., a bug returns `fileValid` as `null` instead of `false`). In every
case the default routes to the *more conservative* branch (reject/retry/manual-review),
never to auto-approval — a missing/malformed signal should never silently fast-track a
document.
