"""
Formula service for safe evaluation of derived metrics.

This module provides a secure formula evaluation engine that:
- Parses formula strings containing metric references and arithmetic
- Validates formulas against allowed tokens and operators
- Evaluates formulas using only provided metric values
- Prevents arbitrary code execution (no Python eval)
"""
import re
import ast
import operator
from decimal import Decimal, InvalidOperation
from typing import Dict, Optional, Any, List, Set


class FormulaError(Exception):
    """Exception raised for formula parsing or evaluation errors."""
    pass


class FormulaService:
    """
    Service class for safe formula evaluation.
    
    Supports:
    - Metric key references (e.g., total_calls, missed_calls)
    - Numeric constants (integers and decimals)
    - Basic arithmetic operators: +, -, *, /
    - Parentheses for grouping
    
    Future extensions can add functions like min, max, coalesce.
    """
    
    # Allowed operators
    OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }
    
    # Pattern for valid metric keys (alphanumeric with underscores)
    METRIC_KEY_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    
    # Pattern for tokenizing formulas
    TOKEN_PATTERN = re.compile(
        r'(\d+\.?\d*)|'  # Numbers
        r'([a-zA-Z_][a-zA-Z0-9_]*)|'  # Identifiers (metric keys)
        r'([+\-*/()])|'  # Operators and parentheses
        r'(\s+)'  # Whitespace
    )
    
    @classmethod
    def validate_formula(cls, formula: str, available_metrics: Set[str] = None) -> List[str]:
        """
        Validate a formula string.
        
        Args:
            formula: Formula string to validate
            available_metrics: Optional set of available metric keys
            
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        if not formula or not formula.strip():
            errors.append("Formula cannot be empty")
            return errors
        
        # Extract metric references from formula
        referenced_metrics = cls.extract_metric_keys(formula)
        
        # Check if referenced metrics are available
        if available_metrics:
            for metric_key in referenced_metrics:
                if metric_key not in available_metrics:
                    errors.append(f"Unknown metric reference: {metric_key}")
        
        # Try to parse the formula
        try:
            cls._parse_formula(formula)
        except FormulaError as e:
            errors.append(str(e))
        except Exception as e:
            errors.append(f"Invalid formula syntax: {str(e)}")
        
        return errors
    
    @classmethod
    def extract_metric_keys(cls, formula: str) -> Set[str]:
        """
        Extract all metric key references from a formula.
        
        Args:
            formula: Formula string
            
        Returns:
            Set of metric keys referenced in the formula
        """
        keys = set()
        for match in re.finditer(r'[a-zA-Z_][a-zA-Z0-9_]*', formula):
            key = match.group()
            # Exclude potential future function names
            if key not in ('min', 'max', 'coalesce', 'abs', 'round'):
                keys.add(key)
        return keys
    
    @classmethod
    def evaluate(cls, formula: str, values: Dict[str, float]) -> float:
        """
        Safely evaluate a formula with given metric values.
        
        Args:
            formula: Formula string (e.g., "missed_calls / total_calls * 100")
            values: Dictionary mapping metric keys to their numeric values
            
        Returns:
            Calculated numeric result
            
        Raises:
            FormulaError: If formula is invalid or evaluation fails
        """
        if not formula or not formula.strip():
            raise FormulaError("Formula cannot be empty")
        
        # Substitute metric keys with their values
        substituted = cls._substitute_values(formula, values)
        
        # Parse and evaluate
        try:
            tree = cls._parse_formula(substituted)
            result = cls._eval_node(tree)
            return float(result)
        except ZeroDivisionError:
            raise FormulaError("Division by zero in formula")
        except FormulaError:
            raise
        except Exception as e:
            raise FormulaError(f"Formula evaluation error: {str(e)}")
    
    @classmethod
    def _substitute_values(cls, formula: str, values: Dict[str, float]) -> str:
        """
        Substitute metric keys in formula with their numeric values.
        
        Args:
            formula: Original formula string
            values: Dictionary of metric values
            
        Returns:
            Formula with metric keys replaced by values
        """
        result = formula
        
        # Sort keys by length (longest first) to avoid partial replacements
        sorted_keys = sorted(values.keys(), key=len, reverse=True)
        
        for key in sorted_keys:
            if key in result:
                # Use word boundary replacement to avoid partial matches
                pattern = r'\b' + re.escape(key) + r'\b'
                result = re.sub(pattern, str(values[key]), result)
        
        # Check for any remaining unsubstituted metric keys
        remaining = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', result)
        if remaining:
            # Filter out potential function names
            unknown = [k for k in remaining if k not in ('min', 'max', 'coalesce', 'abs', 'round')]
            if unknown:
                raise FormulaError(f"Missing values for metrics: {', '.join(unknown)}")
        
        return result
    
    @classmethod
    def _parse_formula(cls, formula: str) -> ast.Expression:
        """
        Parse a formula string into an AST.
        
        Args:
            formula: Formula string (with values already substituted)
            
        Returns:
            AST Expression node
            
        Raises:
            FormulaError: If parsing fails
        """
        try:
            tree = ast.parse(formula, mode='eval')
            cls._validate_ast(tree.body)
            return tree.body
        except SyntaxError as e:
            raise FormulaError(f"Invalid formula syntax: {str(e)}")
    
    @classmethod
    def _validate_ast(cls, node: ast.AST) -> None:
        """Validate that an AST node contains only allowed operations.

        Allowed:
        - Numeric constants
        - Metric identifiers (``ast.Name``)
        - Binary ops (+, -, *, /)
        - Unary ops (+, -)
        Everything else (calls, attributes, etc.) is rejected.
        """
        if isinstance(node, ast.Constant):
            # Allow numeric constants
            if not isinstance(node.value, (int, float)):
                raise FormulaError(f"Only numeric constants are allowed, got: {type(node.value).__name__}")
        elif isinstance(node, ast.Num):
            # Python 3.7 compatibility
            pass
        elif isinstance(node, ast.Name):
            # Allow bare identifiers; ensure they look like metric keys
            if not cls.METRIC_KEY_PATTERN.match(node.id):
                raise FormulaError(f"Invalid identifier in formula: {node.id}")
        elif isinstance(node, ast.BinOp):
            # Binary operations (+, -, *, /)
            if type(node.op) not in cls.OPERATORS:
                raise FormulaError(f"Operator not allowed: {type(node.op).__name__}")
            cls._validate_ast(node.left)
            cls._validate_ast(node.right)
        elif isinstance(node, ast.UnaryOp):
            # Unary operations (+, -)
            if type(node.op) not in cls.OPERATORS:
                raise FormulaError(f"Unary operator not allowed: {type(node.op).__name__}")
            cls._validate_ast(node.operand)
        elif isinstance(node, ast.Expression):
            cls._validate_ast(node.body)
        else:
            raise FormulaError(f"Expression type not allowed: {type(node).__name__}")
    
    @classmethod
    def _eval_node(cls, node: ast.AST) -> float:
        """
        Recursively evaluate an AST node.
        
        Args:
            node: AST node to evaluate
            
        Returns:
            Numeric result
        """
        if isinstance(node, ast.Constant):
            return float(node.value)
        elif isinstance(node, ast.Num):
            # Python 3.7 compatibility
            return float(node.n)
        elif isinstance(node, ast.BinOp):
            left = cls._eval_node(node.left)
            right = cls._eval_node(node.right)
            op_func = cls.OPERATORS[type(node.op)]
            return op_func(left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = cls._eval_node(node.operand)
            op_func = cls.OPERATORS[type(node.op)]
            return op_func(operand)
        else:
            raise FormulaError(f"Cannot evaluate node type: {type(node).__name__}")
    
    @classmethod
    def compute_derived_metrics(cls, base_values: Dict[str, float], 
                                 derived_metrics: list) -> Dict[str, float]:
        """
        Compute all derived metrics from base values.
        
        Args:
            base_values: Dictionary of base metric values
            derived_metrics: List of MetricDefinition objects for derived metrics,
                           ordered by layer (lower layers first)
            
        Returns:
            Dictionary mapping derived metric keys to calculated values
        """
        results = {}
        all_values = base_values.copy()
        
        # Process metrics in layer order
        for metric in sorted(derived_metrics, key=lambda m: m.layer):
            if metric.formula:
                try:
                    value = cls.evaluate(metric.formula, all_values)
                    results[metric.key] = value
                    # Add to all_values so higher-layer metrics can reference it
                    all_values[metric.key] = value
                except FormulaError as e:
                    # Store error indicator or None for failed calculations
                    results[metric.key] = None
        
        return results
    
    @classmethod
    def format_value(cls, value: float, unit: str) -> str:
        """
        Format a metric value for display.
        
        Args:
            value: Numeric value
            unit: Unit type
            
        Returns:
            Formatted string
        """
        if value is None:
            return "N/A"
        
        if unit == 'percent':
            return f"{value:.2f}%"
        elif unit == 'currency':
            return f"${value:,.2f}"
        elif unit == 'mins':
            if value == int(value):
                return f"{int(value):,} min"
            return f"{value:,.1f} min"
        elif unit == 'days':
            return f"{value:.1f}d"
        else:
            # Default: number/count
            if value == int(value):
                return f"{int(value):,}"
            return f"{value:,.2f}"
