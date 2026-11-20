"""Sample DSA syllabus data fixture for automated tests and development fixtures.

NOTE: This fixture is strictly for testing and local validation. It is never automatically
inserted into real student courses.
"""
from __future__ import annotations

import json

SAMPLE_DSA_SYLLABUS_TEXT = """
CS201: Data Structures and Algorithms (Fall 2026)
Instructor: Dr. Alan Turing
Department of Computer Science

[Page 1]
Course Description:
Comprehensive introduction to fundamental data structures, algorithmic design patterns,
algorithmic complexity, and graph algorithms.

Unit 1: Linear Data Structures
- Arrays: Fixed and dynamic arrays, indexing, array traversal, amortized constant time growth.
- Strings: String manipulation, substring search, two-pointer techniques.

[Page 2]
Unit 2: Recursion and Divide & Conquer
- Recursion: Base cases, call stack mechanics, recursive problem formulation.
- Backtracking: State-space tree exploration, constraint satisfaction, N-Queens problem.

[Page 3]
Unit 3: Dynamic Programming
- Dynamic Programming: Optimal substructure, overlapping subproblems.
- Memoization: Top-down cached recursion.
- Tabulation: Bottom-up iterative table construction.
- Grid DP: 2D matrix traversal, minimum path sum.

[Page 4]
Unit 4: Non-Linear Data Structures & Graphs
- Trees: Binary search trees, tree traversals (inorder, preorder, postorder).
- Graphs: Graph representations, BFS, DFS, shortest paths.
"""

SAMPLE_DSA_EXTRACTION_DICT = {
    "units": [
        {
            "unit_name": "Unit 1",
            "unit_title": "Linear Data Structures",
            "topics": [
                {
                    "name": "Arrays",
                    "description": "Contiguous memory structures, dynamic resizing, and pointer arithmetic.",
                    "difficulty": "easy",
                    "source_type": "explicit",
                    "source_pages": [1],
                    "subtopics": [
                        {
                            "name": "Array Traversal",
                            "description": "Sequential element iteration and bounds checking",
                        },
                        {
                            "name": "Dynamic Arrays",
                            "description": "Geometric resizing and amortized complexity",
                        },
                    ],
                },
                {
                    "name": "Strings",
                    "description": "Character sequences, pattern searching, and string immutability.",
                    "difficulty": "easy",
                    "source_type": "explicit",
                    "source_pages": [1],
                    "subtopics": [
                        {
                            "name": "Two-Pointer Techniques",
                            "description": "Opposite-end and sliding window traversal",
                        }
                    ],
                },
            ],
        },
        {
            "unit_name": "Unit 2",
            "unit_title": "Recursion and Divide & Conquer",
            "topics": [
                {
                    "name": "Recursion",
                    "description": "Functions that call themselves with defined termination base cases.",
                    "difficulty": "medium",
                    "source_type": "explicit",
                    "source_pages": [2],
                    "subtopics": [
                        {
                            "name": "Call Stack Mechanics",
                            "description": "Activation records and stack overflow mitigation",
                        }
                    ],
                },
                {
                    "name": "Backtracking",
                    "description": "Systematic search of solution spaces with candidate pruning.",
                    "difficulty": "medium",
                    "source_type": "explicit",
                    "source_pages": [2],
                    "subtopics": [
                        {
                            "name": "State-Space Trees",
                            "description": "Exploring branches and undoing invalid decisions",
                        }
                    ],
                },
            ],
        },
        {
            "unit_name": "Unit 3",
            "unit_title": "Dynamic Programming",
            "topics": [
                {
                    "name": "Dynamic Programming",
                    "description": "Optimization algorithm solving overlapping subproblems using stored sub-results.",
                    "difficulty": "hard",
                    "source_type": "explicit",
                    "source_pages": [3],
                    "subtopics": [
                        {
                            "name": "Memoization",
                            "description": "Top-down recursive caching of intermediate subproblem solutions",
                        },
                        {
                            "name": "Tabulation",
                            "description": "Bottom-up iterative state table population",
                        },
                        {
                            "name": "Grid DP",
                            "description": "Multi-dimensional state transitions on 2D coordinates",
                        },
                    ],
                }
            ],
        },
        {
            "unit_name": "Unit 4",
            "unit_title": "Non-Linear Data Structures & Graphs",
            "topics": [
                {
                    "name": "Trees",
                    "description": "Hierarchical acyclic connected structures including binary trees and BSTs.",
                    "difficulty": "medium",
                    "source_type": "explicit",
                    "source_pages": [4],
                    "subtopics": [
                        {
                            "name": "Tree Traversals",
                            "description": "Inorder, preorder, postorder and level-order depth/breadth visits",
                        }
                    ],
                },
                {
                    "name": "Graphs",
                    "description": "Networks of vertices and edges with cyclic and acyclic topologies.",
                    "difficulty": "hard",
                    "source_type": "explicit",
                    "source_pages": [4],
                    "subtopics": [
                        {
                            "name": "Breadth-First Search",
                            "description": "Queue-based level traversal for shortest path in unweighted graphs",
                        },
                        {
                            "name": "Depth-First Search",
                            "description": "Stack/recursive exploration of connected components",
                        },
                    ],
                },
            ],
        },
    ],
    "prerequisites": [
        {
            "topic": "Dynamic Programming",
            "prerequisite": "Recursion",
            "confidence": 0.95,
            "reason": "Understanding recursion and call state transitions is fundamental to identifying DP recurrence relations.",
        },
        {
            "topic": "Backtracking",
            "prerequisite": "Recursion",
            "confidence": 0.90,
            "reason": "Backtracking algorithms are implemented as recursive state-space traversals.",
        },
        {
            "topic": "Graphs",
            "prerequisite": "Trees",
            "confidence": 0.85,
            "reason": "Trees are a specialized subset of graphs; understanding tree traversals prepares students for BFS/DFS.",
        },
        {
            "topic": "Trees",
            "prerequisite": "Recursion",
            "confidence": 0.88,
            "reason": "Recursive division of left and right subtrees is the standard idiom for tree operations.",
        },
    ],
}

SAMPLE_DSA_LLM_OUTPUT_JSON = json.dumps(SAMPLE_DSA_EXTRACTION_DICT)

SAMPLE_CIRCULAR_PREREQ_DICT = {
    "units": [
        {
            "unit_name": "Unit 1",
            "topics": [
                {"name": "Topic A", "difficulty": "easy"},
                {"name": "Topic B", "difficulty": "medium"},
                {"name": "Topic C", "difficulty": "hard"},
            ],
        }
    ],
    "prerequisites": [
        {"topic": "Topic B", "prerequisite": "Topic A", "confidence": 0.9},
        {"topic": "Topic C", "prerequisite": "Topic B", "confidence": 0.9},
        {"topic": "Topic A", "prerequisite": "Topic C", "confidence": 0.9},  # Cycle: A -> B -> C -> A
    ],
}

SAMPLE_CIRCULAR_PREREQ_JSON = json.dumps(SAMPLE_CIRCULAR_PREREQ_DICT)

