#!/usr/bin/env python3
"""
Personality Trait Extraction Script
Extracts 10-20 personality traits from CV and LinkedIn data
"""
import json
import csv
from pathlib import Path
from typing import List, Dict, Any
import os

try:
    from openai import OpenAI
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Install: pip install openai python-dotenv")
    raise


class PersonalityExtractor:
    """Extract personality traits from CV and LinkedIn data"""
    
    def __init__(self, api_key: str = None):
        api_key = api_key or os.environ.get('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key required")
        self.client = OpenAI(api_key=api_key)
    
    def load_cv_data(self, cv_path: str) -> str:
        """Load CV text"""
        cv_file = Path(cv_path)
        if cv_file.exists():
            with open(cv_file, 'r', encoding='utf-8') as f:
                return f.read()
        return ""
    
    def load_linkedin_data(self, csv_path: str) -> str:
        """Load LinkedIn data from CSV"""
        csv_file = Path(csv_path)
        if not csv_file.exists():
            return ""
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row = next(reader, None)
            if not row:
                return ""
            
            # Extract relevant fields
            linkedin_text = f"""
LinkedIn Profile: {row.get('linkedinHeadline', '')}
Bio: {row.get('linkedinDescription', '')}
Skills: {row.get('linkedinSkillsLabel', '')}
Current Role: {row.get('linkedinJobTitle', '')} at {row.get('companyName', '')}
Job Description: {row.get('linkedinJobDescription', '')}
Previous Role: {row.get('linkedinPreviousJobTitle', '')} at {row.get('previousCompanyName', '')}
Previous Job Description: {row.get('linkedinPreviousJobDescription', '')}
Education: {row.get('linkedinSchoolName', '')} - {row.get('linkedinSchoolDegree', '')}
Education Description: {row.get('linkedinSchoolDescription', '')}
"""
            return linkedin_text
    
    def extract_traits(
        self,
        cv_text: str,
        linkedin_text: str,
        num_traits: int = 15
    ) -> List[Dict[str, str]]:
        """
        Extract personality traits using LLM
        
        Returns list of dicts with 'trait' and 'description' keys
        """
        combined_text = f"""
CV/RESUME DATA:
{cv_text}

LINKEDIN DATA:
{linkedin_text}
"""
        
        prompt = f"""Based on the following CV and LinkedIn profile data, extract {num_traits} key personality traits, communication styles, and behavioral patterns that would manifest in workplace interactions.

Focus on:
- Communication style (formal/informal, technical depth, brevity)
- Work approach (detail-oriented, strategic, hands-on)
- Leadership style (collaborative, decisive, mentoring)
- Problem-solving approach (analytical, creative, systematic)
- Emotional traits (confidence level, enthusiasm, calm under pressure)
- Social dynamics (team player, independent, relationship-building)
- Professional values and priorities
- Response patterns (quick vs thoughtful, detail-oriented vs high-level)

For each trait, provide:
1. Trait name (e.g., "Technical Depth and Precision")
2. Brief description of how it manifests in workplace communication
3. Example of how Ryan would express this in a workplace message

Format as JSON array:
[
  {{
    "trait": "Trait Name",
    "description": "How this manifests",
    "workplace_example": "Example message demonstrating this trait"
  }}
]

Return ONLY the JSON array, no other text."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing personality traits from professional profiles. Extract actionable, specific traits that would affect workplace communication."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Extract JSON
            import re
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                traits = json.loads(json_match.group())
                return traits[:num_traits]  # Limit to requested number
            
            return []
            
        except Exception as e:
            print(f"Error extracting traits: {e}")
            return []
    
    def format_traits_for_context(self, traits: List[Dict[str, str]]) -> str:
        """Format traits as context string for synthetic generation"""
        formatted = "PERSONALITY TRAITS AND COMMUNICATION STYLE:\n\n"
        
        for i, trait in enumerate(traits, 1):
            formatted += f"{i}. {trait['trait']}\n"
            formatted += f"   {trait['description']}\n"
            if 'workplace_example' in trait:
                formatted += f"   Example: {trait['workplace_example']}\n"
            formatted += "\n"
        
        return formatted


def main():
    """Extract personality traits"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract personality traits')
    parser.add_argument('--cv-path', type=str, default='cvryanlin.txt')
    parser.add_argument('--linkedin-csv', type=str, default='result.csv')
    parser.add_argument('--num-traits', type=int, default=15)
    parser.add_argument('--output', type=str, default='personality_traits.json')
    
    args = parser.parse_args()
    
    extractor = PersonalityExtractor()
    
    print("📖 Loading data...")
    cv_text = extractor.load_cv_data(args.cv_path)
    linkedin_text = extractor.load_linkedin_data(args.linkedin_csv)
    
    if not cv_text and not linkedin_text:
        print("❌ No data loaded. Check file paths.")
        return
    
    print(f"✅ Loaded CV ({len(cv_text)} chars) and LinkedIn data ({len(linkedin_text)} chars)")
    print(f"🔍 Extracting {args.num_traits} personality traits...")
    
    traits = extractor.extract_traits(cv_text, linkedin_text, args.num_traits)
    
    if traits:
        # Save traits
        output_file = Path(args.output)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(traits, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Extracted {len(traits)} traits")
        print(f"💾 Saved to {output_file}")
        
        # Print summary
        print("\n📋 Traits extracted:")
        for i, trait in enumerate(traits, 1):
            print(f"   {i}. {trait['trait']}")
    else:
        print("❌ Failed to extract traits")


if __name__ == '__main__':
    main()

