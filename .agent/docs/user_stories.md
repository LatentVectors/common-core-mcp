Here is the refined **User Stories & Acceptance Criteria** document. This focuses on the professional and intentional nature of both homeschooling parents and classroom teachers, ensuring the tone reflects the serious work of education management.

---

# EduMatch MCP: User Stories (Sprint 1)

**Project:** EduMatch MCP
**Sprint Focus:** Core Functionality (Search & Lookup)
**Target Personas:**

1.  **The Intentional Parent:** A homeschool educator seeking to formalize learning experiences and align daily life with educational benchmarks.
2.  **The Adaptive Teacher:** A classroom educator looking to tailor curriculum to student interests while maintaining strict adherence to state standards.

---

## Story 1: The "Retroactive Alignment" (Experience to Record)

**As a** homeschool parent or teacher,
**I want to** describe a completed activity, field trip, or real-world experience to the AI,
**So that** I can identify which Common Core standards were addressed and articulate the educational value in my official logs or lesson plans.

### Context

Educators often seize "teachable moments" (e.g., a trip to a science center, a gardening project). They need to translate these rich, unstructured experiences into the rigid language of educational bureaucracy for reporting purposes.

### Acceptance Criteria

1.  **Input:** The user provides a natural language narrative (e.g., "We visited the planetarium, looked at constellations, and calculated the distance between stars.").
2.  **System Action:** The system queries the `find_relevant_standards` tool using the narrative text.
3.  **Output:** The system returns a list of relevant standards (with ID and text) and a generated reasoning explaining _how_ the activity met that standard.
4.  **Tone Check:** The system treats the activity as a valid educational event, not an "accident," and helps the user professionalize their documentation.

**Example Prompt:**

> "I took my class to the Natural History Museum today. We focused on the timeline of the Jurassic period and compared the sizes of different fossils. Can you find the Common Core standards this visit supported so I can add them to my weekly report?"

---

## Story 2: The "Interest-Based Planner" (Proactive Integration)

**As an** educator looking to engage a student,
**I want to** input a specific student interest (e.g., Minecraft, Baking, Robotics) alongside a target grade level,
**So that** I can discover standards that can be taught _through_ that activity.

### Context

Students learn best when engaged. Teachers and parents often want to build lessons around a child's obsession but need to ensure they aren't skipping required learning targets. This bridges the gap between "Fun" and "Required."

### Acceptance Criteria

1.  **Input:** The user provides a topic and a constraint (e.g., "Baking cookies, 3rd Grade Math").
2.  **System Action:** The system queries `find_relevant_standards` with a combined vector of the activity and the grade level context.
3.  **Output:** The system returns standards that are semantically viable (e.g., standards about measurement, volume, or fractions for baking).
4.  **Reasoning:** The generated explanation explicitly suggests the connection (e.g., "This standard applies because baking requires understanding fractions to measure ingredients.").

**Example Prompt:**

> "My 3rd grader is obsessed with baking. I want to build a math unit around doubling recipes and measuring ingredients. Which standards can we cover with this project?"

---

## Story 3: The "Jargon Decoder" (Curriculum Clarification)

**As a** parent or teacher reviewing administrative documents,
**I want to** ask about a specific standard code (e.g., `CCSS.ELA-LITERACY.RL.4.3`),
**So that** I can retrieve the full text and hierarchy to understand exactly what is required of the student.

### Context

Educational documentation is full of codes that are opaque to parents and hard to memorize for teachers. Users need a quick, authoritative lookup to verify requirements without leaving the chat interface.

### Acceptance Criteria

1.  **Input:** The user provides a specific Standard ID/Code.
2.  **System Action:** The system identifies the code format and calls `get_standard_details`.
3.  **Output:** The system returns the full object, including the parent Domain and Cluster text, allowing the LLM to explain the standard in plain English.
4.  **Error Handling:** If the code doesn't exist, the system returns a polite failure message or suggests the user try a keyword search instead.

**Example Prompt:**

> "The state curriculum guide lists '1.OA.B.3' as a prerequisite for next week. What is that standard, and what does it look like in practice?"
