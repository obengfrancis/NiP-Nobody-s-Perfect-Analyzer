# NiP v2 — Validation and Execution Protocol

**Status:** FROZEN  
**Protocol version:** `nip-v2-validation/1.1`  
**Freeze date:** 2026-09-18  
**Governing specification:** `nip-v2-spec/1.0`  
**Primary study target:** MSR-style repository mining / software analytics study

This protocol operationalizes validation, coverage-pilot, and resolver-robustness procedures for NiP v2. It does **not** modify the frozen measurement semantics in `nip-v2-spec/1.0`. If a pilot result requires changing a semantic rule in that specification (for example, the 80% primary parser-coverage threshold or an association-scope definition), the specification must be versioned before the definitive corpus analysis proceeds.

---

## 1. Purpose

The protocol addresses three threats that must be resolved before corpus-scale inference:

1. mechanism-level validation cells may be too sparse when only the minimum 40 adjudicated invocations per language are available;
2. the `>=0.80` file-coverage and `>=0.80` LOC-coverage primary inclusion rule may induce differential attrition, especially for multilingual repositories;
3. `local_dataflow` and `resolved_cross_scope` association may differ in implementation strength across languages and could reintroduce cross-language incomparability.

The definitive study therefore separates:

- a **representative human-adjudicated validation set**;
- a **rare-mechanism enrichment set** used only for detector validation;
- a **coverage pilot** conducted before final corpus inference; and
- a **resolver-sensitivity analysis** comparing full and restricted association scopes.

---

## 2. Representative validation set

### 2.1 Target and minimum

The preferred target is **60 adjudicated high-confidence outbound service invocations per language** across the nine supported languages:

`60 invocations x 9 languages = 540 adjudicated invocations`

The frozen specification's requirement of **40 adjudicated invocations per language (360 total)** remains the absolute minimum floor. Falling below 60 in a language must be documented; falling below 40 means that language does not satisfy the validation protocol for cross-language claims.

### 2.2 Repository diversity

For each language, the 60-invocation target should be drawn from approximately **30-40 distinct repositories**, where feasible. No repository should contribute more than **3 representative-set invocations** for a language unless required to reach the minimum after documented sampling exhaustion.

The sample should span multiple recognized HTTP-client families rather than concentrating on a single library.

### 2.3 File sampling and human enumeration

Validation must permit false negatives to be discovered. Therefore, annotators must not receive only invocations already detected by NiP.

For each language:

1. sample production source files from the frozen candidate corpus using a fixed random seed and recorded sampling frame;
2. include files with HTTP-client evidence as well as a diagnostic sample of files without NiP invocation detections;
3. human annotators independently inspect the sampled files and **enumerate all outbound service invocations** in scope;
4. NiP outputs remain hidden from annotators during independent annotation;
5. after human enumeration, match NiP detections to adjudicated human invocations by source span/callee rules.

Detector-positive, HTTP-import-only, and detector-negative strata may be used to ensure challenge coverage, but stratum membership and sampling fractions must be recorded. Any deliberately challenge-enriched cases are analyzed separately from representative-set estimates unless appropriate weighting is applied.

### 2.4 Annotation fields

For every human-identified invocation, annotators record at least:

- outbound invocation: `yes/no`;
- language;
- file/source span;
- normalized client/callee where resolvable;
- invocation confidence;
- each frozen core mechanism state: `present/absent/unknown`;
- association scope for each positive mechanism;
- evidence span / concise evidence rationale;
- uncertainty note when `unknown` is used.

The core mechanisms are those frozen in `nip-v2-spec/1.0`:

- `exception_error_handling`;
- `status_error_check`;
- `timeout`;
- `retry`;
- `bounded_retry`;
- `backoff`;
- `exponential_backoff`;
- `circuit_breaker`.

---

## 3. Annotators, independence, and adjudication

### 3.1 Core ground truth

The primary detector ground truth is produced by **two independent human annotators**, followed by adjudication of all disagreements.

The independent annotation phase must be blind to:

- NiP predictions;
- the other human annotator's labels.

### 3.2 Agreement

Report human-human agreement on matched invocation/mechanism labels before adjudication. At minimum report:

- exact agreement for tri-state mechanism labels;
- Cohen's kappa where estimable;
- support counts for each mechanism/state;
- agreement on invocation enumeration/matching using an explicitly documented matching rule.

Agreement is a reproducibility measure; it does not replace NiP-vs-ground-truth precision/recall analysis.

---

## 4. Invocation-detection validation

Per language, compare NiP's high-confidence production invocation detections directly with adjudicated human invocation enumeration.

Report:

- true positives (TP);
- false positives (FP);
- false negatives (FN);
- precision;
- recall;
- F1;
- 95% confidence intervals for precision and recall where feasible;
- number of sampled files and repositories.

Also report a nine-language macro-average. Do not infer recall from a sample containing only NiP-positive invocations.

---

## 5. Mechanism-state validation and minimum support rule

### 5.1 Always report support

