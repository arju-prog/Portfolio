'use client';

import { useId, useMemo, useState, type KeyboardEvent } from 'react';
import type { ArchEdge, ArchNode, Architecture } from '@/data/architecture';

// Grid → SVG geometry
const CELL_W = 244;
const CELL_H = 128;
const NODE_W = 172;
const NODE_H = 64;
const PAD = 20;

type Box = { x: number; y: number; cx: number; cy: number };

function boxOf(n: ArchNode): Box {
  const x = PAD + n.col * CELL_W;
  const y = PAD + n.row * CELL_H;
  return { x, y, cx: x + NODE_W / 2, cy: y + NODE_H / 2 };
}

/** Bezier from one node to another, leaving/entering through the most natural sides. */
function edgePath(a: Box, b: Box) {
  const dx = b.cx - a.cx;
  const dy = b.cy - a.cy;
  if (Math.abs(dx) >= Math.abs(dy) && dx > 0) {
    // left → right
    const x1 = a.x + NODE_W, y1 = a.cy, x2 = b.x, y2 = b.cy;
    const k = Math.max(30, (x2 - x1) / 2);
    return { d: `M${x1},${y1} C${x1 + k},${y1} ${x2 - k},${y2} ${x2},${y2}`, mx: (x1 + x2) / 2, my: (y1 + y2) / 2 };
  }
  if (Math.abs(dy) > Math.abs(dx) || dx === 0) {
    // vertical
    const down = dy > 0;
    const x1 = a.cx, y1 = down ? a.y + NODE_H : a.y, x2 = b.cx, y2 = down ? b.y : b.y + NODE_H;
    const k = Math.max(24, Math.abs(y2 - y1) / 2) * (down ? 1 : -1);
    return { d: `M${x1},${y1} C${x1},${y1 + k} ${x2},${y2 - k} ${x2},${y2}`, mx: (x1 + x2) / 2, my: (y1 + y2) / 2 };
  }
  // right → left (a feedback loop): rise into the gap between rows, run left, enter the target's right side
  const x1 = a.cx, y1 = a.y, x2 = b.x + NODE_W, y2 = b.cy + 18;
  const ym = (b.y + NODE_H + a.y) / 2;
  return {
    d: `M${x1},${y1} C${x1},${ym} ${x1},${ym} ${x1 - 30},${ym} L${x2 + 50},${ym} C${x2 + 20},${ym} ${x2 + 30},${y2} ${x2},${y2}`,
    mx: (x1 - 30 + x2 + 50) / 2,
    my: ym - 6,
  };
}

export default function ArchitectureDiagram({ arch }: { arch: Architecture }) {
  const uid = useId().replace(/:/g, '');
  const [selected, setSelected] = useState<string>(arch.nodes[0]?.id ?? '');
  const [hovered, setHovered] = useState<string | null>(null);
  const focus = hovered ?? selected;

  const boxes = useMemo(() => new Map(arch.nodes.map((n) => [n.id, boxOf(n)])), [arch]);
  const cols = Math.max(...arch.nodes.map((n) => n.col)) + 1;
  const rows = Math.max(...arch.nodes.map((n) => n.row)) + 1;
  const width = PAD * 2 + (cols - 1) * CELL_W + NODE_W;
  const height = PAD * 2 + (rows - 1) * CELL_H + NODE_H;

  const linked = (e: ArchEdge) => e.from === focus || e.to === focus;
  const current = arch.nodes.find((n) => n.id === selected);

  function onKey(e: KeyboardEvent<SVGGElement>, id: string) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      setSelected(id);
    }
  }

  return (
    <figure className="arch">
      <figcaption className="arch__head">
        <strong>{arch.title}</strong>
        <span>{arch.caption}</span>
      </figcaption>

      <div className="arch__scroll">
        <svg
          className="arch__svg"
          viewBox={`0 0 ${width} ${height}`}
          style={{ minWidth: Math.min(width, 640), maxWidth: width }}
          role="group"
          aria-label={`${arch.title} — architecture diagram`}
        >
          <defs>
            <marker id={`arrow-${uid}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M0,0 L10,5 L0,10 z" className="arch__arrow" />
            </marker>
            <pattern id={`tone-${uid}`} width="6" height="6" patternUnits="userSpaceOnUse">
              <circle cx="3" cy="3" r="1" className="arch__tone" />
            </pattern>
          </defs>

          {arch.edges.map((e) => {
            const p = edgePath(boxes.get(e.from)!, boxes.get(e.to)!);
            return (
              <g key={`${e.from}-${e.to}`} className={`edge ${e.dashed ? 'edge--loop' : ''} ${linked(e) ? 'is-linked' : ''}`}>
                <path d={p.d} className="edge__line" markerEnd={`url(#arrow-${uid})`} />
                <path d={p.d} className="edge__flow" />
                {e.label && (
                  <text x={p.mx} y={p.my - 6} className="edge__label" textAnchor="middle">{e.label}</text>
                )}
              </g>
            );
          })}

          {arch.nodes.map((n) => {
            const b = boxes.get(n.id)!;
            return (
              <g
                key={n.id}
                className={`node node--${n.kind} ${selected === n.id ? 'is-selected' : ''} ${focus === n.id ? 'is-focus' : ''}`}
                transform={`translate(${b.x} ${b.y})`}
                role="button"
                tabIndex={0}
                aria-pressed={selected === n.id}
                aria-label={`${n.label}${n.sub ? ` — ${n.sub}` : ''}`}
                onClick={() => setSelected(n.id)}
                onKeyDown={(e) => onKey(e, n.id)}
                onPointerEnter={() => setHovered(n.id)}
                onPointerLeave={() => setHovered(null)}
                onFocus={() => setHovered(n.id)}
                onBlur={() => setHovered(null)}
              >
                <rect className="node__shadow" x="5" y="5" width={NODE_W} height={NODE_H} rx={n.kind === 'store' ? 18 : 3} />
                <rect className="node__box" width={NODE_W} height={NODE_H} rx={n.kind === 'store' ? 18 : 3} />
                {n.kind === 'source' && <rect className="node__tone" width={NODE_W} height={NODE_H} rx="3" fill={`url(#tone-${uid})`} />}
                <text className="node__label" x={NODE_W / 2} y={n.sub ? 27 : 37} textAnchor="middle">{n.label}</text>
                {n.sub && <text className="node__sub" x={NODE_W / 2} y="46" textAnchor="middle">{n.sub}</text>}
              </g>
            );
          })}
        </svg>
      </div>

      {current && (
        <div className="arch__detail" aria-live="polite">
          <span className={`arch__kind arch__kind--${current.kind}`}>{current.kind}</span>
          <strong>{current.label}</strong>
          <p>{current.detail}</p>
        </div>
      )}
    </figure>
  );
}
