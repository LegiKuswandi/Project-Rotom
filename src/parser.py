import re

class BusinessCardParser:
    def parse(self, raw_text: str) -> dict:
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
        
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}'
        
        email = None
        phone = None
        name = None
        company = None
        
        for line in lines:
            if not email and re.search(email_pattern, line):
                match = re.search(email_pattern, line)
                if match:
                    email = match.group(0)
            if not phone and re.search(phone_pattern, line):
                digits = re.sub(r'\D', '', line)
                if len(digits) >= 8:
                    phone = line.strip()

        non_contact_lines = [
            l for l in lines 
            if not re.search(email_pattern, l) 
            and not re.search(phone_pattern, l)
            and not any(keyword in l.lower() for keyword in ['web', 'www', 'http', 'fax', 'phone', 'email'])
        ]
        
        if len(non_contact_lines) > 0:
            name = non_contact_lines[0]
        if len(non_contact_lines) > 1:
            company = non_contact_lines[1]
            
        return {
            "name": name if name else "N/A",
            "company": company if company else "N/A",
            "email": email if email else "N/A",
            "phone": phone if phone else "N/A"
        }