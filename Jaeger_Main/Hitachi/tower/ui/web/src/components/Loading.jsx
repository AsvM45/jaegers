// Loading states: skeletons shaped like the content that is coming, with a soft shimmer
// (still when Settings → Motion is Reduced or the system asks for reduced motion).
import { tr } from "../lib/i18n.js";

export function Skeleton({ w = "100%", h = 12, r = 8, style }) {
  return <span className="sk" style={{ width: w, height: h, borderRadius: r, ...style }} aria-hidden="true" />;
}

// A few lines of text, the last one shorter.
export function SkeletonLines({ n = 3 }) {
  return (
    <div className="sk-lines" role="status" aria-label={tr("Loading…")}>
      {Array.from({ length: n }, (_, i) => <Skeleton key={i} w={i === n - 1 ? "62%" : "100%"} />)}
    </div>
  );
}

// A whole page while its first data arrives: title bar, three tiles, two cards.
export function PageSkeleton() {
  return (
    <div className="sk-page" role="status" aria-live="polite">
      <span className="sr-only">{tr("Loading…")}</span>
      <div className="topbar sk-topbar">
        <div className="sk-col"><Skeleton w={180} h={22} /><Skeleton w={300} h={11} /></div>
        <Skeleton w="38%" h={40} r={14} />
      </div>
      <div className="grid g3" style={{ marginTop: 20 }}>
        {[0, 1, 2].map((i) => (
          <div className="card sk-tile" key={i}>
            <div className="sk-col"><Skeleton w={110} h={9} /><Skeleton w={64} h={26} /><Skeleton w={90} h={18} r={99} /></div>
            <Skeleton w={46} h={46} r={14} />
          </div>
        ))}
      </div>
      <div className="grid g-hero two" style={{ marginTop: 20 }}>
        <div className="card sk-card"><Skeleton w="40%" h={16} /><SkeletonLines n={4} /><Skeleton w={150} h={30} r={99} /></div>
        <div className="card sk-card sk-center"><Skeleton w={150} h={150} r={999} /><Skeleton w="60%" h={11} /></div>
      </div>
    </div>
  );
}

// A spinner ring and a line of status, for something that loads in one piece (the orb graph).
export function Loader({ title, detail }) {
  return (
    <div className="loader" role="status" aria-live="polite">
      <span className="loader-ring" aria-hidden="true"><i /></span>
      <b>{title}</b>
      {detail && <span className="loader-detail">{detail}</span>}
      <span className="loader-bar" aria-hidden="true"><i /></span>
    </div>
  );
}
