from pathlib import Path

BASE_DIR=Path(__file__).resolve().parent
DATA_DIR=BASE_DIR/"data"
NOTES_FILE=DATA_DIR/"notes_long.txt"

BIO_OUTPUT_DIR=BASE_DIR/"outputs"
BIO_TRACE_FILE=BIO_OUTPUT_DIR/"trace.jsonl"

TOPIC_ALIASES={
    "细胞": "Cell",
    "细胞生物学": "Cell Biology",
    "dna": "DNA",
    "脱氧核糖核酸": "DNA",
    "dna sequencing": "DNA Sequencing",
    "dna 测序": "DNA Sequencing",
    "dna测序": "DNA Sequencing",
    "基因测序": "DNA Sequencing",
    "rna": "RNA",
    "核糖核酸": "RNA",
    "rna-seq": "RNA-seq",
    "转录组测序": "RNA-seq",
    "single cell rna-seq": "Single Cell RNA-seq",
    "single-cell rna-seq": "Single Cell RNA-seq",
    "单细胞 rna 测序": "Single Cell RNA-seq",
    "单细胞rna测序": "Single Cell RNA-seq",
    "scrna-seq": "Single Cell RNA-seq",
    "基因表达": "Gene Expression",
    "qpcr": "qPCR",
    "定量 pcr": "qPCR",
    "定量pcr": "qPCR",
    "实时荧光定量 pcr": "qPCR",
    "实时荧光定量pcr": "qPCR",
    "pcr": "PCR",
    "聚合酶链式反应": "PCR",
    "聚合酶链反应": "PCR",
    "crispr": "CRISPR",
    "基因编辑": "CRISPR",
    "蛋白质": "Proteins",
    "免疫": "Immunology",
    "免疫学": "Immunology",
    "肿瘤": "Cancer Biology",
    "癌症": "Cancer Biology",
    "生物信息学": "Bioinformatics",
    "药理学": "Pharmacology",
    "临床研究": "Clinical Research",

}
