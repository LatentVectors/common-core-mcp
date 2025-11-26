Generate tasks from a spec document. The task should be broken into numbered sections with clear, cohesive, focused units of work. The generated tasks document must fully implement the requirements specified in the spec document.

<guidelines>
  - One unit of work per section: Each section delivers a single, clearly defined outcome an LLM can implement end-to-end in one pass.
  - Timebox: Target 30–40 minutes of dev work.
  - Size and focus: 3–7 concrete subtasks per section. Avoid grab-bag sections.
  - Boundaries: Keeps sections and tasks focused on a small subset of files, unless edits are simple and tightly related.
</guidelines>

<file_template>
  <header>
    # Spec Tasks
  </header>
</file_template>

<task_structure>
  <major_tasks>
    - count: 1-12
    - format: numbered checklist
    - grouping: by feature or component
  </major_tasks>
  <subtasks>
    - count: up to 8 per major task
    - format: decimal notation (1.1, 1.2)
  </subtasks>
</task_structure>

<task_template>
  ## Tasks

  - [ ] 1. [MAJOR_TASK_DESCRIPTION]
    - [ ] 1.1 [IMPLEMENTATION_STEP]
    - [ ] 1.2 [IMPLEMENTATION_STEP]
    - [ ] 1.3 [IMPLEMENTATION_STEP]

  - [ ] 2. [MAJOR_TASK_DESCRIPTION]
    - [ ] 2.1 [IMPLEMENTATION_STEP]
    - [ ] 2.2 [IMPLEMENTATION_STEP]
</task_template>

<ordering_principles>
  - Consider technical dependencies
  - Follow TDD approach
  - Group related functionality
  - Build incrementally
</ordering_principles>

</step>
