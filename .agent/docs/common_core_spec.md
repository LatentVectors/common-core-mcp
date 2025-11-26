This is the authoritative **Common Core Data Specification**. It contains the exact source locations, data schemas, field definitions, and the specific processing logic required to interpret the hierarchy correctly.

**Use this document as the source of truth for `tools/build_data.py`.**

---

# Data Specification: Common Core Standards

**Authority:** Common Standards Project (GitHub)
**License:** Creative Commons Attribution 4.0 (CC BY 4.0)
**Format:** JSON (Flat List of Objects)

## 1. Source Locations

We are using the "Clean Data" export from the Common Standards Project. These files are static JSON dumps where each file represents a full Subject.

| Subject            | Direct Download URL                                                                                                          |
| :----------------- | :--------------------------------------------------------------------------------------------------------------------------- |
| **Mathematics**    | `https://raw.githubusercontent.com/commoncurriculum/common-standards-project/master/data/clean-data/CCSSI/Mathematics.json`  |
| **ELA / Literacy** | `https://raw.githubusercontent.com/commoncurriculum/common-standards-project/master/data/clean-data/CCSSI/ELA-Literacy.json` |

---

## 2. The Data Structure (Glossary)

The JSON file contains a root object. The actual standards are located in the `standards` dictionary, keyed by their internal GUID.

### **Root Object**

```json
{
  "subject": "Mathematics",
  "standards": {
    "6051566A...": { ... }, // Standard Object
    "5E367098...": { ... }  // Standard Object
  }
}
```

### **Standard Object (The Item)**

Each item represents a node in the curriculum tree. It could be a broad **Domain**, a grouping **Cluster**, or a specific **Standard**.

| Field Name              | Type            | Definition & Usage                                                                                                                    |
| :---------------------- | :-------------- | :------------------------------------------------------------------------------------------------------------------------------------ |
| **`id`**                | `String (GUID)` | The internal unique identifier. Used for lookups in `ancestorIds`.                                                                    |
| **`statementNotation`** | `String`        | **The Display Code.** (e.g., `CCSS.Math.Content.1.OA.A.1`). This is what teachers recognize. Use this for the UI.                     |
| **`description`**       | `String`        | The text content. **Warning:** For standards, this text is often incomplete without its parent context (see Hierarchy below).         |
| **`statementLabel`**    | `String`        | The hierarchy type. Critical values: <br>• `Domain` (Highest) <br>• `Cluster` (Grouping) <br>• `Standard` (The actionable item)       |
| **`gradeLevels`**       | `Array[String]` | Scope of the standard. <br>• Format: `["01", "02"]` (Grades 1 & 2), `["K"]` (Kindergarten), `["09", "10", "11", "12"]` (High School). |
| **`ancestorIds`**       | `Array[GUID]`   | **CRITICAL.** An ordered list of parent IDs (from root to immediate parent). You must resolve these to build the full context.        |

---

## 3. Hierarchy & Context (The "Interpretation" Problem)

**The Problem:**
A standard's description often relies on its parent "Cluster" for meaning.

- _Cluster Text:_ "Understand the place value system."
- _Standard Text:_ "Recognize that in a multi-digit number, a digit in one place represents 10 times as much..."

If you only embed the _Standard Text_, the vector will miss the concept of "Place Value."

**The Solution (Processing Logic):**
To generate the **Search String** for embedding, you must concatenate the hierarchy.

1.  **Domain:** The broad category (e.g., "Number and Operations in Base Ten").
2.  **Cluster:** The specific topic (e.g., "Generalize place value understanding").
3.  **Standard:** The task.

**Formula:**

```text
"{Subject} {Grade}: {Domain Text} - {Cluster Text} - {Standard Text}"
```

---

## 4. Build Pipeline Specification (`tools/build_data.py`)

This specific logic ensures we extract meaningful vectors.

### **Step A: Ingestion**

1.  Download both JSON files.
2.  Merge the `standards` dictionaries into a single **Lookup Map** (Memory: `Map<GUID, Object>`).

### **Step B: Iteration & Filtering**

Iterate through the Lookup Map.
**Filter Rule:**

- **KEEP** if `statementLabel` equals `"Standard"`.
- **DISCARD** if `statementLabel` is `"Domain"`, `"Cluster"`, or `"Component"`. (We only index the actionable leaves).

### **Step C: Context Resolution (The "Breadcrumb" Loop)**

For every kept Standard:

1.  Initialize `context_text = ""`
2.  Iterate through `ancestorIds`:
    - Use the ID to look up the Parent Object in the **Lookup Map**.
    - Append `Parent.description` to `context_text`.
3.  Construct the final string:
    - `full_text = f"{context_text} {current_standard.description}"`
4.  **Vectorize `full_text`**.

### **Step D: Output Schema (`data/standards.json`)**

The clean, flat JSON file you save for the App to load must look like this:

```json
[
  {
    "id": "CCSS.Math.Content.1.OA.A.1", // From 'statementNotation'
    "guid": "6051566A...", // From 'id'
    "grade": "01", // From 'gradeLevels[0]'
    "subject": "Mathematics", // From 'subject'
    "description": "Use addition and subtraction within 20 to solve word problems...", // From 'description'
    "full_context": "Operations and Algebraic Thinking - Represent and solve problems... - Use addition and..." // The text we used for embedding
  }
]
```

---

## 5. Summary of Valid `gradeLevels`

When processing, normalize these strings if necessary, but typically they appear as:

- `K` (Kindergarten)
- `01` - `08` (Grades 1-8)
- `09-12` (High School generic)

_Note: If `gradeLevels` is an array `["09", "10", "11", "12"]`, you can display it as "High School" or "Grades 9-12"._
