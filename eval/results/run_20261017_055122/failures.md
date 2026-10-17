# Benchmark Failure Taxonomy and Qualitative Error Analysis

Detailed analysis of incorrect answers, retrieval misses, citation issues, and hallucinations.

## System A (Vector Baseline) Failures (0 / 5)

## System B (GraphMind Hybrid) Failures (3 / 5)

### Failure Mode: `retrieval_miss` (2 cases)
- **Question Q001** (single_hop): *"Who is the Chief Executive Officer of NVIDIA Corporation?"*
  - **Expected Answer:** Jen-Hsun Huang (also known as Jensen Huang) is the President and Chief Executive Officer of NVIDIA Corporation.
  - **Generated Response:** The provided filings do not contain sufficient evidence to answer this question....
  - **Retrieved Evidence:** `['wiki:39120:wiki_founding:0000', 'wiki:39120:wiki_founding:0000', 'wiki:39120:wiki_founding:0000']`
- **Question Q041** (three_hop): *"Jen-Hsun Huang previously worked as a microprocessor designer at which semiconductor company, which currently competes with NVIDIA in AI GPUs, and who is that competitor's current CEO?"*
  - **Expected Answer:** Jen-Hsun Huang worked as a microprocessor designer at AMD from 1983 to 1985; AMD currently competes with NVIDIA in data center AI GPUs; AMD is led by Dr. Lisa Su.
  - **Generated Response:** The provided filings do not contain sufficient evidence to answer this question....
  - **Retrieved Evidence:** `['wiki:39120:wiki_founding:0000', 'wiki:39120:wiki_founding:0000', 'wiki:39120:wiki_founding:0000']`

### Failure Mode: `generation_error` (1 cases)
- **Question Q021** (two_hop): *"Is Mellanox Technologies connected to NVIDIA, and what networking technology did it bring to NVIDIA's Data Center business?"*
  - **Expected Answer:** Mellanox Technologies is a wholly owned operating subsidiary of NVIDIA Corporation acquired in April 2020 for $6.9 billion, which brought InfiniBand and high-speed Ethernet networking into NVIDIA's Data Center platform.
  - **Generated Response:** Entity mention 'Mellanox Technologies' is ambiguous. Please clarify which entity you mean....
  - **Retrieved Evidence:** `[]`
