from fpdf import FPDF
import os

def create_receipt_pdf(input_file, output_file):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Courier", size=10)
    
    # Read the text file
    with open(input_file, 'r') as file:
        content = file.readlines()
    
    # Set line height
    line_height = 5
    
    # Add content to PDF
    for line in content:
        pdf.cell(0, line_height, txt=line.strip(), ln=1)
    
    # Save the PDF
    pdf.output(output_file)
    
    return output_file

def create_statement_pdf(input_file, output_file):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Courier", size=10)
    
    # Read the text file
    with open(input_file, 'r') as file:
        content = file.readlines()
    
    # Set line height
    line_height = 5
    
    # Add content to PDF
    for line in content:
        pdf.cell(0, line_height, txt=line.strip(), ln=1)
    
    # Save the PDF
    pdf.output(output_file)
    
    return output_file

if __name__ == "__main__":
    # Generate receipt PDF
    receipt_output = create_receipt_pdf("sample_receipt.txt", "sample_receipt.pdf")
    print(f"Created: {receipt_output}")
    
    # Generate bank statement PDF
    statement_output = create_statement_pdf("sample_bank_statement.txt", "sample_bank_statement.pdf")
    print(f"Created: {statement_output}")
    
    # Print file sizes
    receipt_size = os.path.getsize(receipt_output)
    statement_size = os.path.getsize(statement_output)
    print(f"Receipt PDF size: {receipt_size} bytes")
    print(f"Statement PDF size: {statement_size} bytes")