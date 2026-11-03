import type { Diagram as Spec, Edge, Node } from "../api";

const W = 168, H = 56, GX = 64, GY = 22;

/** Layered left-to-right layout: each node's column is its longest path from a source. Cycles are cut. */
export function layout(nodes: Node[], edges: Edge[]) {
  const ids = new Set(nodes.map((n) => n.id));
  const valid = edges.filter((e) => ids.has(e.source) && ids.has(e.target) && e.source !== e.target);
  const depth = new Map(nodes.map((n) => [n.id, 0]));
  for (let pass = 0; pass < nodes.length; pass++) {
    let changed = false;
    for (const e of valid) {
      const next = depth.get(e.source)! + 1;
      if (next > depth.get(e.target)! && next < nodes.length) {
        depth.set(e.target, next);
        changed = true;
      }
    }
    if (!changed) break;
  }
  const columns: Node[][] = [];
  for (const n of nodes) (columns[depth.get(n.id)!] ??= []).push(n);
  const filled = columns.filter(Boolean);
  const tallest = Math.max(...filled.map((c) => c.length));
  const pos = new Map<string, { x: number; y: number }>();
  filled.forEach((col, ci) => {
    const offset = ((tallest - col.length) * (H + GY)) / 2;
    col.forEach((n, ri) => pos.set(n.id, { x: ci * (W + GX), y: offset + ri * (H + GY) }));
  });
  return {
    pos,
    edges: valid,
    width: filled.length * (W + GX) - GX,
    height: tallest * (H + GY) - GY,
  };
}

function Flow({ spec }: { spec: Spec }) {
  const { pos, edges, width, height } = layout(spec.nodes, spec.edges);
  const pad = 14;
  return (
    <svg
      className="flow"
      viewBox={`${-pad} ${-pad} ${width + pad * 2} ${height + pad * 2}`}
      style={{ maxWidth: width + pad * 2 }}
      role="img"
      aria-label={spec.title}
    >
      <defs>
        <marker id="arr" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
          <path d="M0 0L8 4L0 8z" className="arrowhead" />
        </marker>
      </defs>
      {edges.map((e, i) => {
        const a = pos.get(e.source)!, b = pos.get(e.target)!;
        const forward = b.x > a.x;
        const x1 = forward ? a.x + W : a.x + W / 2, y1 = forward ? a.y + H / 2 : a.y + H;
        const x2 = forward ? b.x : b.x + W / 2, y2 = forward ? b.y + H / 2 : b.y;
        const mx = (x1 + x2) / 2;
        const d = forward ? `M${x1} ${y1} C${mx} ${y1} ${mx} ${y2} ${x2 - 2} ${y2}` : `M${x1} ${y1} L${x2} ${y2 - 2}`;
        return (
          <g key={i} className="edge">
            <path d={d} markerEnd="url(#arr)" style={{ animationDelay: `${i * 90}ms` }} />
            {e.label && (
              <text x={mx} y={(y1 + y2) / 2 - 6}>
                {e.label}
              </text>
            )}
          </g>
        );
      })}
      {spec.nodes.map((n, i) => {
        const p = pos.get(n.id)!;
        return (
          <g key={n.id} className="node" transform={`translate(${p.x} ${p.y})`} style={{ animationDelay: `${i * 70}ms` }}>
            <rect width={W} height={H} rx="14" />
            <text x={W / 2} y={n.detail ? 24 : 32} className="label">
              {n.label}
            </text>
            {n.detail && (
              <text x={W / 2} y={41} className="detail">
                {n.detail.length > 30 ? `${n.detail.slice(0, 29)}…` : n.detail}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

function Compare({ spec }: { spec: Spec }) {
  return (
    <div className="compare" role="table" aria-label={spec.title}>
      <div className="row head" role="row">
        <span />
        <b>{spec.left_title}</b>
        <b>{spec.right_title}</b>
      </div>
      {spec.rows.map((r) => (
        <div className="row" role="row" key={r.label}>
          <span>{r.label}</span>
          <p>{r.left}</p>
          <p>{r.right}</p>
        </div>
      ))}
    </div>
  );
}

export function Diagram({ spec }: { spec: Spec }) {
  const usable = spec.kind === "compare" ? spec.rows.length > 0 : spec.nodes.length > 1;
  if (!usable) return null;
  return (
    <figure className="diagram">
      {spec.kind === "compare" ? <Compare spec={spec} /> : <Flow spec={spec} />}
      <figcaption>{spec.title}</figcaption>
    </figure>
  );
}
