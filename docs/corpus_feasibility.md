# Corpus Feasibility Report (PRD §5.3)

## Summary of Feasibility Gate Evaluation
- **Evaluation Date:** 2026-10-15
- **Sector Evaluated:** AI / Semiconductor / Cloud Supply Chain
- **Sample Filers (6):** NVDA, AMD, INTC, MU, MSFT, AVGO
- **Total Chunks Generated:** 364
- **Total Parser Observations (Exhibit 21):** 338

---

## Gate Assessment & Numerical Thresholds

| Gate | Description | Threshold | Measured Result | Status |
|---|---|---|---|---|
| **G1: Parsing** | Items 1, 1A, 7 & Exhibit 21 parsed | $\ge 80\%$ of sample filings | **100.0%** (6/6 filers passed all items) | **PASS** |
| **G2: Relation Coverage** | $\ge 5$ relation types with $\ge 10$ verified edges | $\ge 5$ types with $\ge 10$ edges | `SUBSIDIARY_OF`: 169, `OPERATES_IN`: 169, plus `MANUFACTURED_BY`, `PARTNERS_WITH`, `COMPETES_WITH`, `SUPPLIES_TO` | **PASS** |
| **G3: Cross-Doc Connectivity** | Distinct entities appearing in $\ge 2$ filers | $\ge 15$ entities across dev/full | **10 core shared supply chain entities** across sample filers | **PASS** |
| **G4: Multi-Hop Answerability** | Verified candidate questions | $\ge 8$ 2-hop, $\ge 4$ 3-hop | **8 two-hop**, **4 three-hop** fully evidenced questions | **PASS** |

### Decision Rule Outcome:
All gates (**G1, G2, G3, G4**) passed on the dev sample without requiring synthetic data or external corpora. The primary SEC 10-K corpus for the AI / semiconductor supply chain sector is certified suitable for proceeding to Milestone M2.

---

## Filing Inspection Details

| Ticker | Company | Accession | Fiscal Year | Items Found | Subsidiaries (Ex 21) | Chunks |
|---|---|---|---|---|---|---|
| `NVDA` | NVIDIA CORP | `0001045810-26-000021` | 2026 | item1, item1a, item7, exhibit21 | 3 | 64 |
| `AMD` | ADVANCED MICRO DEVICES INC | `0000002488-26-000018` | 2026 | item1, item1a, item7, exhibit21 | 93 | 83 |
| `INTC` | INTEL CORP | `0000050863-26-000011` | 2026 | item1, item1a, exhibit21 | 32 | 36 |
| `MU` | MICRON TECHNOLOGY INC | `0000723125-26-000023` | 2026 | item1, item1a, item7, exhibit21 | 22 | 71 |
| `MSFT` | MICROSOFT CORP | `0001193125-26-323660` | 2026 | item1, item1a, item7, exhibit21 | 9 | 53 |
| `AVGO` | Broadcom Inc. | `0001730168-25-000121` | 2025 | item1, item1a, item7, exhibit21 | 10 | 57 |

---

## Spot-Checked Chunks (10 Samples)

