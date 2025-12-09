"""
VAST Parser - Enhanced Parser Module
Production-ready with filtering, sorting, and backward compatibility

Features:
- XPath-based filtering (@type='video/mp4', @width >= '1280')
- Sorting by any attribute (sort_by: "bitrate", sort_order: "desc")
- Limiting results (limit: 1)
- Merge strategies (append, replace, update)
- Full VAST 2.0-4.2 support
- Backward compatible with existing code
"""

from typing import Any, Dict, List, Optional, Union
from lxml import etree
import json
from dataclasses import dataclass
from enum import Enum


class MergeStrategy(Enum):
    """Strategy for merging parsed values"""
    APPEND = "append"      # Add to list
    REPLACE = "replace"    # Replace with latest
    UPDATE = "update"      # Merge dicts


@dataclass
class XPathRule:
    """Configuration for a single XPath rule"""
    xpath: str
    merge: str = "replace"
    target: Optional[str] = None
    extract_node: bool = False
    fields: Optional[Dict[str, str]] = None
    attributes: Optional[List[str]] = None
    sort_by: Optional[str] = None
    sort_order: str = "asc"
    limit: Optional[int] = None
    text: bool = False


class VASTParser:
    """
    Base VAST Parser - maintains backward compatibility
    """
    
    NAMESPACES = {"vast": "http://www.iab.com/VAST"}
    
    def __init__(self, namespaces: Optional[Dict] = None):
        self.namespaces = namespaces or self.NAMESPACES
    
    def parse(self, xml_string: str) -> Dict[str, Any]:
        """
        Legacy parse method - no config, simple extraction
        
        Returns flat dict with all elements found
        
        This is for backward compatibility with existing code
        """
        root = etree.fromstring(xml_string.encode('utf-8'))
        result = {}
        
        # Legacy extraction - all impressions, all errors, all tracking
        impressions = root.xpath("//vast:Impression/text()", namespaces=self.NAMESPACES)
        errors = root.xpath("//vast:Error/text()", namespaces=self.NAMESPACES)
        tracking = root.xpath("//vast:Tracking", namespaces=self.NAMESPACES)
        
        if impressions:
            result['impressions'] = impressions
        if errors:
            result['errors'] = errors
        if tracking:
            result['tracking'] = [
                {
                    'event': t.get('event'),
                    'url': t.text.strip() if t.text else None
                }
                for t in tracking
            ]
        
        return result
    
    def parse_file(self, filepath: str) -> Dict[str, Any]:
        """Parse VAST from file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return self.parse(f.read())


class EnhancedVASTParser(VASTParser):
    """
    Enhanced VAST Parser with filtering, sorting, and configuration
    
    Features:
    - Config-based parsing
    - XPath filtering
    - Sorting and limiting
    - Backward compatible
    """
    
    def __init__(self, config: Dict[str, Any], namespaces: Optional[Dict] = None):
        super().__init__(namespaces)
        self.config = config
    
    def parse(self, xml_string: str) -> Dict[str, Any]:
        """Parse VAST XML with config, filtering, and sorting"""
        root = etree.fromstring(xml_string.encode('utf-8'))
        result = {}
        
        for section, rules in self.config.items():
            for key, rule in rules.items():
                self._process_rule(root, section, key, rule, result)
        
        return result
    
    def _process_rule(
        self,
        root: etree._Element,
        section: str,
        key: str,
        rule: Union[Dict[str, Any], XPathRule],
        result: Dict
    ):
        """Process a single rule with filtering, sorting, limiting"""
        if isinstance(rule, dict):
            rule_dict = rule
        else:
            rule_dict = rule.__dict__
        
        xpath = rule_dict.get("xpath")
        if not xpath:
            return
        
        # Find elements
        try:
            elements = root.xpath(xpath, namespaces=self.namespaces)
        except etree.XPathEvalError as e:
            if hasattr(self, "logger"):
                self.logger.error("xpath_eval_failed", xpath=xpath, error=str(e))
            else:
                # Fallback: print or ignore if logger not present
                pass
            return
        if not elements:
            return
        
        # Extract values
        if rule_dict.get("extract_node") and rule_dict.get("fields"):
            values = self._extract_complex_nodes(elements, rule_dict["fields"])
        elif rule_dict.get("attributes"):
            values = self._extract_attributes(elements, rule_dict)
        else:
            values = [
                elem.text.strip() if hasattr(elem, 'text') and elem.text else str(elem)
                for elem in elements
            ]
        
        # Apply sorting
        if rule_dict.get("sort_by"):
            values = self._apply_sort(
                values,
                rule_dict["sort_by"],
                rule_dict.get("sort_order", "asc")
            )
        
        # Apply limit
        if rule_dict.get("limit"):
            values = values[:rule_dict["limit"]]
        
        # Merge
        if values:
            target = rule_dict.get("target", f"{section}.{key}")
            self._merge_values(result, target, values, rule_dict.get("merge", "replace"))
    
    def _extract_attributes(self, elements: List, rule: Dict) -> List[Dict]:
        """Extract attributes from elements"""
        result = []
        for elem in elements:
            obj = {attr: elem.get(attr) for attr in rule["attributes"]}
            if rule.get("text"):
                obj["text"] = elem.text.strip() if elem.text else None
            result.append(obj)
        return result
    
    def _extract_complex_nodes(
        self,
        elements: List,
        fields: Dict[str, str]
    ) -> List[Dict]:
        """Extract complex node structures"""
        result = []
        for elem in elements:
            obj = {}
            for field_name, field_path in fields.items():
                if field_path.startswith("@"):
                    obj[field_name] = elem.get(field_path[1:])
                elif field_path == "text()":
                    obj[field_name] = elem.text.strip() if elem.text else None
                elif field_path.startswith("concat("):
                    obj[field_name] = self._process_concat(elem, field_path)
                else:
                    sub = elem.xpath(field_path, namespaces=self.namespaces)
                    obj[field_name] = sub[0] if sub else None
            result.append(obj)
        return result
    
    def _process_concat(self, elem: etree._Element, concat_expr: str) -> str:
        """Process concat() expressions"""
        expr = concat_expr.replace("concat(", "").replace(")", "")
        parts = [p.strip() for p in expr.split(", ")]
        
        values = []
        for part in parts:
            if part.startswith("@"):
                val = elem.get(part[1:]) or "?"
                values.append(val)
            else:
                values.append(part.strip("'\""))
        
        return "".join(values)
    
    def _apply_sort(
        self,
        values: List[Dict],
        sort_key: str,
        sort_order: str = "asc"
    ) -> List[Dict]:
        """Sort by field with automatic type conversion"""
        reverse = sort_order.lower() == "desc"
        
        def sort_fn(item):
            val = item.get(sort_key) if isinstance(item, dict) else item
            try:
                return float(val) if val else 0
            except (ValueError, TypeError):
                return str(val) if val else ""
        
        return sorted(values, key=sort_fn, reverse=reverse)
    
    def _merge_values(
        self,
        result: Dict,
        path: str,
        values: List,
        strategy: str
    ):
        """Merge values using dot-notation path"""
        keys = path.split(".")
        obj = result
        
        for k in keys[:-1]:
            obj = obj.setdefault(k, {})
        
        last_key = keys[-1]
        
        if strategy == "append":
            if last_key not in obj:
                obj[last_key] = []
            elif not isinstance(obj[last_key], list):
                obj[last_key] = [obj[last_key]]
            obj[last_key].extend(values)
        
        elif strategy == "replace":
            obj[last_key] = values[-1] if values else None
        
        elif strategy == "update":
            if values:
                if isinstance(values[0], dict):
                    if last_key not in obj:
                        obj[last_key] = {}
                    obj[last_key].update(values[0])
                else:
                    obj[last_key] = values[0]
    
    def to_json(self, result: Dict, indent: int = 2) -> str:
        """Convert result to JSON"""
        return json.dumps(result, indent=indent, ensure_ascii=False)
