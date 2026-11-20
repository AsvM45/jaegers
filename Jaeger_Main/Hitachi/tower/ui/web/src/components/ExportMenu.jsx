// One Export button with a menu of formats: options = [[value, name, description], ...].
// Arrow keys move, Enter picks, Esc or a click outside closes.
import { useEffect, useRef, useState } from "react";
import { Icon } from "../lib/icons.jsx";

export function ExportMenu({ label, options, onPick, disabled }) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const wrap = useRef(null), button = useRef(null), menu = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const away = (e) => { if (!wrap.current?.contains(e.target)) setOpen(false); };
    document.addEventListener("pointerdown", away);
    menu.current?.focus();
    return () => document.removeEventListener("pointerdown", away);
  }, [open]);

  const pick = (value) => { setOpen(false); button.current?.focus(); onPick(value); };
  const onKey = (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => (a + 1) % options.length); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => (a - 1 + options.length) % options.length); }
    else if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(options[active][0]); }
    else if (e.key === "Escape" || e.key === "Tab") { setOpen(false); button.current?.focus(); }
  };

  return (
    <div className={`xm${open ? " open" : ""}`} ref={wrap}>
      <button type="button" ref={button} className="btn" aria-haspopup="menu" aria-expanded={open} disabled={disabled}
        onClick={() => { setActive(0); setOpen((o) => !o); }}
        onKeyDown={(e) => { if (e.key === "ArrowDown") { e.preventDefault(); setActive(0); setOpen(true); } }}>
        <Icon name="download" />{label}<span className="xm-chev" aria-hidden="true"><Icon name="chevron" /></span>
      </button>
      {open && (
        <div className="xm-menu" role="menu" ref={menu} tabIndex={-1} onKeyDown={onKey} aria-label={label}>
          {options.map(([value, name, about], i) => (
            <div key={value} role="menuitem" className={`xm-item${i === active ? " active" : ""}`}
              onPointerMove={() => setActive(i)} onClick={() => pick(value)}>
              <span className="xm-ico" aria-hidden="true"><Icon name="doc" /></span>
              <span className="xm-text"><b>{name}</b><small>{about}</small></span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
