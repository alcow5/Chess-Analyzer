#!/usr/bin/env python3
"""
Basic test script for Chess Insight Analyzer.
Tests core functionality without requiring external APIs.
"""

import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from utils import format_evaluation, format_move_number
        print("✓ utils module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import utils: {e}")
        return False
    
    try:
        from fetch import ChessComAPI
        print("✓ fetch module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import fetch: {e}")
        return False
    
    try:
        from analyze import ChessAnalyzer
        print("✓ analyze module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import analyze: {e}")
        return False
    
    try:
        from report import ReportGenerator
        print("✓ report module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import report: {e}")
        return False
    
    return True

def test_utils():
    """Test utility functions."""
    print("\nTesting utility functions...")
    
    from utils import format_evaluation, format_move_number
    
    # Test format_evaluation
    assert format_evaluation(1.5) == "+1.50"
    assert format_evaluation(-1.5) == "-1.50"
    assert format_evaluation(0.0) == "0.00"
    print("✓ format_evaluation works correctly")
    
    # Test format_move_number
    assert format_move_number(1) == "1."
    assert format_move_number(15) == "15."
    print("✓ format_move_number works correctly")

def test_report_generation():
    """Test report generation with mock data."""
    print("\nTesting report generation...")
    
    from report import ReportGenerator
    
    # Create mock data
    mock_game_data = {
        'white': {'username': 'testuser', 'rating': 1500},
        'black': {'username': 'opponent', 'rating': 1550},
        'result': '1-0',
        'end_time': 1640995200  # 2022-01-01
    }
    
    mock_blunders = [
        {
            'move_number': 15,
            'move': 'e4e5',
            'fen_before': 'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1',
            'eval_before': 0.5,
            'eval_after': -1.0,
            'eval_change': -1.5,
            'san_move': 'e4e5'
        }
    ]
    
    mock_explanations = [
        {
            'why_blunder': 'This move allows a tactical combination.',
            'correct_plan': 'Should have played Nf3 to develop and control the center.',
            'lesson_learned': 'Always consider tactical threats before making moves.'
        }
    ]
    
    # Generate report
    report_gen = ReportGenerator()
    report = report_gen.generate_game_report('testuser', mock_game_data, mock_blunders, mock_explanations)
    
    # Check that report contains expected content
    assert 'testuser' in report
    assert 'Blunder #1' in report
    assert 'tactical combination' in report
    print("✓ Report generation works correctly")

def test_analyzer_initialization():
    """Test analyzer initialization (without Stockfish)."""
    print("\nTesting analyzer initialization...")
    
    from analyze import ChessAnalyzer
    
    analyzer = ChessAnalyzer()
    print("✓ ChessAnalyzer initialized successfully")
    
    # Test that it can handle missing Stockfish gracefully
    if not analyzer.initialize_engine():
        print("⚠ Stockfish not available (expected if not installed)")
    else:
        print("✓ Stockfish engine initialized successfully")
        analyzer.close_engine()

def main():
    """Run all tests."""
    print("Chess Insight Analyzer - Basic Tests")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_utils,
        test_report_generation,
        test_analyzer_initialization
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
    
    print(f"\n{'='*40}")
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! The basic functionality is working.")
        print("\nTo run the full analyzer:")
        print("1. Install Stockfish and add to PATH")
        print("2. Set up your OpenAI API key in .env file")
        print("3. Run: python main.py")
    else:
        print("⚠ Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main() 