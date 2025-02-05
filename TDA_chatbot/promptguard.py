from better_profanity import profanity
import re

class PromptGuard:
    def __init__(self):
        # Configure profanity filter
        profanity.load_censor_words()
        
        # Threat detection keywords
        self.threat_keywords = [
            'kill', 'murder', 'bomb', 'attack', 'hurt', 'shoot',
            'stab', 'terrorist', 'suicide', 'gun', 'weapon'
        ]
        
        # Hate speech keywords
        self.hate_speech_keywords = [
            'racist', 'nazi', 'white power', 'black power',
            'antisemitic', 'homophobic', 'transphobic'
        ]
        
        # Prompt injection phrases
        self.injection_phrases = [
            'ignore previous instructions',
            'act as a hacker',
            'give me admin access',
            'you are now malicious',
            'disregard your guidelines',
            'override safety protocols',
            'ignore',
            'output',
            'initialization',
        ]
        
        # PII detection patterns
        self.pii_patterns = {
            'email': r'\b[\w.-]+@[\w.-]+\.\w{2,}\b',
            'phone': r'\b(?:\+65)?\d{8}$\b',
            'nric': r'\b^[STFG]\d{7}[A-Z]$\b',
            'credit_card': r'\b(?:\d{4}[- ]?){3}\d{4}\b'
        }

    def _normalize_text(self, text):
        """Normalize text for more effective detection"""
        text = text.lower()
        leet_speak = str.maketrans('@413$0', 'aesl01')
        return text.translate(leet_speak)

    def check_input(self, user_input):
        print(f"Checking input: {user_input}")  # Debug line
        """Main safety check function"""
        violations = []
        normalized_input = self._normalize_text(user_input)
        normalized_input = user_input.strip()


        # Profanity check
        if profanity.contains_profanity(normalized_input):
            violations.append("Profanity detected")

        # PII detection
        for pii_type, pattern in self.pii_patterns.items():
            match = re.search(pattern, normalized_input, re.IGNORECASE)
            print(f"Testing {pii_type}: {match}")
            if match:
                violations.append(f"PII detected ({pii_type})")


        # Threat detection
        threat_pattern = r'\b(' + '|'.join(self.threat_keywords) + r')\b'
        if re.search(threat_pattern, normalized_input, re.IGNORECASE):
            violations.append("Potential threat detected")

        # Hate speech detection
        hate_pattern = r'\b(' + '|'.join(self.hate_speech_keywords) + r')\b'
        if re.search(hate_pattern, normalized_input, re.IGNORECASE):
            violations.append("Hate speech detected")

        # Prompt injection detection
        injection_pattern = r'\b(' + '|'.join(self.injection_phrases) + r')\b'
        if re.search(injection_pattern, normalized_input, re.IGNORECASE):
            violations.append("Prompt injection attempt detected")

        return (len(violations) == 0, violations)

