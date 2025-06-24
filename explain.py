"""
GPT-4.1 integration for explaining chess mistakes and providing learning insights.
"""

from openai import OpenAI
from typing import Dict, Any, Optional, List
from utils import get_openai_api_key
import os
from datetime import datetime
import re

class ChessExplainer:
    """Handles GPT-4.1 explanations for chess mistakes."""
    
    def __init__(self):
        """Initialize the explainer with OpenAI API key and gpt-4.1 model."""
        try:
            api_key = get_openai_api_key()
            self.client = OpenAI(api_key=api_key)
            self.model = "gpt-4.1"
            self.total_tokens = 0
            self.total_cost = 0.0
            # Set up per-run log file
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_path = os.path.join(log_dir, f"gpt_api_{timestamp}.log")
        except ValueError as e:
            print(f"Error initializing OpenAI: {e}")
            raise
    
    def _log(self, message: str):
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(message + "\n")
    
    def estimate_cost(self, num_errors: int) -> float:
        """
        Estimate the cost for explaining a given number of errors using gpt-4.1 pricing.
        
        Args:
            num_errors: Number of errors to explain
            
        Returns:
            Estimated cost in USD
        """
        # Rough estimate: 150 tokens per error explanation
        estimated_tokens = num_errors * 150
        # gpt-4.1: $2.00 per 1M input tokens, $8.00 per 1M output tokens
        input_cost = (estimated_tokens * 0.5) * 2.00 / 1_000_000
        output_cost = (estimated_tokens * 0.5) * 8.00 / 1_000_000
        return input_cost + output_cost
    
    def explain_errors_batch(self, errors: List[Dict[str, Any]], max_errors: int = 15) -> List[Dict[str, Any]]:
        """
        Explain multiple errors in a single API call to reduce costs.
        
        Args:
            errors: List of error dictionaries
            max_errors: Maximum number of errors to explain
            
        Returns:
            List of errors with explanations added
        """
        if not errors:
            return []
        
        # Limit the number of errors to explain
        errors_to_explain = errors[:max_errors]
        
        # Log the batch prompt
        batch_prompt = self._create_batch_prompt(errors_to_explain)
        print("\n--- GPT-4.1 BATCH PROMPT ---\n")
        print(batch_prompt)
        print("\n--- END BATCH PROMPT ---\n")
        self._log("\n--- GPT-4.1 BATCH PROMPT ---\n" + batch_prompt + "\n--- END BATCH PROMPT ---\n")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a chess coach. Provide brief, educational explanations for chess mistakes. Format each explanation as 'ERROR_X: [explanation]' where X is the error number (1, 2, 3, etc.)."
                    },
                    {
                        "role": "user",
                        "content": batch_prompt
                    }
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            explanation_text = response.choices[0].message.content.strip()
            print("\n--- RAW GPT-4.1 BATCH RESPONSE ---\n")
            print(explanation_text)
            print("\n--- END RAW RESPONSE ---\n")
            self._log("\n--- RAW GPT-4.1 BATCH RESPONSE ---\n" + explanation_text + "\n--- END RAW RESPONSE ---\n")
            
            # Parse the batch response
            explanations = self._parse_batch_explanations(explanation_text, len(errors_to_explain))
            print("\n--- PARSED EXPLANATIONS DICT ---\n")
            print(explanations)
            print("\n--- END PARSED EXPLANATIONS ---\n")
            self._log("\n--- PARSED EXPLANATIONS DICT ---\n" + str(explanations) + "\n--- END PARSED EXPLANATIONS ---\n")
            
            # Add explanations to errors
            for i, error in enumerate(errors_to_explain):
                error['explanation'] = explanations.get(i+1, "No explanation available.")
            
            # Update token usage
            self.total_tokens += response.usage.total_tokens
            self.total_cost += (response.usage.prompt_tokens * 2.00 / 1_000_000) + (response.usage.completion_tokens * 8.00 / 1_000_000)
            
            print(f"✅ Explained {len(errors_to_explain)} errors. Total cost so far: ${self.total_cost:.3f}")
            
            return errors_to_explain
            
        except Exception as e:
            print(f"Error generating batch explanations: {e}")
            return errors
    
    def _create_batch_prompt(self, errors: List[Dict[str, Any]]) -> str:
        """Create a batch prompt for multiple errors."""
        prompt = "Explain these chess mistakes briefly:\n\n"
        
        for i, error in enumerate(errors, 1):
            prompt += f"ERROR_{i}:\n"
            prompt += f"Move: {error['san_move']}\n"
            prompt += f"Type: {error['error_type']}\n"
            prompt += f"Eval change: {error['eval_change']:.2f} pawns\n"
            prompt += f"Position: {error['fen_before']}\n\n"
        
        prompt += "Provide brief explanations (1-2 sentences each) focusing on why the move was problematic and what would be better."
        return prompt
    
    def _parse_batch_explanations(self, response: str, num_errors: int) -> Dict[int, str]:
        """Parse batch response into individual explanations."""
        explanations = {}
        current_error = None
        current_explanation = []
        lines = response.split('\n')
        for line in lines:
            match = re.match(r"ERROR_(\d+):\s*(.*)", line)
            if match:
                # Save previous explanation
                if current_error is not None and current_explanation:
                    explanations[current_error] = ' '.join(current_explanation).strip()
                # Start new error
                current_error = int(match.group(1))
                explanation_text = match.group(2).strip()
                current_explanation = [explanation_text] if explanation_text else []
            elif current_error is not None:
                # Continuation of previous explanation
                if line.strip():
                    current_explanation.append(line.strip())
        # Save last explanation
        if current_error is not None and current_explanation:
            explanations[current_error] = ' '.join(current_explanation).strip()
        return explanations

    def explain_error(self, san_move: str, fen_before: str, eval_change: float, error_type: str) -> Optional[str]:
        """
        Generate explanation for a chess error using GPT-4.1.
        
        Args:
            san_move: The move in SAN notation
            fen_before: FEN string of the position before the move
            eval_change: Evaluation change in pawns
            error_type: Type of error ('Blunder', 'Mistake', 'Inaccuracy')
            
        Returns:
            Explanation string or None if error
        """
        try:
            # Log the prompt
            prompt = self._create_error_prompt(san_move, fen_before, eval_change, error_type)
            print("\n--- GPT-4.1 SINGLE PROMPT ---\n")
            print(prompt)
            print("\n--- END SINGLE PROMPT ---\n")
            self._log("\n--- GPT-4.1 SINGLE PROMPT ---\n" + prompt + "\n--- END SINGLE PROMPT ---\n")
            
            # Call GPT-4.1
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a chess coach. Provide brief, educational explanations of chess mistakes."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            explanation = response.choices[0].message.content.strip()
            print("\n--- RAW GPT-4.1 SINGLE RESPONSE ---\n")
            print(explanation)
            print("\n--- END SINGLE RESPONSE ---\n")
            self._log("\n--- RAW GPT-4.1 SINGLE RESPONSE ---\n" + explanation + "\n--- END SINGLE RESPONSE ---\n")
            
            # Update token usage
            self.total_tokens += response.usage.total_tokens
            self.total_cost += (response.usage.prompt_tokens * 2.00 / 1_000_000) + (response.usage.completion_tokens * 8.00 / 1_000_000)
            
            return explanation
            
        except Exception as e:
            print(f"Error generating explanation: {e}")
            return f"Unable to generate explanation for this {error_type.lower()}."
    
    def _create_error_prompt(self, san_move: str, fen_before: str, eval_change: float, error_type: str) -> str:
        """
        Create a concise prompt for GPT-4.1 to explain an error.
        
        Args:
            san_move: The move in SAN notation
            fen_before: FEN string of the position before the move
            eval_change: Evaluation change in pawns
            error_type: Type of error
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""Briefly explain this chess {error_type.lower()}:

Move: {san_move}
Eval change: {eval_change:.2f} pawns
Position: {fen_before}

Explain why this move was problematic and what would be better (1-2 sentences)."""
        return prompt

    def explain_blunder(self, blunder_data: Dict[str, Any], player_color: str) -> Optional[Dict[str, str]]:
        """
        Generate explanation for a chess blunder using GPT-4.1.
        
        Args:
            blunder_data: Dictionary containing blunder information
            player_color: Color of the player ('white' or 'black')
            
        Returns:
            Dictionary with explanation components or None if error
        """
        try:
            # Construct the prompt
            prompt = self._create_blunder_prompt(blunder_data, player_color)
            
            # Call GPT-4.1
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a chess coach. Provide clear, educational explanations of chess mistakes that help players learn and improve."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            explanation = response.choices[0].message.content.strip()
            
            # Parse the explanation into sections
            return self._parse_explanation(explanation)
            
        except Exception as e:
            print(f"Error generating explanation: {e}")
            return None
    
    def _create_blunder_prompt(self, blunder_data: Dict[str, Any], player_color: str) -> str:
        """
        Create a detailed prompt for GPT-4.1 to explain a blunder.
        
        Args:
            blunder_data: Blunder information
            player_color: Player's color
            
        Returns:
            Formatted prompt string
        """
        move_number = blunder_data['move_number']
        move = blunder_data['san_move']
        fen_before = blunder_data['fen_before']
        eval_before = blunder_data['eval_before']
        eval_after = blunder_data['eval_after']
        eval_change = blunder_data['eval_change']
        
        prompt = f"""
Analyze this chess blunder and provide a comprehensive explanation:

**Position**: {fen_before}
**Move**: {move_number}. {move} ({player_color} to move)
**Evaluation before**: {eval_before:.2f}
**Evaluation after**: {eval_after:.2f}
**Evaluation change**: {eval_change:.2f}

Please provide a structured explanation with the following sections:

1. **Why this move was a blunder**: Explain what went wrong tactically or strategically
2. **What the correct plan should have been**: Suggest the best move or plan
3. **General lesson learned**: What chess principle or pattern should the player remember

Keep explanations clear and educational, suitable for intermediate players.
"""
        return prompt
    
    def _parse_explanation(self, explanation: str) -> Dict[str, str]:
        """
        Parse GPT-4.1 response into structured sections.
        
        Args:
            explanation: Raw explanation from GPT-4.1
            
        Returns:
            Dictionary with parsed sections
        """
        # Simple parsing - look for common section headers
        sections = {
            'why_blunder': '',
            'correct_plan': '',
            'lesson_learned': ''
        }
        
        lines = explanation.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detect section headers
            if 'blunder' in line.lower() or 'wrong' in line.lower():
                current_section = 'why_blunder'
            elif 'correct' in line.lower() or 'best' in line.lower() or 'should' in line.lower():
                current_section = 'correct_plan'
            elif 'lesson' in line.lower() or 'principle' in line.lower() or 'remember' in line.lower():
                current_section = 'lesson_learned'
            elif current_section and line:
                sections[current_section] += line + ' '
        
        # Clean up sections
        for key in sections:
            sections[key] = sections[key].strip()
            if not sections[key]:
                sections[key] = "No specific explanation provided for this section."
        
        return sections
    
    def get_improvement_suggestions(self, game_summary: Dict[str, Any]) -> Optional[str]:
        """
        Generate overall improvement suggestions based on game analysis.
        
        Args:
            game_summary: Summary of the game analysis
            
        Returns:
            Improvement suggestions or None if error
        """
        try:
            num_blunders = len(game_summary.get('blunders', []))
            result = game_summary.get('result', 'Unknown')
            
            prompt = f"""
Based on this chess game analysis, provide 2-3 specific improvement suggestions:

**Game Result**: {result}
**Number of Blunders**: {num_blunders}

Focus on practical, actionable advice that the player can work on in their training.
Keep suggestions concise and specific.
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a chess coach providing practical improvement advice."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error generating improvement suggestions: {e}")
            return None 