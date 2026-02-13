"""
Knowledge Graph for Project Understanding

Builds a semantic graph of:
- Files as nodes
- Dependencies, imports, calls as edges
- Proximity-based retrieval (BFS from changed file)
- Finds modules most relevant to a change

No external vectors - pure graph traversal.
"""

import logging
from typing import Dict, Set, List, Optional, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass

from core.structured_logger import get_logger

logger = get_logger(__name__)


@dataclass
class GraphNode:
    """Node in knowledge graph."""
    id: str  # file path or symbol
    type: str  # "file", "class", "function", "module"
    metadata: Dict = None


@dataclass
class GraphEdge:
    """Edge in knowledge graph."""
    source: str
    target: str
    relation: str  # "imports", "calls", "extends", "depends_on", "uses"
    weight: float = 1.0  # For prioritization


class KnowledgeGraph:
    """Build and query semantic knowledge graph."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.adjacency: Dict[str, List[GraphEdge]] = defaultdict(list)
    
    def add_node(
        self,
        node_id: str,
        node_type: str,
        metadata: Optional[Dict] = None,
    ):
        """Add node to graph."""
        
        if node_id not in self.nodes:
            self.nodes[node_id] = GraphNode(
                id=node_id,
                type=node_type,
                metadata=metadata or {},
            )
    
    def add_edge(
        self,
        source: str,
        target: str,
        relation: str,
        weight: float = 1.0,
    ):
        """Add edge to graph."""
        
        # Ensure nodes exist
        if source not in self.nodes:
            self.add_node(source, "unknown")
        if target not in self.nodes:
            self.add_node(target, "unknown")
        
        edge = GraphEdge(source, target, relation, weight)
        self.edges.append(edge)
        self.adjacency[source].append(edge)
    
    def find_related_nodes(
        self,
        start_node: str,
        max_distance: int = 2,
        relation_filter: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Find nodes related to start_node using BFS.
        
        Args:
            start_node: Starting node ID
            max_distance: Max hops (1 = direct, 2 = 2 hops away)
            relation_filter: Only follow these relation types
        
        Returns:
            List of related node IDs, sorted by distance
        """
        
        if start_node not in self.nodes:
            self.logger.warning(f"Node {start_node} not in graph")
            return []
        
        visited = {}  # node_id -> distance
        queue = deque([(start_node, 0)])
        visited[start_node] = 0
        
        while queue:
            current, distance = queue.popleft()
            
            if distance >= max_distance:
                continue
            
            # Get edges from current node
            for edge in self.adjacency[current]:
                # Filter by relation type if specified
                if relation_filter and edge.relation not in relation_filter:
                    continue
                
                target = edge.target
                new_distance = distance + 1
                
                if target not in visited:
                    visited[target] = new_distance
                    queue.append((target, new_distance))
        
        # Remove start node and sort by distance
        visited.pop(start_node, None)
        sorted_nodes = sorted(visited.items(), key=lambda x: (x[1], x[0]))
        
        return [node_id for node_id, _ in sorted_nodes]
    
    def find_shortest_path(self, source: str, target: str) -> Optional[List[str]]:
        """
        Find shortest path from source to target.
        
        Returns:
            List of node IDs from source to target, or None if unreachable
        """
        
        if source == target:
            return [source]
        
        if source not in self.nodes or target not in self.nodes:
            return None
        
        visited = {source}
        queue = deque([(source, [source])])
        
        while queue:
            current, path = queue.popleft()
            
            for edge in self.adjacency[current]:
                if edge.target == target:
                    return path + [target]
                
                if edge.target not in visited:
                    visited.add(edge.target)
                    queue.append((edge.target, path + [edge.target]))
        
        return None
    
    def get_node_importance(self, node_id: str) -> float:
        """
        Calculate importance of node using PageRank-like metric.
        
        Based on incoming/outgoing edges and relation weights.
        
        Returns:
            Importance score (0.0 to 1.0)
        """
        
        if node_id not in self.nodes:
            return 0.0
        
        # Count incoming and outgoing edges
        outgoing = len(self.adjacency[node_id])
        incoming = sum(
            1 for edges in self.adjacency.values()
            for edge in edges if edge.target == node_id
        )
        
        # Simple score: degree centrality
        total_edges = len(self.edges)
        if total_edges == 0:
            return 0.0
        
        centrality = (incoming + outgoing) / (2 * total_edges)
        return min(centrality, 1.0)  # Normalize to [0, 1]
    
    def find_impact_zone(
        self,
        changed_file: str,
        radius: int = 2,
    ) -> Dict[str, int]:
        """
        Find files potentially impacted by change to changed_file.
        
        Args:
            changed_file: File path that changed
            radius: How far to propagate impact
        
        Returns:
            {file: proximity_distance}
        """
        
        forward_impact = {}
        
        # Forward propagation (who depends on this file)
        for node_id in self.find_related_nodes(
            changed_file,
            max_distance=radius,
            relation_filter=["imports", "calls", "extends"],
        ):
            # Only include files, not internal symbols
            if "/" in node_id or node_id.endswith(('.py', '.js', '.ts', '.java')):
                path = self._extract_file_path(node_id)
                forward_impact[path] = self.find_shortest_path(changed_file, node_id).__len__()
        
        return forward_impact
    
    def export_json(self) -> Dict:
        """Export graph as JSON for visualization."""
        
        return {
            "nodes": [
                {
                    "id": node.id,
                    "type": node.type,
                    "metadata": node.metadata,
                }
                for node in self.nodes.values()
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "relation": edge.relation,
                    "weight": edge.weight,
                }
                for edge in self.edges
            ],
        }
    
    @staticmethod
    def _extract_file_path(node_id: str) -> str:
        """Extract file path from node ID."""
        
        # If it's a symbol like "file.py:ClassName.method", extract file
        if ":" in node_id:
            return node_id.split(":")[0]
        
        return node_id


class ProjectGraphBuilder:
    """Build knowledge graph from project."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.graph = KnowledgeGraph()
    
    def build_from_analysis(
        self,
        files: Dict[str, any],  # From ProjectAnalyzer
        dependencies: Dict[str, any],
    ) -> KnowledgeGraph:
        """
        Build graph from project analysis.
        
        Args:
            files: File analysis dict {path: FileInfo}
            dependencies: Dependencies dict {name: DependencyInfo}
        
        Returns:
            Populated KnowledgeGraph
        """
        
        # Add file nodes
        for file_path, file_info in files.items():
            self.graph.add_node(
                file_path,
                "file",
                {
                    "language": file_info.language,
                    "is_test": file_info.is_test,
                    "complexity": file_info.complexity,
                },
            )
        
        # Add dependency nodes
        for dep_name, dep_info in dependencies.items():
            self.graph.add_node(
                f"dep:{dep_name}",
                "dependency",
                {"version": dep_info.version, "scope": dep_info.scope},
            )
        
        # Add edges from imports
        for file_path, file_info in files.items():
            for imp in file_info.imports:
                # Link to dependency
                dep_node = f"dep:{imp}"
                if dep_node in self.graph.nodes:
                    self.graph.add_edge(file_path, dep_node, "imports", weight=0.8)
                
                # Link to other files (if file exists)
                for other_file in files.keys():
                    if imp in other_file:
                        self.graph.add_edge(file_path, other_file, "imports", weight=0.9)
        
        self.logger.info(
            f"✓ Built knowledge graph: "
            f"{len(self.graph.nodes)} nodes, {len(self.graph.edges)} edges"
        )
        
        return self.graph
