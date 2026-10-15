"""Generate 40 hand-verified (question, gold_chunk_ids) evaluation pairs (PRD FR-2.3, Milestone M4)."""

import json
from pathlib import Path

# 40 Hand-Verified Question-Chunk Ground Truth Pairs across 6 filers (PRD FR-2.3)
RETRIEVAL_PAIRS = [
    # --- AMD (7 questions) ---
    {
        "id": "RET_01",
        "ticker": "AMD",
        "question": "Who are AMD's primary competitors in the FPGA and adaptive SoC markets?",
        "gold_chunk_ids": ["0000002488-26-000018:item1:0011"],
        "category": "competition",
        "description": "AMD FPGA competitors (Altera, Lattice Semiconductor, Microsemi)",
    },
    {
        "id": "RET_02",
        "ticker": "AMD",
        "question": "How does AMD manage wafer sorting and assembly, test, mark and packaging (ATMP) with foundries?",
        "gold_chunk_ids": ["0000002488-26-000018:item1:0012"],
        "category": "supply_chain",
        "description": "Wafer sorting by foundry and delivery to ATMP partners",
    },
    {
        "id": "RET_03",
        "ticker": "AMD",
        "question": "What enterprise security and manageability features are offered by AMD Ryzen PRO commercial processors?",
        "gold_chunk_ids": ["0000002488-26-000018:item1:0005"],
        "category": "products",
        "description": "AMD Ryzen PRO commercial client CPU features",
    },
    {
        "id": "RET_04",
        "ticker": "AMD",
        "question": "What workstation use cases and integrations are supported by AMD Radeon PRO professional graphics?",
        "gold_chunk_ids": ["0000002488-26-000018:item1:0006"],
        "category": "products",
        "description": "AMD Radeon PRO family for desktop workstations",
    },
    {
        "id": "RET_05",
        "ticker": "AMD",
        "question": "How did AMD combine its Client and Gaming segments for financial reporting?",
        "gold_chunk_ids": ["0000002488-26-000018:item1:0003"],
        "category": "segments",
        "description": "Combination of Client and Gaming segments into one reportable segment",
    },
    {
        "id": "RET_06",
        "ticker": "AMD",
        "question": "Which corporate entities operate as subsidiaries of Advanced Micro Devices in California and internationally?",
        "gold_chunk_ids": ["0000002488-26-000018:exhibit21:0000"],
        "category": "subsidiaries",
        "description": "Exhibit 21 subsidiaries including Xilinx Development Corporation",
    },
    {
        "id": "RET_07",
        "ticker": "AMD",
        "question": "What export regulations, tariffs and trade protection risks does AMD face?",
        "gold_chunk_ids": ["0000002488-26-000018:item1a:0001"],
        "category": "risk_factors",
        "description": "Government trade restrictions, tariffs, and export controls",
    },

    # --- NVIDIA (7 questions) ---
    {
        "id": "RET_08",
        "ticker": "NVDA",
        "question": "What is NVIDIA's core business platform strategy across accelerated computing hardware, software, and systems?",
        "gold_chunk_ids": ["0001045810-26-000021:item1:0000", "0001045810-26-000021:item1:0001"],
        "category": "business_overview",
        "description": "Pioneering accelerated computing full-stack architecture",
    },
    {
        "id": "RET_09",
        "ticker": "NVDA",
        "question": "What networking architectures and interconnect technologies does NVIDIA offer for AI data centers?",
        "gold_chunk_ids": ["0001045810-26-000021:item1:0002", "0001045810-26-000021:item1:0003"],
        "category": "products",
        "description": "NVLink interconnects, switches, and InfiniBand networking platforms",
    },
    {
        "id": "RET_10",
        "ticker": "NVDA",
        "question": "In which international jurisdiction is NVIDIA's subsidiary Mellanox Technologies organized?",
        "gold_chunk_ids": ["0001045810-26-000021:exhibit21:0000"],
        "category": "subsidiaries",
        "description": "Exhibit 21 Mellanox Technologies Ltd organized in Israel",
    },
    {
        "id": "RET_11",
        "ticker": "NVDA",
        "question": "What multi-year cloud service agreements and compute commitments has NVIDIA entered into?",
        "gold_chunk_ids": ["0001045810-26-000021:item1a:0002"],
        "category": "commitments",
        "description": "Cloud service agreements to support research and operations",
    },
    {
        "id": "RET_12",
        "ticker": "NVDA",
        "question": "What risks does NVIDIA highlight regarding business disruptions and operational concentration at its corporate headquarters?",
        "gold_chunk_ids": ["0001045810-26-000021:item1a:0015"],
        "category": "risk_factors",
        "description": "Santa Clara California corporate headquarters disruption risks",
    },
    {
        "id": "RET_13",
        "ticker": "NVDA",
        "question": "How does NVIDIA engage developers and build ecosystem software libraries for GPU optimization?",
        "gold_chunk_ids": ["0001045810-26-000021:item1:0007"],
        "category": "developer_ecosystem",
        "description": "Developer platform optimization and software libraries",
    },
    {
        "id": "RET_14",
        "ticker": "NVDA",
        "question": "Which subsidiaries does NVIDIA operate in the United States and abroad according to Exhibit 21?",
        "gold_chunk_ids": ["0001045810-26-000021:exhibit21:0000"],
        "category": "subsidiaries",
        "description": "NVIDIA Exhibit 21 corporate subsidiary list",
    },

    # --- Broadcom (7 questions) ---
    {
        "id": "RET_15",
        "ticker": "AVGO",
        "question": "What are Broadcom's two primary reportable business segments?",
        "gold_chunk_ids": ["0001730168-25-000121:item1:0000"],
        "category": "business_overview",
        "description": "Semiconductor solutions and infrastructure software segments",
    },
    {
        "id": "RET_16",
        "ticker": "AVGO",
        "question": "What major infrastructure software businesses has Broadcom acquired including VMware and Symantec?",
        "gold_chunk_ids": ["0001730168-25-000121:item1:0000"],
        "category": "acquisitions",
        "description": "Broadcom's acquisition of VMware, Symantec, and CA Technologies",
    },
    {
        "id": "RET_17",
        "ticker": "AVGO",
        "question": "Which operating subsidiaries does Broadcom maintain under Exhibit 21?",
        "gold_chunk_ids": ["0001730168-25-000121:exhibit21:0000"],
        "category": "subsidiaries",
        "description": "Broadcom Exhibit 21 subsidiaries including Avago Technologies and VMware",
    },
    {
        "id": "RET_18",
        "ticker": "AVGO",
        "question": "What types of semiconductor solutions does Broadcom provide for data center networking and broadband?",
        "gold_chunk_ids": ["0001730168-25-000121:item1:0000"],
        "category": "products",
        "description": "Broadcom networking, broadband, server storage, and wireless products",
    },
    {
        "id": "RET_19",
        "ticker": "AVGO",
        "question": "What dependencies does Broadcom have on third-party foundries and outsourced manufacturing?",
        "gold_chunk_ids": ["0001730168-25-000121:item1a:0000", "0001730168-25-000121:item1a:0001"],
        "category": "supply_chain_risks",
        "description": "Outsourced foundry and assembly risk factors in Item 1A",
    },
    {
        "id": "RET_20",
        "ticker": "AVGO",
        "question": "Where is Avago Technologies International Sales Pte. Limited incorporated according to Broadcom's filing?",
        "gold_chunk_ids": ["0001730168-25-000121:exhibit21:0000"],
        "category": "subsidiaries",
        "description": "Avago Technologies International Sales Pte in Singapore",
    },
    {
        "id": "RET_21",
        "ticker": "AVGO",
        "question": "How does Broadcom manage post-acquisition integration of acquired companies like VMware?",
        "gold_chunk_ids": ["0001730168-25-000121:item1:0000", "0001730168-25-000121:item1a:0000"],
        "category": "integration_risks",
        "description": "Integration and operational execution across acquired software assets",
    },

    # --- Intel (7 questions) ---
    {
        "id": "RET_22",
        "ticker": "INTC",
        "question": "What competitive factors and product portfolio pressures does Intel face against other semiconductor manufacturers?",
        "gold_chunk_ids": ["0000050863-26-000011:item1a:0001"],
        "category": "competition",
        "description": "Intel product portfolio competition in client, server, and graphics",
    },
    {
        "id": "RET_23",
        "ticker": "INTC",
        "question": "What packaging technologies and energy efficiency metrics are critical to Intel's semiconductor competitiveness?",
        "gold_chunk_ids": ["0000050863-26-000011:item1a:0002"],
        "category": "technology",
        "description": "Competition based on packaging, energy efficiency, and performance",
    },
    {
        "id": "RET_24",
        "ticker": "INTC",
        "question": "In which jurisdiction is Intel's subsidiary Mobileye incorporated according to Exhibit 21?",
        "gold_chunk_ids": ["0000050863-26-000011:exhibit21:0000"],
        "category": "subsidiaries",
        "description": "Mobileye Global subsidiary in Delaware/Israel",
    },
    {
        "id": "RET_25",
        "ticker": "INTC",
        "question": "What material risk factors does Intel describe regarding its foundry business and internal manufacturing capabilities?",
        "gold_chunk_ids": ["0000050863-26-000011:item1a:0000"],
        "category": "risk_factors",
        "description": "Item 1A material factors affecting semiconductor operations",
    },
    {
        "id": "RET_26",
        "ticker": "INTC",
        "question": "Which international subsidiaries does Intel operate in Ireland, Israel, and Germany?",
        "gold_chunk_ids": ["0000050863-26-000011:exhibit21:0000"],
        "category": "subsidiaries",
        "description": "Exhibit 21 subsidiaries in Ireland, Israel, and international locations",
    },
    {
        "id": "RET_27",
        "ticker": "INTC",
        "question": "How does Intel structure capital investments and government incentives under the CHIPS Act?",
        "gold_chunk_ids": ["0000050863-26-000011:item1a:0000", "0000050863-26-000011:item1a:0001"],
        "category": "regulation",
        "description": "Government incentives and regulatory compliance for fab construction",
    },
    {
        "id": "RET_28",
        "ticker": "INTC",
        "question": "What subsidiaries does Intel International, Inc. control according to Exhibit 21?",
        "gold_chunk_ids": ["0000050863-26-000011:exhibit21:0000"],
        "category": "subsidiaries",
        "description": "Intel International, Inc. California and overseas subsidiaries",
    },

    # --- Micron Technology (6 questions) ---
    {
        "id": "RET_29",
        "ticker": "MU",
        "question": "What are Micron's core semiconductor memory and storage product categories?",
        "gold_chunk_ids": ["0000723125-26-000023:item1:0000"],
        "category": "products",
        "description": "Micron overview of DRAM and NAND memory and storage technologies",
    },
    {
        "id": "RET_30",
        "ticker": "MU",
        "question": "Which international subsidiaries does Micron operate in Taiwan, Singapore, and Japan?",
        "gold_chunk_ids": ["0000723125-26-000023:exhibit21:0000"],
        "category": "subsidiaries",
        "description": "Exhibit 21 subsidiaries including Micron Semiconductor Asia in Singapore and Taiwan",
    },
    {
        "id": "RET_31",
        "ticker": "MU",
        "question": "Where is Micron Technology B.V. incorporated according to Exhibit 21?",
        "gold_chunk_ids": ["0000723125-26-000023:exhibit21:0000"],
        "category": "subsidiaries",
        "description": "Micron Technology B.V. in the Netherlands",
    },
    {
        "id": "RET_32",
        "ticker": "MU",
        "question": "What markets and end-user computing sectors use Micron DRAM memory solutions?",
        "gold_chunk_ids": ["0000723125-26-000023:item1:0000"],
        "category": "markets",
        "description": "Data center, client, mobile, and automotive markets for DRAM",
    },
    {
        "id": "RET_33",
        "ticker": "MU",
        "question": "What primary risks does Micron face regarding semiconductor memory price volatility and cyclical downturns?",
        "gold_chunk_ids": ["0000723125-26-000023:item1a:0000", "0000723125-26-000023:item1a:0001"],
        "category": "risk_factors",
        "description": "Item 1A cyclical downturns and ASP volatility in memory markets",
    },
    {
        "id": "RET_34",
        "ticker": "MU",
        "question": "What operating entity conducts Micron's fab operations in Idaho?",
        "gold_chunk_ids": ["0000723125-26-000023:exhibit21:0000"],
        "category": "subsidiaries",
        "description": "Micron Idaho Semiconductor LLC in Delaware/Idaho",
    },

    # --- Microsoft (6 questions) ---
    {
        "id": "RET_35",
        "ticker": "MSFT",
        "question": "What are Microsoft's three primary operating and reportable business segments?",
        "gold_chunk_ids": ["0001193125-26-323660:item1:0000"],
        "category": "business_overview",
        "description": "Productivity and Business Processes, Intelligent Cloud, and More Personal Computing",
    },
    {
        "id": "RET_36",
        "ticker": "MSFT",
        "question": "What products and cloud services are included in Microsoft's Intelligent Cloud segment?",
        "gold_chunk_ids": ["0001193125-26-323660:item1:0000"],
        "category": "products",
        "description": "Server products and cloud services including Azure",
    },
    {
        "id": "RET_37",
        "ticker": "MSFT",
        "question": "Who does Microsoft identify as primary competitors to its Office and productivity application suite?",
        "gold_chunk_ids": ["0001193125-26-323660:item1:0003"],
        "category": "competition",
        "description": "Competitors to Office including software and global web-based application vendors",
    },
    {
        "id": "RET_38",
        "ticker": "MSFT",
        "question": "Under which jurisdiction is Microsoft subsidiary LinkedIn Corporation organized?",
        "gold_chunk_ids": ["0001193125-26-323660:exhibit21:0000"],
        "category": "subsidiaries",
        "description": "LinkedIn Corporation in Delaware under Exhibit 21",
    },
    {
        "id": "RET_39",
        "ticker": "MSFT",
        "question": "Which operating subsidiaries does Microsoft Corporation maintain in Ireland and Europe?",
        "gold_chunk_ids": ["0001193125-26-323660:exhibit21:0000"],
        "category": "subsidiaries",
        "description": "Microsoft Ireland Operations Limited and European corporate entities",
    },
    {
        "id": "RET_40",
        "ticker": "MSFT",
        "question": "What platform strategy does Microsoft pursue across AI infrastructure and enterprise cloud solutions?",
        "gold_chunk_ids": ["0001193125-26-323660:item1:0000"],
        "category": "strategy",
        "description": "Microsoft's commitment to mission, digital transformation, and cloud/AI platform",
    },
]


def write_retrieval_dataset(output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for p in RETRIEVAL_PAIRS:
            f.write(json.dumps(p) + "\n")
    print(f"Successfully generated {len(RETRIEVAL_PAIRS)} retrieval evaluation pairs in {output_path}")


if __name__ == "__main__":
    out = Path("benchmarks/questions/retrieval_eval_pairs.jsonl")
    write_retrieval_dataset(out)
