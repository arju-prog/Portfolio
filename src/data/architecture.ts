// System-diagram model shared by experience and projects.
// Nodes sit on a small grid (col, row); the renderer turns that into an SVG.

export type NodeKind = 'source' | 'process' | 'store' | 'service' | 'agent' | 'output';

export type ArchNode = {
  id: string;
  label: string;
  sub?: string; // short second line on the node
  detail: string; // shown when the node is selected
  col: number;
  row: number;
  kind: NodeKind;
};

export type ArchEdge = { from: string; to: string; label?: string; dashed?: boolean };

export type Architecture = {
  title: string;
  caption: string;
  nodes: ArchNode[];
  edges: ArchEdge[];
};