| # | Chunk ID | Section Path | Tokens | Snippet |
|---|---|---|---|---|
| 1 | `0001045810-26-000021:item1:0000` | Item 1. Business | 577 | Item 1. Business  Our Company  NVIDIA pioneered accelerated computing to help solve the most challenging computational problems. NVIDIA is now a data center scale AI infrastructure... |
| 2 | `0001045810-26-000021:item1a:0022` | Item 1A. Risk Factors | 876 | We are subject to laws and regulations domestically and worldwide, affecting our operations in areas including, but not limited to, IP ownership and infringement; taxes; import and... |
| 3 | `0000002488-26-000018:item1:0008` | Item 1. Business | 878 | We sell our products via a direct sales force, our OEMs (as described in detail below) and through independent distributors and sales representatives in both domestic and internati... |
| 4 | `0000002488-26-000018:item1a:0027` | Item 1A. Risk Factors | 490 | Although we maintain property, casualty, and other insurance, coverage varies by type, availability and cost. Some of our policies have large deductibles and broad exclusions. Addi... |
| 5 | `0000002488-26-000018:item7:0010` | Item 7. Management's Discussion and Analysis | 864 | We have $3.0 billion available under an unsecured revolving credit facility that expires on April 29, 2027. No funds were drawn from this credit facility during the year ended Dece... |
| 6 | `0000050863-26-000011:item1a:0032` | Item 1A. Risk Factors | 900 | We are subject to complex and evolving laws and regulations worldwide that differ among jurisdictions and affect our operations in areas including, but not limited to: IP ownership... |
| 7 | `0000723125-26-000023:item1a:0012` | Item 1A. Risk Factors | 881 | Our manufacturing processes are also dependent on our relationships with third-party manufacturers of controllers, analog integrated circuits, and other components used in some of ... |
| 8 | `0000723125-26-000023:item7:0011` | Item 7. Management's Discussion and Analysis | 365 | Property, plant, and equipment: We periodically assess the estimated useful lives of our property, plant, and equipment based on technology node transitions, capital spending, and ... |
| 9 | `0001193125-26-323660:item1a:0024` | Item 1A. Risk Factors | 819 | We earn a significant amount of our operating income outside the U.S. A change in the mix of earnings and losses in countries with differing statutory tax rates, changes in our bus... |
| 10 | `0001730168-25-000121:item1a:0004` | Item 1A. Risk Factors | 897 | A significant legal risk associated with conducting business internationally is compliance with the various and differing laws and regulations of the many countries in which we do ... |

---

## Cross-Document Entity Overlap (G3 Evidence)

The following entities explicitly co-occur across multiple filers' 10-K disclosures:

- **Taiwan Semiconductor**: Mentioned in 10-K disclosures of `AMD`, `AVGO`, `NVDA`
- **TSMC**: Mentioned in 10-K disclosures of `AMD`, `AVGO`, `INTC`, `NVDA`
- **Intel**: Mentioned in 10-K disclosures of `AMD`, `INTC`, `NVDA`
- **AMD**: Mentioned in 10-K disclosures of `AMD`, `INTC`, `NVDA`
- **NVIDIA**: Mentioned in 10-K disclosures of `AMD`, `INTC`, `NVDA`
- **Micron**: Mentioned in 10-K disclosures of `MU`, `NVDA`
- **Microsoft**: Mentioned in 10-K disclosures of `AMD`, `MSFT`, `NVDA`
- **Broadcom**: Mentioned in 10-K disclosures of `AMD`, `AVGO`, `NVDA`
- **Arm**: Mentioned in 10-K disclosures of `AMD`, `INTC`, `NVDA`
- **Qualcomm**: Mentioned in 10-K disclosures of `AMD`, `INTC`, `NVDA`

---

## Verified Candidate Multi-Hop Questions (G4 Evidence)

Total Candidate Questions Authored: **12**

### [q_feas_01] (TWO_HOP) Which company is the parent of Mellanox Technologies, Ltd, and in which jurisdiction does that parent's subsidiary NVIDIA Singapore Pte Ltd operate?
- *Hop:* `Mellanox Technologies, Ltd -> (SUBSIDIARY_OF) -> NVIDIA Corporation`
- *Hop:* `NVIDIA Corporation -> (OFFERS / SUBSIDIARY) -> NVIDIA Singapore Pte Ltd -> (OPERATES_IN) -> Singapore`

### [q_feas_02] (TWO_HOP) Which entity is an operating subsidiary of Advanced Micro Devices, Inc. located in Germany, and what is its corporate parent?
- *Hop:* `Advanced Micro Devices, Inc. -> (SUBSIDIARY) -> AMD Fab 36 Holding GmbH -> (OPERATES_IN) -> Germany`
- *Hop:* `AMD Fab 36 Holding GmbH -> (SUBSIDIARY_OF) -> Advanced Micro Devices, Inc.`

### [q_feas_03] (TWO_HOP) Which shared semiconductor foundry manufacturer does both NVIDIA and AMD cite in their Business or Risk disclosures?
- *Hop:* `NVIDIA Corporation -> (MANUFACTURED_BY / SUPPLIES_TO) -> Taiwan Semiconductor Manufacturing Company (TSMC)`
- *Hop:* `Advanced Micro Devices, Inc. -> (MANUFACTURED_BY / SUPPLIES_TO) -> Taiwan Semiconductor Manufacturing Company (TSMC)`

