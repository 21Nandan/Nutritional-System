import React from 'react';
import { ChevronDown } from 'lucide-react';

// Shared expand/collapse pieces. The panel animates its height with a CSS grid transition and
// stays in the page when closed (hidden from assistive technology), so aria-controls always
// points at a real element.

export function Chevron({ open, size = 16 }) {
  return <ChevronDown size={size} className="chevron" data-open={open} aria-hidden="true" />;
}

export function Collapse({ id, open, children }) {
  return (
    <div id={id} className="collapse" data-open={open} aria-hidden={!open} inert={!open}>
      <div className="collapse-inner">{children}</div>
    </div>
  );
}
