"""Generate a sample vendor contract PDF for testing extraction."""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
import os

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sample_contracts")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def make_contract(filename, vendor_name, contract_data):
    filepath = os.path.join(OUTPUT_DIR, filename)
    doc = SimpleDocTemplate(filepath, pagesize=letter,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('ContractTitle', parent=styles['Title'],
                                  fontSize=18, spaceAfter=20, alignment=TA_CENTER)
    heading_style = ParagraphStyle('ContractHeading', parent=styles['Heading2'],
                                    fontSize=13, spaceBefore=16, spaceAfter=8,
                                    textColor=colors.HexColor('#1a1a2e'))
    body_style = ParagraphStyle('ContractBody', parent=styles['Normal'],
                                 fontSize=10.5, leading=15, alignment=TA_JUSTIFY,
                                 spaceAfter=8)
    
    elements = []
    
    # Title
    elements.append(Paragraph(f"MASTER SERVICE AGREEMENT", title_style))
    elements.append(Paragraph(f"Between VendorSentry Inc. and {vendor_name}", 
                              ParagraphStyle('Sub', parent=styles['Normal'], 
                                             fontSize=11, alignment=TA_CENTER, spaceAfter=24)))
    elements.append(Spacer(1, 12))
    
    # Sections
    for section_title, section_body in contract_data:
        elements.append(Paragraph(section_title, heading_style))
        elements.append(Paragraph(section_body, body_style))
    
    doc.build(elements)
    print(f"Generated: {filepath}")
    return filepath

# ─── Contract 1: CloudVault Solutions (original-ish, matches existing data) ───
contract1_data = [
    ("1. SCOPE OF SERVICES",
     "CloudVault Solutions ('Vendor') shall provide cloud infrastructure management, "
     "data backup, and disaster recovery services. The Vendor will have access to "
     "the Client's AWS S3 buckets, Kubernetes clusters, and CloudWatch monitoring logs."),
    
    ("2. DATA ACCESS AND HANDLING",
     "The Vendor acknowledges that it will process Personally Identifiable Information (PII) "
     "as part of its service delivery. The Vendor shall NOT process or store any financial "
     "data, including payment card data, banking details, or transaction records. "
     "All PII processing must comply with GDPR and CCPA regulations."),
    
    ("3. SECURITY AND COMPLIANCE",
     "The Vendor maintains SOC 2 Type II certification (current, annual renewal). "
     "The Vendor is currently undergoing an ISO 27001 audit but is not yet certified. "
     "The Vendor shall maintain an information security management system and provide "
     "evidence of annual penetration testing."),
    
    ("4. SERVICE LEVEL AGREEMENT",
     "The Vendor guarantees 99.99% uptime for all production services. In the event of "
     "a data breach, the Vendor shall notify the Client within 24 hours of discovery. "
     "Response time for critical incidents: 15 minutes. Resolution time for P1 issues: 4 hours."),
    
    ("5. TERM AND TERMINATION",
     "This agreement is effective for 24 months from the execution date. Either party may "
     "terminate with 90 days written notice. The Vendor must securely delete all client data "
     "within 30 days of termination."),
]

# ─── Contract 2: CloudVault Solutions (DIFFERENT — worse security posture) ───
contract2_data = [
    ("1. SCOPE OF SERVICES — AMENDED",
     "CloudVault Solutions ('Vendor') shall provide expanded cloud infrastructure management, "
     "including production database administration, CI/CD pipeline access, and root-level "
     "access to all Kubernetes namespaces. The Vendor will additionally have access to "
     "the Client's AWS RDS instances, IAM management console, and Secrets Manager."),
    
    ("2. DATA ACCESS AND HANDLING — AMENDED",
     "The Vendor acknowledges that it will process Personally Identifiable Information (PII) "
     "AND financial data including payment processing records and billing system access "
     "as part of the expanded service scope. The Vendor shall also have access to "
     "employee HR records and salary information stored in the Client's HRIS platform. "
     "All data processing must comply with GDPR, CCPA, and PCI-DSS regulations."),
    
    ("3. SECURITY AND COMPLIANCE — AMENDED",
     "The Vendor's SOC 2 Type II certification has EXPIRED as of March 2026 and is "
     "currently pending renewal. The ISO 27001 certification audit has been POSTPONED "
     "indefinitely due to resource constraints. The Vendor does not currently hold any "
     "active security certifications. The Vendor commits to obtaining recertification "
     "within 6 months of this amendment."),
    
    ("4. SERVICE LEVEL AGREEMENT — AMENDED",
     "The Vendor guarantees 99.5% uptime (reduced from 99.99%) for all production services "
     "during the transition period. In the event of a data breach, the Vendor shall notify "
     "the Client within 72 hours of discovery (extended from 24 hours). "
     "Response time for critical incidents: 1 hour. Resolution time for P1 issues: 12 hours."),
    
    ("5. FINANCIAL TERMS — NEW",
     "The annual contract value is increased to $2,400,000 reflecting expanded scope. "
     "The Vendor's recent quarterly financial report indicates a 15% revenue decline and "
     "ongoing restructuring. The Vendor has disclosed a pending regulatory investigation "
     "by the FTC regarding data handling practices. Payment terms: Net 60."),
    
    ("6. INCIDENT HISTORY DISCLOSURE",
     "The Vendor discloses that it experienced a security incident in January 2026 affecting "
     "approximately 50,000 records. The incident involved unauthorized access to a staging "
     "database containing customer PII. A full post-incident review has been completed and "
     "remediation measures implemented."),
]

make_contract("sample_contract.pdf", "CloudVault Solutions", contract1_data)
make_contract("sample_contract1.pdf", "CloudVault Solutions", contract2_data)
print("\nDone! Both contracts generated in:", OUTPUT_DIR)
