import React from 'react';
import { Package, Coffee, Cookie, Sparkles, Utensils, Milk, Layers } from 'lucide-react';

export default function ProductImageFallback({
  category = 'Food',
  brand = '',
  productName = '',
  height = 140,
  width = '100%',
  style = {}
}) {
  // Select subtle theme color and category icon
  const getCategoryDetails = (cat) => {
    const c = (cat || '').toLowerCase();
    if (c.includes('beverage') || c.includes('drink')) {
      return { bg: '#e8f4fd', fg: '#0288d1', label: 'Beverage', icon: Coffee };
    }
    if (c.includes('biscuit') || c.includes('bakery')) {
      return { bg: '#fef7e0', fg: '#b26a00', label: 'Bakery', icon: Cookie };
    }
    if (c.includes('cereal') || c.includes('breakfast')) {
      return { bg: '#f1f8e9', fg: '#558b2f', label: 'Cereal', icon: Layers };
    }
    if (c.includes('dairy') || c.includes('milk')) {
      return { bg: '#e0f2f1', fg: '#00796b', label: 'Dairy', icon: Milk };
    }
    if (c.includes('instant') || c.includes('noodle')) {
      return { bg: '#fbe9e7', fg: '#d84315', label: 'Instant Food', icon: Utensils };
    }
    return { bg: '#f5f7f6', fg: '#2e7d32', label: category || 'Packaged Snack', icon: Package };
  };

  const details = getCategoryDetails(category);
  const IconComponent = details.icon;

  return (
    <div
      style={{
        width: width,
        height: height,
        backgroundColor: details.bg,
        borderRadius: 8,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
        overflow: 'hidden',
        border: '1px solid rgba(0, 0, 0, 0.05)',
        ...style
      }}
      title={`${productName || 'Product'} — Image unavailable`}
      aria-label="Product packaging illustration"
    >
      {/* Background vector watermark illustration */}
      <svg
        width="100%"
        height="100%"
        viewBox="0 0 200 120"
        preserveAspectRatio="none"
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          opacity: 0.12,
          pointerEvents: 'none'
        }}
      >
        <path
          d="M 20,95 L 60,35 L 140,35 L 180,95 Z"
          fill={details.fg}
        />
        <rect x="75" y="20" width="50" height="15" rx="4" fill={details.fg} />
        <line x1="45" y1="65" x2="155" y2="65" stroke={details.fg} strokeWidth="3" strokeDasharray="4 4" />
      </svg>

      {/* Center Icon and Badge */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 6,
          zIndex: 1,
          padding: '0 8px',
          textAlign: 'center'
        }}
      >
        <div
          style={{
            width: 38,
            height: 38,
            borderRadius: '50%',
            backgroundColor: '#ffffff',
            boxShadow: '0 2px 6px rgba(0,0,0,0.08)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: details.fg
          }}
        >
          <IconComponent size={20} strokeWidth={2} />
        </div>

        <span
          style={{
            fontSize: '0.68rem',
            fontWeight: 700,
            color: details.fg,
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
            background: 'rgba(255, 255, 255, 0.75)',
            padding: '2px 8px',
            borderRadius: 12
          }}
        >
          {details.label}
        </span>
      </div>
    </div>
  );
}
