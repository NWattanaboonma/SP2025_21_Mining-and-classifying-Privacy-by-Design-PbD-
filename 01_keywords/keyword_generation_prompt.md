# AI prompt for keyword generation (report Listing 4.3.1)

Used with Gemini to generate 100 candidate keywords per domain (government, health, IoT, general).
The output was then verified manually and reduced to the top-30 keywords per domain using cosine
similarity to the domain centroid (report Section 4.3.1, Step 1.2; Tables 5.1 and 5.2).
The final keyword lists are in [`Keyword_domain.md`](Keyword_domain.md).

```
AI Role: Assistant for GitHub open-source repository discovery and metadata analysis.

Objective: Identify and collect as many GitHub repositories as possible that belong to each
specified domain. The goal is to maximize repository recall - finding the largest possible volume
of relevant repositories - by generating a high-density keyword matrix.

Domain Definitions:
1. Government Domain: This domain encompasses public sector services, processes, and functions
   that directly impact citizens or legal entities on a large scale.
2. Health Domain: This domain includes case studies focused on the healthcare sector, including
   systems for hospital management, patient data records (EHRs), and other digital health
   technologies that handle sensitive health data.
3. Internet of Things (IoT) Domain: This domain covers interconnected devices and systems
   designed for personal convenience, self-monitoring, and automating parts of daily life.

Case studies domain:
1. Government: Electronic-ID Card, Electronic-Health Card, ELENA, ePetition, Electronic Toll
   Pricing, Ontario TTC initiative, Ontario OLG casinos initiative.
2. Health: Privacy By Design Speech Assistant, Personal e-Health systems
3. Internet of Things (IoT): SensiTrack, Car Finder, Gym Monitoring, Britains Smart Meter Programme.

Case studies are seed knowledge only. Use them to infer the domain scope and generate additional
keywords beyond the case-study names.
Each domain keyword list must contain a mix of:
  (1) Seed-derived keywords (directly from case studies / closely related tech terms) and
  (2) AI-inferred generalized system keywords (common repo naming terms in GitHub for that domain).
Do not overfit to case-study proper nouns; prioritize developer-used repository naming terms.

4. General (Functional & Privacy): Refers to domain-agnostic terms that describe privacy-related
   concerns, risks, or functional behaviors commonly found in software systems regardless of
   application domain.

These terms:
* Do not identify a specific domain (e.g., e-government, healthcare, IoT)
* Represent privacy issues, security failures, or data-handling concerns
* Can be combined with domain-specific keywords to surface real-world privacy issues in GitHub repositories

Strict Selection Constraints:
1. Output Format:
   a. Provide one Python list per domain.
   b. Keywords must be ordered in ascending order of value according to the ranking requirement.
   c. Each keyword must include its justification as an inline Python comment, placed directly
      after the keyword.
2. Morphology: Keywords can be single nouns or standard industry compound terms
   (e.g., smart-home, e-government).
3. Mutual Exclusivity: Each keyword must appear in exactly one of the four lists. If a keyword
   plausibly applies to multiple domains, place it in General (Functional & Privacy), not in
   domain lists.
4. Noise Reduction: Strictly exclude generic software tokens (e.g., app, system, code,
   repository, fix, issue, user, data, key, log, node).
5. Semantic Precision: Avoid polysemous words (words with multiple meanings) such as state,
   policy, light, car, or bridge. When a case study name contains a polysemous word, convert it
   to a more specific compound term used by developers.
6. Recall Strategy: Include a mixture of "Expert" technical jargon and "Simple" functional nouns.
7. Volume: Target exactly 100 entries per domain (400 entries total).
```
