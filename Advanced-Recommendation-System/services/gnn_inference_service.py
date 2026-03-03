"""
GNN Inference Service - Production Link Prediction.

Loads trained GNN model and provides efficient skill probability predictions.
Performance target: <200ms per candidate.
"""
import logging
import json
import time
from pathlib import Path
from typing import Dict, Optional
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import SAGEConv, HeteroConv

logger = logging.getLogger(__name__)


# ============================================================================
# GNN MODEL ARCHITECTURE (must match training)
# ============================================================================

class HeteroGNN(nn.Module):
    """Heterogeneous GNN for link prediction using HeteroConv."""
    
    def __init__(self, metadata, hidden_dim, num_layers, dropout=0.3):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.dropout = dropout
        
        # Extract node types and edge types from metadata
        node_types, edge_types = metadata
        
        # Create heterogeneous convolution layers
        self.convs = nn.ModuleList()
        for i in range(num_layers):
            conv_dict = {}
            for edge_type in edge_types:
                src_type, _, dst_type = edge_type
                # Use SAGEConv for each edge type
                conv_dict[edge_type] = SAGEConv((-1, -1), hidden_dim)
            
            self.convs.append(HeteroConv(conv_dict, aggr='mean'))
        
    def forward(self, x_dict, edge_index_dict):
        """Forward pass through GNN layers."""
        for i, conv in enumerate(self.convs):
            x_dict = conv(x_dict, edge_index_dict)
            if i < self.num_layers - 1:
                x_dict = {key: F.relu(x) for key, x in x_dict.items()}
                x_dict = {key: F.dropout(x, p=self.dropout, training=self.training)
                         for key, x in x_dict.items()}
        return x_dict


class LinkPredictionModel(nn.Module):
    """Full link prediction model with GNN encoder + dot product decoder."""
    
    def __init__(self, metadata, hidden_dim, num_layers, dropout=0.3):
        super().__init__()
        self.encoder = HeteroGNN(metadata, hidden_dim, num_layers, dropout)
        
    def forward(self, x_dict, edge_index_dict):
        """Encode nodes to embeddings."""
        return self.encoder(x_dict, edge_index_dict)
    
    def decode(self, z_person, z_skill, edge_label_index):
        """
        Decode edge scores using dot product.
        
        Args:
            z_person: Person embeddings [num_persons, hidden_dim]
            z_skill: Skill embeddings [num_skills, hidden_dim]
            edge_label_index: [2, num_edges] tensor
            
        Returns:
            scores: [num_edges] tensor
        """
        person_embeds = z_person[edge_label_index[0]]
        skill_embeds = z_skill[edge_label_index[1]]
        scores = (person_embeds * skill_embeds).sum(dim=-1)
        return scores


# ============================================================================
# INFERENCE SERVICE
# ============================================================================

