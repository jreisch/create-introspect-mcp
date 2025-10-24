# Agent Skills: Comprehensive Research and Patterns

> Research document synthesizing official Agent Skills documentation with analysis of 15+ real-world skill examples from the Anthropic skills repository.

**Research Date:** 2025-10-23
**Purpose:** Foundation for creating the `create-introspect-mcp` Agent Skill

---

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Official Specification](#official-specification)
3. [Patterns from Real Examples](#patterns-from-real-examples)
4. [Category Analysis](#category-analysis)
5. [Best Practices Synthesis](#best-practices-synthesis)
6. [Creating New Skills](#creating-new-skills)

---

## Core Concepts

### What Are Agent Skills?

Agent Skills are **modular, self-contained packages** that extend Claude's capabilities by providing specialized knowledge, workflows, and tool integrations. They act as "onboarding guides" that transform Claude from a general-purpose agent into a specialized agent equipped with procedural knowledge.

**Key Characteristics:**
- **Model-invoked:** Claude autonomously decides when to use skills based on request context and skill description
- **Self-contained:** Each skill is a complete package with all necessary resources
- **Progressive disclosure:** Information loaded hierarchically to manage context efficiently
- **Discoverable:** Description field determines when Claude activates the skill

### Progressive Disclosure Architecture

Skills use a three-level loading system:

```
Level 1: Metadata (name + description)
  ├─ Always in context (~100 words)
  └─ Determines if skill should activate

Level 2: SKILL.md body
  ├─ Loaded when skill triggers (<5k words recommended)
  └─ Core procedural knowledge

Level 3: Bundled Resources
  ├─ scripts/ - Executed without loading (token efficient)
  ├─ references/ - Loaded as needed (detailed docs)
  └─ assets/ - Used in output (never loaded)
```

**Benefits:**
- Efficient context window usage
- Scales to complex domains
- Clear separation of concerns
- Token-conscious design

---

## Official Specification

### Required File Structure

**Minimal Skill:**
```
my-skill/
  └── SKILL.md
```

**Complete Skill:**
```
skill-name/
├── SKILL.md (required)
├── LICENSE.txt (optional but recommended)
├── requirements.txt (if dependencies needed)
├── scripts/ (optional - executables)
├── references/ (optional - documentation to load)
└── assets/ (optional - output resources)
```

### SKILL.md Structure

**Required YAML Frontmatter:**
```yaml
---
name: skill-name
description: Complete description of what the skill does and when Claude should use it
---
```

**Optional Fields:**
```yaml
---
name: skill-name
description: Description here
license: Complete terms in LICENSE.txt
allowed-tools:
  - Read
  - Write
  - Bash
metadata:
  version: "1.0"
  author: "Your Name"
---
```

### Field Validation Rules

#### `name` Field
- **Format:** hyphen-case (lowercase with hyphens)
- **Characters:** Lowercase Unicode alphanumeric + hyphen only
- **Directory Match:** Must match directory name
- **Examples:**
  - ✅ `mcp-builder`
  - ✅ `slack-gif-creator`
  - ❌ `Skill_Name` (wrong case/character)
  - ❌ `skill name` (spaces not allowed)

#### `description` Field
- **Purpose:** Determines when Claude uses the skill
- **Voice:** Third-person perspective ("This skill should be used when...")
- **Quality:** Be specific about WHAT it does and WHEN to use it
- **Length:** Comprehensive enough for discovery (~1-3 sentences)

**Example Descriptions:**
```yaml
# Good - specific triggers and technologies
description: Guide for creating high-quality MCP servers that enable LLMs to interact with external services through well-designed tools. Use when building MCP servers to integrate external APIs or services, whether in Python (FastMCP) or Node/TypeScript (MCP SDK).

# Good - includes example user request
description: Toolkit for creating animated GIFs optimized for Slack. This skill applies when users request animated GIFs or emoji animations for Slack from descriptions like "make me a GIF for Slack of X doing Y".
```

### Bundled Resources

#### `scripts/` Directory
- **Purpose:** Executable code (Python/Bash/etc.)
- **When to use:** Deterministic reliability needed, token efficiency important
- **Loaded:** May execute WITHOUT loading into context
- **Examples:** Data processing, validation, conversion utilities

#### `references/` Directory
- **Purpose:** Documentation to load INTO context as needed
- **When to use:** API docs, schemas, policies, detailed guides
- **Loaded:** Only when Claude determines it's needed
- **Best Practice:** Move detailed info from SKILL.md to references/

#### `assets/` Directory
- **Purpose:** Files used in output, NOT loaded into context
- **When to use:** Templates, images, fonts, boilerplate
- **Loaded:** Never - used directly in final output
- **Examples:** PowerPoint templates, brand assets, font files

---

## Patterns from Real Examples

### Writing Style Patterns

**Imperative/Infinitive Form (Correct):**
```markdown
To accomplish X, do Y
Load the following resources
Run the initialization script
Create a comprehensive plan
```

**Second Person (Incorrect):**
```markdown
❌ You should do X
❌ If you need to do X
❌ Your task is to...
```

### Documentation Structure Patterns

**Pattern 1: Process-Oriented (mcp-builder)**
```markdown
# Skill Title

## Overview
[Clear explanation of purpose]

## High-Level Workflow
[Phase overview]

### Phase 1: Research and Planning
[Detailed steps with resource loading instructions]

### Phase 2: Implementation
[Detailed steps]

### Phase 3: Review and Refine
[Quality checks]

## Reference Files
[List with loading guidance]
```

**Pattern 2: Toolkit Pattern (slack-gif-creator)**
```markdown
# Skill Title - Toolkit

[Overview paragraph]

## Requirements
[Technical constraints]

## Toolkit Structure
[Component explanation]

## Core Components
[Essential tools with code examples]

## Helper Utilities
[Optional tools]

## Troubleshooting
[Common issues and solutions]
```

**Pattern 3: Router Pattern (internal-comms)**
```markdown
# Skill Title

## How to Use This Skill

1. **Identify the communication type**
2. **Load appropriate guideline**:
   - File A for scenario X
   - File B for scenario Y
3. **Follow specific instructions**

## Available Guidelines
[List of references/ files with descriptions]
```

### Progressive Disclosure Patterns

**Mandatory Reading Pattern:**
```markdown
1. **MANDATORY - READ ENTIRE FILE**: Read [`reference.md`](reference.md)
   completely from start to finish. **NEVER set any range limits when reading
   this file.** Read the full content for detailed syntax, critical formatting
   rules, and best practices.
```

**Conditional Loading Pattern:**
```markdown
## Reference Files

Load these as needed during development:

### Core Documentation (Load First)
- [📋 Best Practices](./reference/best_practices.md)

### SDK Documentation (Load During Phase 1/2)
- **Python SDK**: Fetch from `https://example.com/README.md`

### Implementation Guides (Load During Phase 2)
- [🐍 Python Guide](./reference/python_guide.md)
```

**Decision Tree Pattern:**
```markdown
## Workflow Decision Tree

```
User task → Is it static?
    ├─ Yes → Simple approach (read file)
    └─ No → Complex approach (load references)
```
```

### Script Reference Patterns

**Pattern 1: Black-Box Philosophy**
```markdown
**Always run scripts with `--help` first** to see usage. DO NOT read the
source until you try running the script first and find that a customized
solution is absolutely necessary. These scripts can be very large and thus
pollute your context window.
```

**Pattern 2: Inline Usage Examples**
```markdown
Run the initialization script:
```bash
bash scripts/init-artifact.sh <project-name>
cd <project-name>
```
```

**Pattern 3: Full Command Documentation**
```markdown
# Single server
python scripts/with_server.py --server "npm run dev" --port 5173 -- python automation.py

# Multiple servers
python scripts/with_server.py \
  --server "cd backend && python server.py" --port 3000 \
  --server "cd frontend && npm run dev" --port 5173 \
  -- python test.py
```

---

## Category Analysis

### Document Skills (pdf, xlsx, pptx, docx)

**Key Patterns:**
1. **Workflow Decision Trees** - Clear routing based on task type
2. **Mandatory Reading Gates** - Enforce loading detailed documentation
3. **Validation Steps** - Built-in quality checks throughout workflow
4. **Shared Infrastructure** - Common `ooxml/` utilities across skills
5. **Multi-Tool Composition** - Orchestrate multiple scripts for complex workflows

**Structure Example:**
```
xlsx/
├── SKILL.md (workflow decision tree + quick reference)
├── ooxml.md (detailed technical reference)
├── scripts/
│   ├── recalc.py (formula validation)
│   └── inventory.py (data extraction)
└── ooxml/
    └── scripts/ (shared XML utilities)
```

**Best Practices:**
- Explicit good/bad examples to prevent common mistakes
- Industry standards embedded (e.g., Excel color conventions)
- Cross-platform compatibility handled explicitly
- JSON intermediate formats for inspection/debugging

### Creative/Design Skills (algorithmic-art, canvas-design, theme-factory)

**Key Patterns:**
1. **Philosophy-First Approach** - Conceptual framework before implementation
2. **Two-Phase Creation** - Philosophy (.md) → Expression (artifact)
3. **Template as Foundation** - Clear FIXED vs VARIABLE sections
4. **Pre-emptive Quality Control** - Assume feedback and address it upfront
5. **Self-Contained Artifacts** - Everything needed in one file

**Structure Example:**
```
algorithmic-art/
├── SKILL.md (philosophy creation + implementation guidance)
├── templates/
│   ├── viewer.html (Anthropic-branded artifact structure)
│   └── generator_template.js (p5.js best practices)
└── LICENSE.txt
```

**Best Practices:**
- Emphasis on craftsmanship throughout
- "Subtle reference" concept for depth
- Parameter-driven design (no mode switches)
- Anti-pattern warnings (what NOT to do)
- Resource bundling (80+ fonts, 10 themes)

### Developer Tools Skills (mcp-builder, skill-creator, artifacts-builder)

**Key Patterns:**
1. **Phase-Based Workflows** - Research → Implement → Review → Test
2. **External Documentation Loading** - WebFetch for latest specs
3. **Evaluation Infrastructure** - Automated testing and scoring
4. **Agent-Centric Design** - Optimized for AI consumption
5. **Template Generation** - Scaffolding utilities

**Structure Example:**
```
mcp-builder/
├── SKILL.md (phased workflow + resource loading)
├── scripts/
│   ├── evaluation.py (testing harness)
│   ├── connections.py (transport logic)
│   └── requirements.txt
└── references/
    ├── mcp_best_practices.md
    ├── python_mcp_server.md
    └── typescript_mcp_server.md
```

**Best Practices:**
- Context budget awareness (optimize for limited tokens)
- Quality checklists for validation
- Design principles embedded (tools for workflows, not API wrappers)
- Black-box script philosophy (preserve context)
- Iterative improvement workflows

### Communication Skills (internal-comms, slack-gif-creator)

**Key Patterns:**
1. **Router Architecture** - SKILL.md directs to specific guidelines
2. **Strict Formatting** - Templates for consistency
3. **Composable Building Blocks** - Primitives + philosophy
4. **Optimization Guidance** - Troubleshooting tiered solutions
5. **Graceful Degradation** - Fallbacks when tools unavailable

**Structure Example:**
```
slack-gif-creator/
├── SKILL.md (comprehensive toolkit documentation)
├── requirements.txt
├── core/
│   ├── gif_builder.py
│   ├── validators.py
│   └── [utility modules]
└── templates/
    ├── bounce.py
    ├── spin.py
    └── [animation primitives]
```

**Best Practices:**
- Context-aware instructions (gather info first)
- Type hints and docstrings throughout
- Helpful validation feedback (actionable suggestions)
- Example composition patterns (multi-phase animations)
- Keywords section for discovery

---

## Best Practices Synthesis

### 1. Description Best Practices

**Make descriptions discoverable:**
```yaml
# Include triggers, technologies, and example phrases
description: Toolkit for creating animated GIFs optimized for Slack, with validators for size constraints. Use when users request animated GIFs or emoji animations for Slack from descriptions like "make me a GIF for Slack of X doing Y".
```

**Include exclusions:**
```yaml
# Help Claude avoid false positives
description: Suite of tools for complex artifacts requiring state management, routing, or shadcn/ui components - not for simple single-file HTML/JSX artifacts.
```

**List scenarios explicitly:**
```yaml
# Be comprehensive
description: A set of resources for internal communications (status reports, leadership updates, 3P updates, company newsletters, FAQs, incident reports, project updates, etc.).
```

### 2. SKILL.md Organization

**Keep focused (target <5k words):**
- Essential procedural knowledge only
- Move detailed info to `references/`
- Information in ONE place (SKILL.md OR references, not both)

**Structure recommendations:**
1. Overview (what/why) - 1-2 paragraphs
2. When to use - Explicit scenarios
3. How to use - Clear workflow
4. Resource loading - When and how to load bundled files
5. Examples - Concrete usage patterns

**Progressive complexity:**
- Quick start section first
- Common tasks next
- Advanced features in references/
- Deep technical details in separate files

### 3. Script Design

**Black-box philosophy:**
```markdown
**Always run with `--help` first.** DO NOT read source code until absolutely necessary. Scripts can be large and pollute context.
```

**Comprehensive docstrings:**
```python
#!/usr/bin/env python3
"""
Module Name - Brief description.

This module provides functionality to:
- Feature 1 with details
- Feature 2 with details

Classes:
    ClassName: Description

Functions:
    function_name: Description

Usage:
    python script.py input.txt output.json
"""
```

**Self-contained examples:**
```python
if __name__ == '__main__':
    # Runnable example demonstrating usage
    print("Example: Creating output...")
    result = main_function(example_input)
    print(f"Result: {result}")
```

### 4. Resource Organization

**scripts/** - Executable, token-efficient
- Validation utilities
- Data processing
- Complex algorithms
- Repeated operations

**references/** - Load into context
- API documentation
- Detailed guides
- Best practices
- Database schemas
- Policy documents

**assets/** - Never loaded, used in output
- Templates (.pptx, .html)
- Images/logos
- Fonts
- Boilerplate code

### 5. Quality Patterns

**Validation checkpoints:**
```markdown
4. **CRITICAL**: Validate immediately after each edit and fix any
   validation errors before proceeding
```

**Pre-emptive quality control:**
```markdown
## FINAL STEP

**IMPORTANT**: The user ALREADY said "It isn't perfect enough."

Take a second pass. Go back and refine/polish further...
```

**Quality checklists:**
```markdown
## Quality Checklist

### Strategic Design
- [ ] Tools enable complete workflows
- [ ] Tool names reflect natural task subdivisions

### Implementation Quality
- [ ] All tools have descriptive documentation
- [ ] Error handling for all external calls
```

### 6. Context Management

**Explicit loading instructions:**
```markdown
**Load and read the following reference files:**
- [📋 Best Practices](./reference/best_practices.md) - Load first
- [🐍 Python Guide](./reference/python.md) - Load during implementation
```

**WebFetch for external docs:**
```markdown
**Fetch the latest protocol documentation:**

Use WebFetch to load: `https://example.com/docs/latest.txt`
```

**Grep patterns for large files:**
```markdown
For large reference files (>10k words), include search patterns:
- To find X, grep for "pattern"
- To find Y, search in section Z
```

---

## Creating New Skills

### Step-by-Step Process

#### 1. Planning

**Define scope:**
- What specific capability does this skill add?
- What tasks should trigger it?
- What knowledge/resources are needed?

**Identify triggers:**
- List keywords users might mention
- Define scenarios where skill applies
- Note exclusions (when NOT to use)

**Plan resources:**
- What scripts/utilities are needed?
- What documentation should be referenced?
- What templates/assets are required?

#### 2. Create Structure

**Minimal start:**
```bash
mkdir -p skill-name
cd skill-name
touch SKILL.md
```

**Add resources as needed:**
```bash
mkdir -p scripts
mkdir -p references
mkdir -p assets
```

#### 3. Write SKILL.md

**Start with frontmatter:**
```yaml
---
name: skill-name
description: Comprehensive description with triggers, technologies, and when to use. Include example phrases users might say.
---
```

**Add core content:**
```markdown
# Skill Title

## Overview
[1-2 paragraphs: what it does and why]

## When to Use
[Explicit list of scenarios]

## Workflow
[Step-by-step procedural guidance]

## Bundled Resources
[List scripts/references/assets with usage]

## Examples
[Concrete usage patterns]
```

#### 4. Add Supporting Files

**Scripts:**
- Include comprehensive docstrings
- Add --help support
- Provide usage examples
- Create requirements.txt if needed

**References:**
- Detailed API documentation
- Best practices guides
- Schema definitions
- Policy documents

**Assets:**
- Templates for output
- Brand resources
- Boilerplate code
- Font files

#### 5. Test and Iterate

**Testing approach:**
- Ask questions that should trigger the skill
- Verify bundled resources load correctly
- Check script execution
- Validate output quality

**Common issues:**
- Description too vague → Claude doesn't trigger skill
- YAML syntax errors → Skill doesn't load
- File paths incorrect → Resources not found
- Scripts don't execute → Permission or dependency issues

#### 6. Package and Deploy

**Personal skills:**
```bash
cp -r skill-name ~/.claude/skills/
```

**Project skills:**
```bash
cp -r skill-name .claude/skills/
git add .claude/skills/skill-name
git commit -m "Add skill-name skill"
```

**Plugin skills:**
- Package in plugin's `skills/` directory
- Distribute via marketplace or git

---

## Validation Checklist

### Required Elements
- [ ] SKILL.md exists at skill root
- [ ] Valid YAML frontmatter
- [ ] `name` field present and follows hyphen-case
- [ ] `name` matches directory name
- [ ] `description` field present and comprehensive
- [ ] No placeholder text in description

### Quality Elements
- [ ] Description uses third-person voice
- [ ] Description includes specific triggers
- [ ] Clear "when to use" guidance
- [ ] Workflow/process documented
- [ ] Bundled resources referenced and explained
- [ ] Writing style is imperative/infinitive
- [ ] SKILL.md is focused (<5k words recommended)
- [ ] Detailed info moved to references/
- [ ] No duplication between SKILL.md and references

### Technical Elements
- [ ] Scripts have proper shebangs (#!/usr/bin/env python3)
- [ ] Scripts include comprehensive docstrings
- [ ] Dependencies documented (requirements.txt)
- [ ] File paths are correct and portable
- [ ] Examples are tested and work
- [ ] License included (if applicable)

---

## Key Insights for MCP Introspection Skill

Based on analysis of 15+ skills, here's what to apply:

### 1. Follow mcp-builder Pattern
- **Phase-based workflow** (Research → Implement → Test)
- **External docs via WebFetch** (latest Python/igraph docs)
- **Evaluation infrastructure** (testing/validation)
- **Agent-optimized design** (token efficient, high-signal output)

### 2. Use Document Skills Patterns
- **Decision trees** for routing complexity
- **Validation checkpoints** throughout
- **Good/bad examples** to prevent mistakes
- **Script composition** for multi-step workflows

### 3. Apply Developer Tools Best Practices
- **Black-box scripts** to preserve context
- **Template generation** for scaffolding
- **Quality checklists** for validation
- **Iterative improvement** workflow

### 4. Structure Recommendation

```
create-introspect-mcp/
├── SKILL.md (workflow + resource loading)
├── scripts/
│   ├── introspect.py (runtime introspection)
│   ├── create_database.py (SQLite creation)
│   ├── create_mcp_server.py (server scaffolding)
│   ├── validate_server.py (testing utility)
│   └── requirements.txt
└── references/
    ├── database_schema.md (schema design patterns)
    ├── mcp_best_practices.md (server design)
    ├── introspection_guide.md (Python inspection)
    └── examples.md (complete walkthrough)
```

### 5. Key Features to Include
- **Module specification** as input
- **Automated introspection** of classes/functions
- **Database creation** with normalized schema
- **MCP server generation** (Python FastMCP)
- **Validation utilities** (test the server)
- **Claude Code integration** (.mcp.json setup)

---

## Conclusion

Agent Skills provide a powerful framework for extending Claude's capabilities in a modular, discoverable, and token-efficient way. The key to effective skill design is:

1. **Clear triggering** through comprehensive descriptions
2. **Progressive disclosure** to manage context efficiently
3. **Separation of concerns** (scripts/references/assets)
4. **Quality emphasis** throughout (validation, examples, checklists)
5. **Agent-centric design** (optimize for AI consumption)

The patterns observed across document, creative, developer, and communication skills provide a solid foundation for creating new skills in any domain.

---

## References

**Official Documentation:**
- Claude Code Agent Skills: https://docs.claude.com/en/docs/claude-code/agent-skills

**Analyzed Skills Repository:**
- Location: `~/dev/github/skills/`
- Skills analyzed: 15+ across 4 categories
- Examples: mcp-builder, skill-creator, pdf, xlsx, algorithmic-art, canvas-design, slack-gif-creator, internal-comms

**Research Date:** 2025-10-23
**Research Method:** Parallel Haiku agents analyzing skill categories + official documentation synthesis
