import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.api.server import app

pdf_path = Path("Supplier Code of Conduct - Google - About Google.pdf")
assert pdf_path.exists(), "PDF not found in root directory!"

with TestClient(app) as client:
    with open(pdf_path, "rb") as f:
        client.post("/api/upload", files={"file": (pdf_path.name, f, "application/pdf")})

    # Diverse compliance questions covering Labor, Safety, Ethics, and Out-of-Domain
    questions = [
        # 1. Working Hours & Rest
        "What is the maximum workweek limit in hours including overtime for workers?",
        # 2. Forced Labor & Identity Documents
        "Can suppliers retain government-issued identification, passports, or work permits of employees?",
        # 3. Child Labor & Minimum Age
        "What is the minimum age policy for workers and how is child labor defined?",
        # 4. Disciplinary Deductions from Wages
        "Are wage deductions permitted as a disciplinary measure against workers?",
        # 5. Health & Safety / Emergency Preparedness
        "What emergency preparedness and fire safety procedures must suppliers implement?",
        # 6. Anti-Corruption & Bribery (Ethics)
        "What is the zero-tolerance policy regarding bribery, corruption, and extortion?",
        # 7. Whistleblower Protection & Non-Retaliation
        "How are workers protected from retaliation when reporting compliance violations?",
        # 8. Out-of-Domain / Negative Test (Should trigger safe rejection)
        "What are the corporate travel expense reimbursement rules for flight upgrades?"
    ]

    print("================================================================================")
    print("      AXIOMRAG ENTERPRISE AUDIT STRESS TEST (GOOGLE SUPPLIER CODE OF CONDUCT)   ")
    print("================================================================================\n")

    for i, q in enumerate(questions, 1):
        res = client.post("/api/audit", json={"query": q}).json()
        conf = res["confidence_score"]
        status = "PASSED (VERIFIED)" if res["is_sufficient"] else "REJECTED (INSUFFICIENT)"
        
        print(f"[{i}/8] QUERY: {q}")
        print(f"      STATUS     : {status} | CONFIDENCE: {conf:.4f} ({conf*100:.1f}%) | LATENCY: {res['latency_ms']}ms")
        print(f"      EXCERPT    :\n{res['final_answer'][:280]}...")
        print("-" * 80 + "\n")