class GNNInferenceService:
    """
    Production GNN inference service.
    
    Loads trained model at startup and provides fast skill probability predictions.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Singleton pattern to ensure single model load."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize service (only once)."""
        if GNNInferenceService._initialized:
            return
            
        self.model = None
        self.graph_data = None
        self.id_maps = None
        self.skill_idx_to_name = None
        self.candidate_id_to_idx = None
        self.device = torch.device('cpu')  # Production uses CPU
        
        GNNInferenceService._initialized = True
        logger.info("GNN Inference Service initialized")
    
    def load_model(self, model_path: str, data_path: str, id_maps_path: str):
        """
        Load trained GNN model and graph data at startup.
        
        Args:
            model_path: Path to best_gnn_linkpred.pt
            data_path: Path to heterodata_lp.pt
            id_maps_path: Path to id_maps.json
        """
        start_time = time.time()
        logger.info("Loading GNN model and graph data...")
        
        # Load graph data
        logger.info(f"Loading graph data from {data_path}")
        self.graph_data = torch.load(data_path, map_location=self.device, weights_only=False)
        
        # Add reverse edges for bidirectional message passing (same as training)
        logger.info("Adding reverse edges for bidirectional message passing...")
        if ('person', 'has_skill', 'skill') in self.graph_data.edge_types:
            self.graph_data['skill', 'rev_has_skill', 'person'].edge_index = \
                self.graph_data['person', 'has_skill', 'skill'].edge_index.flip(0)
        
        if ('person', 'worked_on', 'project') in self.graph_data.edge_types:
            self.graph_data['project', 'rev_worked_on', 'person'].edge_index = \
                self.graph_data['person', 'worked_on', 'project'].edge_index.flip(0)
        
        if ('project', 'uses_technology', 'skill') in self.graph_data.edge_types:
            self.graph_data['skill', 'rev_uses_technology', 'project'].edge_index = \
                self.graph_data['project', 'uses_technology', 'skill'].edge_index.flip(0)
        
        if ('skill', 'belongs_to_category', 'skill_category') in self.graph_data.edge_types:
            self.graph_data['skill_category', 'rev_belongs_to_category', 'skill'].edge_index = \
                self.graph_data['skill', 'belongs_to_category', 'skill_category'].edge_index.flip(0)
        
        # Load ID mappings
        logger.info(f"Loading ID mappings from {id_maps_path}")
        with open(id_maps_path, 'r', encoding='utf-8') as f:
            self.id_maps = json.load(f)
        
        # Build reverse mappings (handle both old and new format)
        # Old format: {'person_to_idx': {...}, 'skill_to_idx': {...}}
        # New format: {'person': {...}, 'skill': {...}}
        if 'person_to_idx' in self.id_maps:
            person_map = self.id_maps['person_to_idx']
            skill_map = self.id_maps['skill_to_idx']
        else:
            person_map = self.id_maps['person']
            skill_map = self.id_maps['skill']
        
        self.skill_idx_to_name = {v: k for k, v in skill_map.items()}
        self.candidate_id_to_idx = {k: v for k, v in person_map.items()}
        
        # Initialize model architecture
        logger.info("Initializing model architecture")
        metadata = self.graph_data.metadata()
        
        # Production model: hidden_dim=128, num_layers=2, dropout=0.3
        self.model = LinkPredictionModel(
            metadata=metadata,
            hidden_dim=128,
            num_layers=2,
            dropout=0.3
        ).to(self.device)
        
        # Dummy forward pass to initialize lazy modules
        x_dict = {node_type: self.graph_data[node_type].x for node_type in self.graph_data.node_types}
        edge_index_dict = {edge_type: self.graph_data[edge_type].edge_index 
                          for edge_type in self.graph_data.edge_types}
        with torch.no_grad():
            _ = self.model(x_dict, edge_index_dict)
        
        # Load trained weights
        logger.info(f"Loading trained weights from {model_path}")
        checkpoint = torch.load(model_path, map_location=self.device, weights_only=False)
        
        # Handle both checkpoint formats
        if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
            # Format: {'model_state_dict': state_dict, 'epoch': ..., ...}
            self.model.load_state_dict(checkpoint['model_state_dict'])
        else:
            # Format: state_dict directly (OrderedDict)
            self.model.load_state_dict(checkpoint)
        
        # Set to eval mode
        self.model.eval()
        
        load_time = time.time() - start_time
        logger.info(f"GNN model loaded successfully in {load_time:.2f}s")
        logger.info(f"  - Graph: {self.graph_data.num_nodes} nodes, {len(self.graph_data.edge_types)} edge types")
        logger.info(f"  - Persons: {self.graph_data['person'].num_nodes}")
        logger.info(f"  - Skills: {self.graph_data['skill'].num_nodes}")
        logger.info(f"  - Model parameters: {sum(p.numel() for p in self.model.parameters())}")
    
    def predict_skill_probs(self, candidate_id: str, use_fallback: bool = True) -> Dict[str, float]:
        """
        Predict skill probabilities for a candidate.
        
        For NEW CANDIDATES (not in training data):
        - If use_fallback=True: Returns average P_gnn across all skills (graceful degradation)
        - If use_fallback=False: Raises ValueError (strict mode)
        
        This allows hybrid ranking to work for real-time candidates added via API.
        
        Args:
            candidate_id: Neo4j candidate_id
            use_fallback: If True, use average P_gnn for unknown candidates (default: True)
            
        Returns:
            Dict mapping skill_name to P_gnn (probability from GNN)
            
        Raises:
            ValueError: If candidate not found and use_fallback=False
            RuntimeError: If GNN model not loaded
        """
        if self.model is None:
            raise RuntimeError("GNN model not loaded. Call load_model() first.")
        
        start_time = time.time()
        
        # Check if candidate exists in training data
        if candidate_id not in self.candidate_id_to_idx:
            if not use_fallback:
                raise ValueError(f"Candidate {candidate_id} not found in graph data")
            
            # NEW CANDIDATE: Use fallback strategy
            logger.warning(
                f"⚠️  Candidate {candidate_id} not in GNN training data. "
                f"Using average P_gnn fallback for hybrid ranking."
            )
            return self._predict_with_fallback(candidate_id)
        
        person_idx = self.candidate_id_to_idx[candidate_id]
        
        # Run GNN forward pass ONCE to get all embeddings
        x_dict = {node_type: self.graph_data[node_type].x for node_type in self.graph_data.node_types}
        edge_index_dict = {edge_type: self.graph_data[edge_type].edge_index 
                          for edge_type in self.graph_data.edge_types}
        
        with torch.no_grad():
            z_dict = self.model(x_dict, edge_index_dict)
        
        # Extract person and skill embeddings
        z_person = z_dict['person']  # [num_persons, hidden_dim]
        z_skill = z_dict['skill']    # [num_skills, hidden_dim]
        
        # Get this person's embedding
        person_embed = z_person[person_idx].unsqueeze(0)  # [1, hidden_dim]
        
        # Compute dot products with ALL skills
        scores = torch.matmul(person_embed, z_skill.T).squeeze(0)  # [num_skills]
        
        # Apply sigmoid to get probabilities
        probs = torch.sigmoid(scores)
        
        # Convert to dict {skill_name: P_gnn}
        skill_probs = {}
        for skill_idx in range(len(probs)):
            skill_name = self.skill_idx_to_name.get(skill_idx)
            if skill_name:
                skill_probs[skill_name] = float(probs[skill_idx].item())
        
        inference_time = (time.time() - start_time) * 1000  # Convert to ms
        logger.debug(f"GNN inference for {candidate_id}: {inference_time:.1f}ms ({len(skill_probs)} skills)")
        
        if inference_time > 200:
            logger.warning(f"GNN inference took {inference_time:.1f}ms (target: <200ms)")
        
        return skill_probs
    
    def _predict_with_fallback(self, candidate_id: str) -> Dict[str, float]:
        """
        Fallback strategy for NEW CANDIDATES not in training data.
        
        Strategy: Compute average P_gnn across all training candidates for each skill.
        This provides a reasonable baseline that:
        - Doesn't crash the system
        - Reflects average learnability patterns
        - Allows hybrid ranking to work (with reduced personalization)
        
        Returns:
            Dict mapping skill_name to average P_gnn
        """
        logger.info(f"Computing fallback P_gnn for new candidate: {candidate_id}")
        start_time = time.time()
        
        # Run GNN forward pass to get all embeddings
        x_dict = {node_type: self.graph_data[node_type].x for node_type in self.graph_data.node_types}
        edge_index_dict = {edge_type: self.graph_data[edge_type].edge_index 
                          for edge_type in self.graph_data.edge_types}
        
        with torch.no_grad():
            z_dict = self.model(x_dict, edge_index_dict)
        
        z_person = z_dict['person']  # [num_persons, hidden_dim]
        z_skill = z_dict['skill']    # [num_skills, hidden_dim]
        
        # Compute scores for ALL person-skill pairs
        all_scores = torch.matmul(z_person, z_skill.T)  # [num_persons, num_skills]
        
        # Apply sigmoid
        all_probs = torch.sigmoid(all_scores)  # [num_persons, num_skills]
        
        # Compute MEAN probability for each skill across all persons
        mean_probs = all_probs.mean(dim=0)  # [num_skills]
        
        # Convert to dict
        skill_probs = {}
        for skill_idx in range(len(mean_probs)):
            skill_name = self.skill_idx_to_name.get(skill_idx)
            if skill_name:
                skill_probs[skill_name] = float(mean_probs[skill_idx].item())
        
        fallback_time = (time.time() - start_time) * 1000
        logger.info(
            f"✓ Fallback computed in {fallback_time:.1f}ms: "
            f"{len(skill_probs)} skills with avg P_gnn={sum(skill_probs.values())/len(skill_probs):.3f}"
        )
        
        return skill_probs
    
    def is_ready(self) -> bool:
        """Check if service is ready for inference."""
        return self.model is not None and self.graph_data is not None
    
    def get_stats(self) -> Dict:
        """Get service statistics."""
        if not self.is_ready():
            return {"status": "not_loaded"}
        
        return {
            "status": "ready",
            "num_persons": self.graph_data['person'].num_nodes,
            "num_skills": self.graph_data['skill'].num_nodes,
            "num_edge_types": len(self.graph_data.edge_types),
            "model_params": sum(p.numel() for p in self.model.parameters()),
            "device": str(self.device)
        }


# ============================================================================
# GLOBAL SERVICE INSTANCE
# ============================================================================

# Singleton instance to be used across the application
gnn_service = GNNInferenceService()
