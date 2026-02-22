"""
Graph Neural Network for AML node classification.

Uses GraphSAGE (Hamilton et al. 2017) — inductive, scales to unseen nodes.
Includes a pure-PyTorch fallback if torch_geometric is not installed.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    from torch_geometric.nn import SAGEConv

    class GraphSAGE(nn.Module):
        """Two-layer GraphSAGE node classifier (PyTorch Geometric)."""

        def __init__(
            self,
            in_channels: int,
            hidden_channels: int,
            out_channels: int,
            dropout: float = 0.3,
        ) -> None:
            super().__init__()
            self.conv1 = SAGEConv(in_channels, hidden_channels)
            self.conv2 = SAGEConv(hidden_channels, hidden_channels)
            self.classifier = nn.Linear(hidden_channels, out_channels)
            self.dropout = dropout

        def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
            x = F.relu(self.conv1(x, edge_index))
            x = F.dropout(x, p=self.dropout, training=self.training)
            x = F.relu(self.conv2(x, edge_index))
            x = F.dropout(x, p=self.dropout, training=self.training)
            return self.classifier(x)

        def embed(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
            """Return node embeddings without the classification head."""
            x = F.relu(self.conv1(x, edge_index))
            return F.relu(self.conv2(x, edge_index))

    USING_PYG = True

except ImportError:
    USING_PYG = False

    class GraphSAGE(nn.Module):  # type: ignore[no-redef]
        """Pure-PyTorch GraphSAGE fallback (no torch_geometric dependency)."""

        def __init__(
            self,
            in_channels: int,
            hidden_channels: int,
            out_channels: int,
            dropout: float = 0.3,
        ) -> None:
            super().__init__()
            half = hidden_channels // 2
            self.l1_self  = nn.Linear(in_channels, half)
            self.l1_neigh = nn.Linear(in_channels, half)
            self.l2_self  = nn.Linear(hidden_channels, half)
            self.l2_neigh = nn.Linear(hidden_channels, half)
            self.classifier = nn.Linear(hidden_channels, out_channels)
            self.dropout_p = dropout

        @staticmethod
        def _sage(
            lin_self: nn.Linear,
            lin_neigh: nn.Linear,
            x: torch.Tensor,
            edge_index: torch.Tensor,
        ) -> torch.Tensor:
            n, d = x.size()
            src, dst = edge_index[0], edge_index[1]
            agg    = torch.zeros(n, d, device=x.device)
            counts = torch.zeros(n, 1, device=x.device)
            agg.scatter_add_(0, dst.unsqueeze(1).expand(-1, d), x[src])
            counts.scatter_add_(0, dst.unsqueeze(1),
                                torch.ones(src.size(0), 1, device=x.device))
            agg = agg / (counts + 1e-8)
            return torch.cat([lin_self(x), lin_neigh(agg)], dim=-1)

        def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
            h = F.relu(self._sage(self.l1_self, self.l1_neigh, x, edge_index))
            h = F.dropout(h, p=self.dropout_p, training=self.training)
            h = F.relu(self._sage(self.l2_self, self.l2_neigh, h, edge_index))
            h = F.dropout(h, p=self.dropout_p, training=self.training)
            return self.classifier(h)

        def embed(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
            h = F.relu(self._sage(self.l1_self, self.l1_neigh, x, edge_index))
            return F.relu(self._sage(self.l2_self, self.l2_neigh, h, edge_index))


def build_graph_tensors(
    feature_matrix: "np.ndarray",
    node_ids: list[str],
    entities: list,
    transactions: list,
) -> object:
    """
    Convert feature matrix and entity/transaction lists into tensors.

    Returns a Data-like object (PyG Data if available, SimpleNamespace otherwise).
    """
    import numpy as np

    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}

    edges = [
        [id_to_idx[tx.src], id_to_idx[tx.dst]]
        for tx in transactions
        if tx.src in id_to_idx and tx.dst in id_to_idx
    ]

    edge_index = (
        torch.tensor(edges, dtype=torch.long).t().contiguous()
        if edges
        else torch.zeros((2, 0), dtype=torch.long)
    )

    x = torch.tensor(feature_matrix, dtype=torch.float32)
    y = torch.tensor([1 if e.is_suspicious else 0 for e in entities], dtype=torch.long)

    if USING_PYG:
        from torch_geometric.data import Data
        return Data(x=x, edge_index=edge_index, y=y)
    else:
        from types import SimpleNamespace
        return SimpleNamespace(x=x, edge_index=edge_index, y=y)