For every mechanism-language combination, report the available support counts even when a stable per-language metric cannot be estimated:

- adjudicated `present` count;
- adjudicated `absent` count;
- adjudicated `unknown` count;
- NiP TP/FP/FN/TN for evaluable binary present-vs-absent cases.

`unknown` is reported separately and is not collapsed into `absent`.

### 5.2 Per-language metric reporting rule

A per-language mechanism precision/recall/F1 value is treated as **reportable for interpretation** only when the representative validation set contains at least:

- **10 adjudicated `present` cases**, and
- **10 adjudicated `absent` cases**

for that mechanism in that language.

If this support rule is not met, the table reports the support counts and marks the metric as **insufficient support** rather than presenting an unstable percentage as if it were comparable.

Metrics may still be computed internally for diagnostics, but they are not used to support cross-language claims.

### 5.3 Confidence intervals

For reportable mechanism metrics, accompany precision and recall with 95% binomial confidence intervals where possible. Small-support estimates must be interpreted through their support and intervals rather than point estimates alone.

---

## 6. Rare-mechanism enrichment

### 6.1 Purpose

Rare mechanisms are intentionally enriched only to test detector behavior. Enriched cases must never be mixed into corpus-prevalence estimates.

The rare-mechanism set includes, at minimum:

- `retry`;
- `bounded_retry`;
- `backoff`;
- `exponential_backoff`;
- `circuit_breaker`.

### 6.2 Pooled target

For each rare mechanism, target at least **50 adjudicated positive cases pooled across languages**, plus a comparably sized set of relevant negatives/challenging near-misses where feasible.

Positive cases should span at least **5 languages** when ecosystem support permits. The exact language distribution and client libraries must be reported.

If 50 positives cannot be obtained without disproportionate duplication or synthetic examples, stop at the available support and report that limitation rather than manufacturing balance.

### 6.3 Reporting

Rare-mechanism validation is reported primarily as pooled precision/recall/F1 with support counts and language composition. Per-language rare-mechanism metrics are reported only when the minimum support rule in Section 5.2 is met.

Synthetic/golden fixtures are for conformance testing, not empirical detector-performance estimates, and are not counted as human-validation positives.

---

## 7. Coverage pilot before definitive corpus inference

### 7.1 Objective

The frozen specification requires both:

- file coverage `>= 0.80`, and
- LOC coverage `>= 0.80`

for inclusion in the primary repository analysis set.

Before running definitive inferential analyses, the study must empirically characterize how this rule affects corpus retention and whether attrition is differential by language or repository composition.

### 7.2 Pilot sample

After repository collection is complete, draw a fixed-seed **coverage-pilot sample of 600 candidate repositories**, where feasible.

The sample should preserve a random representative component and ensure enough multilingual repositories for comparison. The final sampling frame, seed, and any stratification/oversampling must be recorded.

If the full candidate corpus contains too few repositories for this target, use the available corpus and document the reduction.

### 7.3 Required coverage outputs

For each pilot repository record:

- eligible production supported-source files;
- parsed `ok` files;
- `partial` files;
- `failed` files;
- `unsupported` files;
- eligible production LOC;
- parsed `ok` LOC;
- file coverage;
- LOC coverage;
- coverage by language;
- single-language vs multilingual status;
- repository size/LOC;
- parser/backend failure reason counts.

Report the empirical distributions and corpus-retention rates under paired file+LOC thresholds of:

- 0.50;
- 0.60;
- 0.70;
- 0.80;
- 0.90;
- 0.95.

### 7.4 Differential-attrition diagnostics

At minimum compare retention at the frozen 0.80 threshold by:

- single-language vs multilingual repositories;
- each language with adequate pilot support;
- repository size/LOC quartile;
- parser backend/failure cause.

Also report the language composition of repositories excluded solely for insufficient coverage.

### 7.5 Decision rule

The coverage pilot does **not** automatically alter the 0.80 threshold.

The pilot triggers a documented specification review before definitive corpus inference if any of the following occurs:

- fewer than **70%** of the pilot repositories satisfy the 0.80/0.80 primary rule;
- multilingual retention is more than **10 percentage points lower** than single-language retention;
- a language with at least 30 pilot repositories has retention more than **15 percentage points below** the overall pilot retention because of parser/unsupported coverage;
- a specific backend failure systematically removes a recognizable repository subgroup.

If review determines that the primary threshold or source-eligibility semantics must change, issue a new NiP specification version **before** definitive analysis. The original v1.0 pilot results remain archived.

If the threshold remains unchanged despite differential attrition, the paper must explicitly characterize the resulting analysis population and qualify generalization accordingly.

---

## 8. Cross-language resolver conformance

### 8.1 Existing mandatory fixtures

All nine adapters must continue to pass the 15 fixtures in `nip-v2-spec/1.0` Section 14.

### 8.2 Additional mandatory dataflow/cross-scope fixtures

Add semantically equivalent fixtures in **all nine languages** for:

16. local variable -> configured client -> outbound invocation;
17. invocation response -> local alias -> status/error check;
18. retry policy -> local variable -> policy wrapper -> outbound invocation;
19. client configuration stored in class/object field -> invocation in method;
20. module/class-level client configuration -> invocation in another function/method;
21. ambiguous alias/dataflow where association cannot be resolved -> mechanism must be `unknown`, not `present`;
22. unresolved cross-scope configuration that could materially govern the invocation -> mechanism must be `unknown`, not `absent`.

These seven fixture families create at least **63 additional semantic checks** (7 scenarios x 9 languages), beyond language-specific subcases.

### 8.3 Conformance requirement

All adapters must produce the same normalized semantic outcome for equivalent fixtures. A language adapter that cannot satisfy a fixture because the backend lacks required resolution must return `unknown` where specified rather than guessing `present` or `absent`.

A failing adapter cannot be used for the affected cross-language mechanism claim until fixed or explicitly excluded/qualified under the frozen specification.

---

## 9. Resolver-sensitivity analysis

### 9.1 Full-resolver analysis

The primary NiP v2 analysis uses all eight approved association scopes from the frozen specification:

- `call_argument`;
- `fluent_chain`;
- `lexical_handler`;
- `response_link`;
- `configured_client`;
- `policy_wrapper`;
- `local_dataflow`;
- `resolved_cross_scope`.

### 9.2 Restricted-scope sensitivity analysis

Repeat the major mechanism-coverage and cross-language analyses using only:

- `call_argument`;
- `fluent_chain`;
- `lexical_handler`;
- `response_link`;
- `configured_client`;
- `policy_wrapper`.

Exclude positive evidence that depends solely on:

- `local_dataflow`;
- `resolved_cross_scope`.

Invocations affected by removal of those scopes must be recomputed under the frozen tri-state rules rather than blindly relabeled absent.

### 9.3 Required comparison

For every major reported outcome, report at least:

- full-resolver estimate;
- restricted-scope estimate;
- absolute difference;
- affected invocation count/proportion;
- language-specific differences where relevant.

Differences greater than **5 percentage points** in a headline mechanism-coverage estimate, or a reversal of the direction of a reported cross-language association, are flagged as resolver-sensitive and must be discussed explicitly rather than presented as robust.

This sensitivity rule diagnoses dependence on resolver strength; it does not automatically invalidate the full-resolver result.

---

## 10. Sequence of execution

The study proceeds in the following order:

1. freeze repository collection and candidate-corpus provenance;
2. implement NiP v2 against `nip-v2-spec/1.0`;
3. pass the original 15 cross-language conformance fixtures;
4. pass the 7 added dataflow/cross-scope fixture families;
5. run the coverage pilot and archive its outputs;
6. resolve any specification-changing coverage issue **before** definitive corpus analysis;
7. construct the representative human-validation sample;
8. complete independent human annotation and adjudication;
9. run rare-mechanism enrichment validation separately;
10. freeze the validated NiP implementation/version;
11. run NiP on the definitive frozen corpus;
12. compute primary invocation-level and repository-derived outcomes;
13. run parser-coverage threshold sensitivities required by the specification;
14. run the restricted-scope resolver sensitivity analysis;
15. produce final statistical analyses and replication artifacts.

No definitive hypothesis/inferential result should be used to tune detector semantics or sampling rules after Step 10 without a documented new analysis/specification version.

---

## 11. Required replication-package artifacts

At minimum, include:

```text
validation/
  NiP_v2_Validation_Execution_Protocol_v1.1_FROZEN.md
  sampling_manifest.json
  representative_sample_manifest.csv
  annotation_manual.md
  human_A.csv
  human_B.csv
  adjudication_decisions.csv
  ground_truth.csv
  invocation_detection_metrics.csv
  mechanism_metrics.csv
  mechanism_support.csv
  rare_pattern_validation.csv
  agreement_metrics.csv
  confusion_matrices/

coverage_pilot/
  sample_manifest.csv
  coverage_by_repository.csv
  coverage_by_language.csv
  threshold_retention.csv
  attrition_diagnostics.csv
  backend_failure_summary.csv

conformance/
  golden/
  expected_outputs/
  conformance_results.json

sensitivity/
  resolver_scope_comparison.csv
  coverage_threshold_comparison.csv
```

All generated tables must retain the analyzer version, specification version, protocol version, and corpus/input hash in provenance or accompanying manifests.

---

## 12. Freeze and amendment rules

This protocol is frozen at `nip-v2-validation/1.1`.

A protocol version bump is required for changes to:

- representative validation target/minimum;
- adjudication design;
- minimum-support reporting rule;
- rare-mechanism enrichment target/role;
- coverage-pilot decision triggers;
- added conformance fixture semantics;
- restricted-scope sensitivity definition;
- the order of pilot/validation/final-analysis steps in a way that could introduce post-hoc tuning.

Editorial corrections, path/name changes, and additional diagnostic outputs that do not alter the above decisions do not require a version bump.

If a protocol change also changes a frozen NiP measurement semantic, both the protocol and `nip-v2-spec` must be versioned.
