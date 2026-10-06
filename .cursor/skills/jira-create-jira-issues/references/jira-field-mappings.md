# Jira Field Mappings

Complete reference of field IDs, custom fields, and format types for the Jira project. All field IDs below use parameterized placeholders so they can be configured per-team via `promp.json` parameters.

## Standard Jira Fields


| Field       | API Key       | Format            | Notes                                                               |
| ----------- | ------------- | ----------------- | ------------------------------------------------------------------- |
| Summary     | `summary`     | String            | Plain text, required for all issue types                            |
| Description | `description` | String (markdown) | API auto-converts markdown; update in separate call from ADF fields |
| Labels      | `labels`      | Array of strings  | `["label1", "label2"]`                                              |
| Priority    | `priority`    | Object            | `{"name": "High"}`                                                  |
| Assignee    | `assignee`    | Object            | `{"accountId": "user-account-id"}`                                  |
| Reporter    | `reporter`    | Object            | `{"accountId": "user-account-id"}`                                  |


## Project Custom Fields

### Acceptance Criteria

- **Field ID:** `{{acceptanceCriteriaFieldId}}`
- **Format:** ADF JSON (see `adf-format-guide.md`)
- **Availability:** Stories and Tasks only -- **NOT available for Bug issue types**
- **Related field:** `{{acReadyFieldId}}` ("Is the Acceptance Criteria Ready?" Yes/No)

### Organizational Fields

These fields are **required for all issue types** in the project:


| Field       | Field ID                | Format        | Type   | Example                       |
| ----------- | ----------------------- | ------------- | ------ | ----------------------------- |
| Channel     | `{{channelFieldId}}`    | Multi-select  | Array  | `[{"value": "{{channel}}"}]`  |
| Work-Stream | `{{workStreamFieldId}}` | Single-select | Object | `{"value": "{{workStream}}"}` |
| Teams       | `{{teamsFieldId}}`      | Multi-select  | Array  | `[{"value": "{{team}}"}]`     |


### Story Points

- **Field ID:** `{{storyPointsFieldId}}`
- **Format:** Number -- send the **bare value** (`5`), never an option object. This is the one configured custom field that is not a select, so the `{"value": ...}` wrapper used by the organizational and Bug fields will be rejected here.
- **Availability:** Estimable types (Story, Task, Bug). Sub-tasks do not carry story points.
- **Why it matters:** Project workflows commonly validate on it -- for example, requiring both Epic Link and Story Points before an issue may leave `Backlog`. An issue created without points can be blocked from transitioning until someone sets them.
- **Note:** Some projects also expose a team-managed `Story point estimate` field. `configure-jira` prefers an exact `Story Points` match; the other is usually unused.


### Bug-Specific Fields

These fields are **required only for Bug issue types**:


| Field                | Field ID                        | Format        | Type   |
| -------------------- | ------------------------------- | ------------- | ------ |
| Environment          | `{{bugEnvironmentFieldId}}`     | Single-select | Object |
| Severity             | `{{bugSeverityFieldId}}`        | Single-select | Object |
| Test Phase           | `{{bugTestPhaseFieldId}}`       | Single-select | Object |
| Responsible Dev Team | `{{bugResponsibleTeamFieldId}}` | Single-select | Object |


### Epic-Specific Fields

The base Epic profile uses only the generic required fields (Channel, Work-Stream, Teams). Some Jira projects expose additional Epic-specific custom fields. When a consuming team requires them, they are configured at install time and merged into `additional_fields` via the `epicExtras` workflow input.


| Field             | Field ID                   | Format        | Type                    | Notes                                                                                                                                   |
| ----------------- | -------------------------- | ------------- | ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Epic Name         | `{{epicNameFieldId}}`      | Plain text    | String                  | Optional. Some Jira projects keep Epic Name as a separate field distinct from `summary`. Modern Jira treats `summary` as the Epic Name. |
| Target Start Date | `{{epicStartDateFieldId}}` | Date          | String (`"YYYY-MM-DD"`) | Optional.                                                                                                                               |
| Target End Date   | `{{epicEndDateFieldId}}`   | Date          | String (`"YYYY-MM-DD"`) | Optional.                                                                                                                               |
| Theme             | `{{epicThemeFieldId}}`     | Single-select | Object                  | Optional. Use `{"value": "<theme>"}` when the project defines themes.                                                                   |


If a consuming project does not define one or more of these placeholders, the Epic profile silently omits them. Confirm which placeholders are used by your team by calling `getJiraIssueTypeMetaWithFields` for the Epic issue type and updating the consumer's promp parameter file accordingly.

#### Epic Acceptance Criteria Field Availability

The Epic profile in `issue-type-requirements.md` defaults to `acceptanceCriteriaMode = inline-description` because most projects (including AIP) do not expose the AC custom field on the Epic issue type — the workflow appends a `## Acceptance Criteria` section to the description before creation.

