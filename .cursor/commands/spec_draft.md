I am working on developing a comprehensive spec document for the next development sprint.

<goal>
Solidify the current spec_draft document into a comprehensive specification for the next development sprint through iterative refinement. 

The spec draft represents the rough notes and ideas for the next sprint. These notes are likely incomplete and require additional details and decisions to obtain sufficient information to move forward with the sprint.

READ: @.cursor/commands/finalize_spec.md to see the complete requirements for the finalized spec. The goal is to reach the level of specificity and clarity required to create this final spec. 
</goal>

<process>
<overview>
    Iteratively carry out the following steps to progressively refine the requirements for this sprint. Use `Requests for Input` only to gather information that cannot be inferred from the user's selection of a Recommendation; do not ask to confirm details already specified by a selected option. The initial `spec_draft` may be a loose assortment of notes, ideas, and thoughts; treat it accordingly in the first round.

    First round: produce a response that includes Recommendations and Requests for Input. The user will reply by selecting exactly one option per Recommendation (or asking for refinement if none fit) and answering only those questions that cannot be inferred from selected options.

    After each user response: update the `spec_draft` to incorporate the selected options with minimal, focused edits. Remove any conflicting or superseded information made obsolete by the selection. Avoid unrelated formatting or editorial changes.

    Repeat this back-and-forth until ambiguity is removed and the draft aligns with the requirements in `@.cursor/commands/finalize_spec.md`.
</overview>

<steps>
    - READ the spec_draft.
    - IDENTIFY anything in the spec draft that is confusing, conflicting, unclear, or missing. Identify important decisions that need to be made.
    - REVIEW the current state of the project to fully understand how these new requirements fit into what already exists.
    - RECOMMEND specific additions or updates to the draft spec to resolve confusion, add clarity, fill gaps, or add specificity. Recommendations may provide a single option when appropriate or multiple options when needed. Each Recommendation expects selection of one and only one option by the user.
    - ASK targeted questions to acquire details, decisions, or preferences from the user.
    - APPLY the user's selections: make minimal, localized edits to the `spec_draft` to incorporate the chosen options and remove conflicting content. Incorporate all information contained in the selected options; do not omit details. Do not change unrelated text, structure, or formatting.
    - REFINE: if the user rejects the provided options, revise the Recommendations based on feedback and repeat selection and apply.
</steps>

<end_conditions>
    - Continue this process until the draft is unambiguous and conforms to `@.cursor/commands/finalize_spec.md`, or the user directs you to do otherwise.
    - Do not stop after a single round unless the draft already satisfies all requirements in `@.cursor/commands/finalize_spec.md`.
</end_conditions>
</process>

<response>
<overview>
    Your responses should be focused on providing clear, concrete recommendations for content to add to the spec draft to resolve ambiguity, add specificity, and increase clarity for the sprint. The options you provide in your recommendations should provide complete content that can be incorporated into the spec draft. For each Recommendation, expect the user to select exactly one option; Recommendations may include a single option when appropriate. If no option fits, the user may request refinement. If you do not have sufficient understanding of the user's intent or the meaning of some element of the spec draft, use `Request for Input` sections to ask targeted questions of the user. Only ask for information that cannot be inferred from the user's selection of a Recommendation. Do not ask to confirm details already encoded in an option (e.g., if Option 1.1 specifies renaming a file to `foo.py`, do not ask to confirm that rename).

    Using incrementing section numbers are essential for helping the user quickly reference specific options or questions in their responses.
    Responses must strictly follow the Format section. Include only the specified sections and no additional commentary or subsections.
    The agent is responsible for updating the spec draft after each user response.
</overview>

<guidelines>
    - Break recommendations and requests for input into related sections to provide concrete options or ask targeted questions to the user.
    - Focus sections on a specific, concrete decision or unit of work related to the sprint outlined in the spec draft.
    - Recommendations may provide one or more options; when multiple options are presented, the user must select exactly one.
    - `Requests for Input` may include one or more questions, but only for details that cannot be derived from the selected option(s).
    - Do not ask confirmation questions about facts stated by options; assume the selected option is authoritative.
    - Use numbered sections that increment.
    - Use incrementing decimals for recommendation options and request for input questions.
    - After the user selects options, apply minimal, focused edits to the `spec_draft` reflecting only those selections. Remove conflicting or superseded content. Avoid broad formatting or editorial changes to unrelated content.
    - Do not clutter options or questions with information already clear and unambiguous from the current draft.
    - Do not add subsections beyond those defined in the Format.
</guidelines>

<format>

# Recommendations
## 1: Section Title
Short overview providing background on the section.

**Option 1.1**
Specifics of the first option.

**Option 1.2**
Specifics of the second option.

## 2: Section Title
Short overview providing background on the section.

**Option 2.1**
Specifics of the first option.

# Request for Input
## 3: Section Title
Short overview providing background on the section.

**Questions**
- 3.1 Some question.
- 3.2 Another question.

</format>
<user_selection_format>
    Respond by indicating a single selection per Recommendation, e.g.: `Select 1.2, 2.1`. If no option fits, reply with `Refine 1:` followed by feedback to guide revised options. You may also answer targeted questions under `Request for Input` inline.

    Example mixed selections and answers:

```text
1.1 OK
2: Clarifying question from the user?
3.1 OK
4.1 OK
5.1 OK
6: Answer to the specific question.
7 Directions that indicate the users preference in response to the question.
8 Clear directive in response to the question.
```
</user_selection_format>

<selection_and_editing_rules>
    - One and only one option must be selected per Recommendation. If none fit, request refinement.
    - Apply edits narrowly: change only text directly impacted by the chosen option(s).
    - Incorporate all information from the selected options into the draft.
    - Remove or rewrite conflicting statements made obsolete by the selection.
    - Preserve unrelated content and overall formatting; do not perform wide editorial passes.
</selection_and_editing_rules>
</response>

<guardrails>
    - Only edit the draft to apply selected options and answers. Do not edit code or any other files.
</guardrails>

<finalize_spec_compliance_checklist>
- [ ] All information required by @.cursor/commands/finalize_spec.md is present.
- [ ] Requirements are testable and unambiguous.
- [ ] Risks, dependencies, and assumptions captured.
- [ ] Approval received.
</finalize_spec_compliance_checklist>