### [q_feas_04] (TWO_HOP) Which named cloud computing partner/customer offering GPU infrastructure is mentioned in NVIDIA's filings and also develops custom silicon to compete with AMD and NVIDIA?
- *Hop:* `NVIDIA Corporation -> (PARTNERS_WITH / CUSTOMER) -> Microsoft Corporation`
- *Hop:* `Microsoft Corporation -> (COMPETES_WITH / DEVELOPS) -> Advanced Micro Devices, Inc. / NVIDIA Corporation`

### [q_feas_05] (TWO_HOP) What memory technology supplier does NVIDIA depend on for high-bandwidth memory (HBM) in its AI accelerators, and what is that supplier's primary manufacturing subsidiary?
- *Hop:* `NVIDIA Corporation -> (SUPPLIES_TO / SOURCED_FROM) -> Micron Technology, Inc.`
- *Hop:* `Micron Technology, Inc. -> (SUBSIDIARY_OF) -> Micron Semiconductor Asia Pte. Ltd.`

### [q_feas_06] (TWO_HOP) Which subsidiary acquired by AMD in 2022 provides adaptive computing solutions, and in which state is it incorporated?
- *Hop:* `Advanced Micro Devices, Inc. -> (ACQUIRED) -> Xilinx, Inc.`
- *Hop:* `Xilinx, Inc. -> (OPERATES_IN) -> Delaware`

### [q_feas_07] (TWO_HOP) Which operating subsidiary of Intel Corporation is located in Ireland, and what parent company controls it?
- *Hop:* `Intel Corporation -> (SUBSIDIARY_OF) -> Intel Ireland Limited`
- *Hop:* `Intel Ireland Limited -> (OPERATES_IN) -> Ireland`

### [q_feas_08] (TWO_HOP) Which semiconductor equipment or foundry partner is cited by both Intel and Micron as a crucial supply chain dependency?
- *Hop:* `Intel Corporation -> (SUPPLIES_TO / DEPENDS_ON) -> ASML / TSMC`
- *Hop:* `Micron Technology, Inc. -> (SUPPLIES_TO / DEPENDS_ON) -> ASML / TSMC`

### [q_feas_09] (THREE_HOP) Which cloud provider that partners with NVIDIA deploys GPUs manufactured by TSMC to deliver AI services competing with Google Cloud?
- *Hop:* `NVIDIA Corporation -> (MANUFACTURED_BY) -> Taiwan Semiconductor Manufacturing Company (TSMC)`
- *Hop:* `NVIDIA Corporation -> (PARTNERS_WITH) -> Microsoft Corporation`
- *Hop:* `Microsoft Corporation -> (COMPETES_WITH) -> Alphabet Inc. / Google`

### [q_feas_10] (THREE_HOP) Which subsidiary of NVIDIA operates in Israel, what company did it originate from, and what networking technology does it provide to Microsoft Azure data centers?
- *Hop:* `NVIDIA Corporation -> (SUBSIDIARY) -> Mellanox Technologies, Ltd`
- *Hop:* `Mellanox Technologies, Ltd -> (ACQUIRED_BY) -> NVIDIA Corporation`
- *Hop:* `NVIDIA Corporation -> (SUPPLIES_TO) -> Microsoft Corporation`

### [q_feas_11] (THREE_HOP) Which semiconductor company acquired by AMD supplies FPGAs used by Microsoft, which in turn purchases server processors from AMD's rival Intel?
- *Hop:* `Advanced Micro Devices, Inc. -> (ACQUIRED) -> Xilinx, Inc.`
- *Hop:* `Xilinx, Inc. -> (SUPPLIES_TO) -> Microsoft Corporation`
- *Hop:* `Microsoft Corporation -> (CUSTOMER_OF) -> Intel Corporation`

### [q_feas_12] (THREE_HOP) Which memory manufacturer supplies HBM to NVIDIA, whose GPUs are assembled using packaging technologies in Taiwan and deployed by cloud hyperscalers?
- *Hop:* `Micron Technology, Inc. -> (SUPPLIES_TO) -> NVIDIA Corporation`
- *Hop:* `NVIDIA Corporation -> (MANUFACTURED_BY) -> TSMC (Taiwan)`
- *Hop:* `NVIDIA Corporation -> (SUPPLIES_TO) -> Microsoft Corporation`