If a project's Jira configuration **does** expose the AC field on Epic, set `issueTypeOverrides.Epic.acceptanceCriteriaMode = "adf-field"` in `.ai/jira.config.json`. The workflow will then write AC to `config.fieldIds.acceptanceCriteria` in a separate `editJiraIssue` call after creation, mirroring the Story pattern.

The package's drift checker (`verify-jira-config`) reports an `ac-mode-drift` finding whenever the configured mode disagrees with what the live project actually exposes.

## Issue Type IDs


| Issue Type | ID                       | API Name   |
| ---------- | ------------------------ | ---------- |
| Story      | `{{storyIssueTypeId}}`   | `Story`    |
| Task       | `{{taskIssueTypeId}}`    | `Task`     |
| Bug        | `{{bugIssueTypeId}}`     | `Bug`      |
| Sub-task   | `{{subTaskIssueTypeId}}` | `Sub-task` |
| Epic       | `{{epicIssueTypeId}}`    | `Epic`     |


## Format Type Rules

### Single-Select Fields

```json
{"value": "FieldValue"}
```

Used by: Work-Stream, Environment, Severity, Test Phase, Responsible Dev Team

### Multi-Select Fields

```json
[{"value": "FieldValue"}]
```

Used by: Channel, Teams

### Text Fields

```json
"Plain text content here"
```

Used by: Summary, Description

### User Fields

```json
{"accountId": "712020:7652882f-b99f-477d-825c-c95e878834fb"}
```

Used by: Reporter, Assignee

## Bug Field Allowed Values

### Environment (`{{bugEnvironmentFieldId}}`)


| Value        | Description                       |
| ------------ | --------------------------------- |
| `PRD`        | Production (most common for bugs) |
| `QA`         | Generic QA                        |
| `DEV`        | Generic Development               |
| `STG`        | Generic Staging                   |
| `STG2`       | Staging 2                         |
| `CDLQA`      | CDL Quality Assurance             |
| `CDLUAT`     | CDL User Acceptance Testing       |
| `Kanan-Dev1` | Kanan Development 1               |
| `Kanan-Dev2` | Kanan Development 2               |
| `Kanan-QA1`  | Kanan QA 1                        |
| `Kanan-QA2`  | Kanan QA 2                        |
| `Kanan-Stg1` | Kanan Staging 1                   |
| `Kanan-Stg2` | Kanan Staging 2                   |
| `Kanan-Prod` | Kanan Production                  |
| `DL-Dev`     | DataLake Development              |
| `DL-Test1`   | DataLake Test 1                   |
| `DL-Test2`   | DataLake Test 2                   |
| `DL-Prod`    | DataLake Production               |
| `Rey-Dev1`   | Rey Development 1                 |
| `Rey-Dev2`   | Rey Development 2                 |
| `Rey-QA1`    | Rey QA 1                          |
| `Rey-QA2`    | Rey QA 2                          |
| `Rey-Stg1`   | Rey Staging 1                     |
| `Rey-Stg2`   | Rey Staging 2                     |
| `Rey-Prod`   | Rey Production                    |
| `Dragon1`    | Dragon Environment 1              |
| `Dragon2`    | Dragon Environment 2              |


### Severity (`{{bugSeverityFieldId}}`)


| Value   | Description                           |
| ------- | ------------------------------------- |
| `Sev 1` | Critical/blocking, system down        |
| `Sev 2` | Major functional issues (most common) |
| `Sev 3` | Minor issues, cosmetic problems       |
| `TBD`   | To be determined during triage        |


### Test Phase (`{{bugTestPhaseFieldId}}`)


| Value                | Description                             |
| -------------------- | --------------------------------------- |
| `QA`                 | Quality assurance testing (most common) |
| `UAT`                | User acceptance testing                 |
| `SIT`                | System integration testing              |
| `E2E`                | End-to-end testing                      |
| `BAT`                | Business acceptance testing             |
| `Data Certification` | Data validation testing                 |
| `Performance`        | Performance testing                     |
| `DR`                 | Disaster recovery testing               |
| `Production`         | Issues found in production              |


### Responsible Development Team (`{{bugResponsibleTeamFieldId}}`)


| Value             | Description                                 |
| ----------------- | ------------------------------------------- |
| `Pennymac`        | Internal Pennymac development (most common) |
| `Blend`           | Blend team                                  |
| `CallMiner`       | CallMiner team                              |
| `Capital Markets` | Capital Markets team                        |
| `Caylent`         | Caylent team                                |
| `CCAD`            | CCAD team                                   |
| `Closing Corp`    | Closing Corp team                           |
| `Docutech`        | Docutech team                               |
| `FoundEver`       | FoundEver team                              |
| `Hakkoda`         | Hakkoda team                                |
| `HomeStory`       | HomeStory team                              |
| `ICE`             | ICE team                                    |
| `Loan Logics`     | Loan Logics team                            |
| `Mace`            | Mace team                                   |
| `Salesforce`      | Salesforce team                             |
| `Surge`           | Surge team                                  |
| `Tavant`          | Tavant team                                 |
| `Tealium`         | Tealium team                                |


