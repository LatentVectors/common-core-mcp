I am working on developing a comprehensive spec document for the next development sprint.

<goal>
Solidify the current spec document into a comprehensive specification for the next development sprint through iterative refinement.

The spec draft represents the rough notes and ideas for the next sprint. These notes are likely incomplete and require additional details and decisions to obtain sufficient information to move forward with the sprint.

READ: `<finalized_spec_requirements>` to see the complete requirements for the finalized spec. The goal is to reach the level of specificity and clarity required to create this final spec.
</goal>

<process>
<overview>

    Iteratively carry out the following steps to progressively refine the requirements for this sprint. Use `Requests for Input` only to gather information that cannot be inferred from the user's selection of a Recommendation; do not ask to confirm details already specified by a selected option. The initial spec draft may be a loose assortment of notes, ideas, and thoughts; treat it accordingly in the first round.

    First round: produce a response that includes Recommendations and Requests for Input. The user will reply by selecting exactly one option per Recommendation (or asking for refinement if none fit) and answering only those questions that cannot be inferred from selected options.

    After each user response: update the spec draft to incorporate the selected options with minimal, focused edits. Remove any conflicting or superseded information made obsolete by the selection. Avoid unrelated formatting or editorial changes.

    Repeat this back-and-forth until ambiguity is removed and the draft aligns with the requirements in `<finalized_spec_requirements>`.

</overview>

<steps>
    - READ the spec draft.
    - IDENTIFY anything in the spec draft that is confusing, conflicting, unclear, or missing. Identify important decisions that need to be made.
    - REVIEW the current state of the project to fully understand how these new requirements fit into what already exists.
    - RESEARCH any technical questions, library options, or implementation approaches that need to be resolved. Conduct this research during spec development so that specific, concrete guidance can be included in the final spec rather than leaving research tasks for the implementer.
    - RECOMMEND specific additions or updates to the draft spec to resolve confusion, add clarity, fill gaps, or add specificity. Recommendations may provide a single option when appropriate or multiple options when needed. Each Recommendation expects selection of one and only one option by the user.
    - ASK targeted questions to acquire details, decisions, or preferences from the user.
    - APPLY the user's selections: make minimal, localized edits to the spec draft to incorporate the chosen options and remove conflicting content. Incorporate all information contained in the selected options; do not omit details. Do not change unrelated text, structure, or formatting.
    - REFINE: if the user rejects the provided options, revise the Recommendations based on feedback and repeat selection and apply.
</steps>

<end_conditions> - Continue this process until the draft is unambiguous and conforms to `<finalized_spec_requirements>`, or the user directs you to do otherwise. - Do not stop after a single round unless the draft already satisfies all requirements in `<finalized_spec_requirements>`.
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
    - After the user selects options, apply minimal, focused edits to the spec draft reflecting only those selections. Remove conflicting or superseded content. Avoid broad formatting or editorial changes to unrelated content.
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

<selection_and_editing_rules> - One and only one option must be selected per Recommendation. If none fit, request refinement. - Apply edits narrowly: change only text directly impacted by the chosen option(s). - Incorporate all information from the selected options into the draft. - Remove or rewrite conflicting statements made obsolete by the selection. - Preserve unrelated content and overall formatting; do not perform wide editorial passes.
</selection_and_editing_rules>
</response>

<guardrails>
    - Only edit the draft to apply selected options and answers. Do not edit code or any other files.
</guardrails>

<finalize_spec_compliance_checklist>

- [ ] All information required by `<finalized_spec_requirements>` are present.
- [ ] Requirements are testable and unambiguous.
- [ ] All research completed and findings documented in the spec.
- [ ] All decisions made and documented; no decision-making left for the implementer.
- [ ] No research tasks or decision points left for the implementer (or explicitly documented as blockers).
- [ ] Risks, dependencies, and assumptions captured.
- [ ] Approval received.

</finalize_spec_compliance_checklist>

<finalized_spec_requirements>
The spec acts as the comprehensive source of truth for this sprint and should include all the necessary context and technical details to implement this sprint. It should leave no ambiguity for important details necessary to properly implement the changes required.

The spec.md will act as a reference for an LLM coding agent responsible for completing this sprint.

The spec must not include any directions for the implementer to conduct research or make decisions. All research must be completed during spec development, and all decisions must be made and documented in the spec. If there are pending decisions or research that cannot be completed during spec development, these must be explicitly documented as blockers or prerequisites that prevent implementation from proceeding.

The spec should include the following information if applicable:

- An overview of the changes implemented in this sprint.
- User stories for the new functionality, if applicable.
- An outline of any new data models proposed.
- An other technical details determined in the spec_draft or related conversations.
- Specific filepaths for files for any files that need to be added, edited, or deleted as part of this sprint.
- Specific files or modules relevant to this sprint.
- Details on how things should function such as a function, workflow, or other process.
- Describe what any new functions, services, ect. are supposed to do.
- Any reasoning or rationale behind decisions, preferences, or changes that provides context for the sprint and its changes.
- Any other information required to properly understand this sprint, the desired changes, the expected deliverables, or important technical details.

Strive to retain all the final decisions and implementation details provided in the spec draft and related conversations. Cleaning and organizing these raw notes is desirable, but do not exclude or leave out information provided in the spec draft if it is relevant to this sprint. If there is information in the spec draft that is outdated and negated or revised by further direction in the draft or related conversation, you should leave that stale information out of the final spec.

The spec should have all the information a junior developer needs to complete this sprint. They should be able to independently find answers to any questions they have about this sprint and how to implement it in this document. The spec defines exactly what should be implemented and how; it does not require the implementer to make decisions or conduct research. All technical research, library selection, design decisions, and implementation approaches must be resolved and documented in the spec before implementation begins.

**Code Examples in Specs:**
Use code examples sparingly and only when they provide clarity that text cannot achieve. Keep examples small and focused on specific scenarios, usage patterns, or situations that are difficult to express concisely in prose. Prefer code examples when they are more explicit or concise than equivalent text descriptions. Avoid code examples for obvious implementations or concepts that can be clearly explained in bullet points or brief text. If explicitly directed, longer code examples are appropriate. The guiding principle is to maintain a balance of conciseness, precision, and comprehensiveness—choose the format (code or text) that best achieves this balance.
</finalized_spec_requirements>
