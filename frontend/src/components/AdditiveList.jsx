import React, { useId, useState } from 'react';
import { Chevron, Collapse } from './Expandable';

// Additives found in the ingredient text. Each box shows the INS number, name and category;
// its chevron reveals the existing regulatory note. Boxes open independently.
export default function AdditiveList({ additives }) {
  const baseId = useId();
  const [open, setOpen] = useState(() => new Set());

  const toggle = (code) => setOpen((prev) => {
    const next = new Set(prev);
    if (next.has(code)) next.delete(code);
    else next.add(code);
    return next;
  });

  return (
    <ul className="additive-list">
      {additives.map((add, i) => {
        const isOpen = open.has(add.code);
        const panelId = `${baseId}-additive-${i}`;
        return (
          <li key={add.code} className="additive-item" data-open={isOpen}>
            <button
              type="button"
              className="additive-toggle"
              aria-expanded={isOpen}
              aria-controls={panelId}
              onClick={() => toggle(add.code)}
            >
              <span className="additive-code">{add.code}</span>
              <span className="additive-text">
                <span className="additive-name">{add.name}</span>
                <span className="additive-class">{add.functional_class}</span>
              </span>
              <Chevron open={isOpen} size={15} />
            </button>
            <Collapse id={panelId} open={isOpen}>
              <p className="additive-note">
                {add.regulatory_context}
                {add.authority && <span className="additive-authority">Reference: {add.authority}</span>}
              </p>
            </Collapse>
          </li>
        );
      })}
    </ul>
  );
}
