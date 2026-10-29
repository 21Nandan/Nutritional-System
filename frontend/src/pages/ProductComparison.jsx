import React, { useState, useEffect } from 'react';
import { X, Plus, ChevronRight } from 'lucide-react';
import { useLockBodyScroll } from '../components/useLockBodyScroll';
import { apiFetch } from '../api';
import { basisLabel } from '../format';

export default function ProductComparison({ initialProductIds = [], onSelectProduct, activeProfile }) {
  const [selectedIds, setSelectedIds] = useState(
    initialProductIds.length >= 2 ? initialProductIds : ['IND_PKG_001', 'IND_PKG_002']
  );
  const [comparedData, setComparedData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [showSearchModal, setShowSearchModal] = useState(false);

  useLockBodyScroll(showSearchModal);

  const [compareError, setCompareError] = useState(null);
  const [searchError, setSearchError] = useState(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    if (selectedIds.length < 2) return undefined;
    const controller = new AbortController();
    setLoading(true);
    setCompareError(null);
    apiFetch(`/api/compare?ids=${selectedIds.map(encodeURIComponent).join(',')}`, { signal: controller.signal })
      .then((data) => {
        setComparedData(data);
        setLoading(false);
      })
      .catch((err) => {
        if (err.name === 'AbortError') return;
        setCompareError(err.message);
        setLoading(false);
      });
    return () => controller.abort();
  }, [selectedIds, activeProfile, reloadToken]);

  const handleSearch = (q) => {
    setSearchQuery(q);
    setSearchError(null);
    if (!q.trim()) {
      setSearchResults([]);
      return;
    }
    apiFetch(`/api/products?query=${encodeURIComponent(q)}&limit=12`)
      .then((data) => setSearchResults(data.products))
      .catch((err) => {
        setSearchResults([]);
        setSearchError(err.message);
      });
  };

  const addProductToCompare = (pid) => {
    if (!selectedIds.includes(pid) && selectedIds.length < 4) {
      setSelectedIds([...selectedIds, pid]);
    }
    setShowSearchModal(false);
    setSearchQuery('');
    setSearchResults([]);
  };

  const removeProduct = (pid) => {
    if (selectedIds.length > 2) {
      setSelectedIds(selectedIds.filter(id => id !== pid));
    } else {
      window.alert('Please keep at least 2 products to compare.');
    }
  };

  const products = comparedData?.products_compared || [];

  return (
    <div className="product-comparison-page">
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: '2.2rem', color: 'var(--color-primary)', marginBottom: 8 }}>
          Product Comparison Matrix
        </h1>
        <p style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem' }}>
          Side-by-side nutrition values, per 100 g for foods and per 100 ml for drinks (shown under each product). Personal scores use your goal: <strong>{activeProfile?.goal || 'Balanced Choices'}</strong>.
        </p>
      </div>

      {/* Control bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
          Active Comparison Matrix ({products.length} items selected)
        </div>
        {selectedIds.length < 4 && (
          <button 
            className="btn-secondary" 
            onClick={() => setShowSearchModal(true)}
            style={{ padding: '8px 14px', fontSize: '0.85rem' }}
          >
            <Plus size={16} />
            <span>Add Product to Compare</span>
          </button>
        )}
      </div>

      {loading ? (
        <div style={{ padding: '60px 0', textAlign: 'center', color: 'var(--color-text-muted)' }}>
          Comparing products...
        </div>
      ) : compareError ? (
        <div role="alert" style={{ textAlign: 'center', padding: '48px 0', color: '#c62828' }}>
          <p style={{ marginBottom: 12 }}>We couldn&apos;t compare these products: {compareError}</p>
          <button className="btn-primary" onClick={() => setReloadToken((t) => t + 1)}>Try again</button>
        </div>
      ) : products.length < 2 ? (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          Select at least 2 items to compare.
        </div>
      ) : (
        <div className="responsive-table-wrapper" style={{ background: '#fff', borderRadius: 'var(--radius-lg)', border: '1px solid var(--color-border)', boxShadow: 'var(--shadow-sm)' }}>
          <table style={{ width: '100%', minWidth: 620, borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.88rem' }}>
            <thead>
              <tr style={{ background: 'var(--color-surface-alt)', borderBottom: '2px solid var(--color-border)' }}>
                <th style={{ padding: '16px 20px', width: '220px', fontWeight: 800, color: 'var(--color-primary)' }}>
                  Nutritional Metric
                </th>
                {products.map(p => (
                  <th key={p.product_id} style={{ padding: '16px 20px', minWidth: '220px', verticalAlign: 'top' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
                      <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                        {(p.image_small_url || p.image_url) && (
                          <img
                            src={p.image_small_url || p.image_url}
                            alt={p.product_name}
                            onError={(e) => { e.currentTarget.style.display = 'none'; }}
                            style={{
                              width: 44,
                              height: 44,
                              objectFit: 'contain',
                              borderRadius: 6,
                              background: '#f8f9fa',
                              border: '1px solid var(--color-border)',
                              padding: 2,
                              flexShrink: 0
                            }}
                          />
                        )}
                        <div>
                          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--color-text-subtle)', textTransform: 'uppercase' }}>
                            {p.brand}
                          </span>
                          <h4 style={{ fontSize: '1rem', color: 'var(--color-primary)', margin: '2px 0 6px' }}>
                            {p.product_name}
                          </h4>
                          <span className="badge badge-neutral" style={{ fontSize: '0.68rem' }}>
                            {p.category}
                          </span>
                          <span style={{ display: 'block', fontSize: '0.7rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
                            Values {basisLabel(p.measurement_basis)}
                          </span>
                        </div>
                      </div>
                      <button 
                        onClick={() => removeProduct(p.product_id)} 
                        style={{ color: 'var(--color-text-subtle)', padding: 4 }}
                        title="Remove"
                      >
                        <X size={16} />
                      </button>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {/* Row 1: General Grade */}
              <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                <td style={tdLabelStyle}>General Nutrition Grade</td>
                {products.map(p => (
                  <td key={p.product_id} style={tdValStyle}>
                    <span className={`grade-badge grade-${p.general_grade || 'NA'}`} style={{ width: 28, height: 28, fontSize: '1.1rem' }}>
                      {p.general_grade || 'NA'}
                    </span>
                  </td>
                ))}
              </tr>

              {/* Row 2: Personalized Goal Match */}
              <tr style={{ borderBottom: '1px solid var(--color-border)', background: 'var(--color-accent-subtle)' }}>
                <td style={{ ...tdLabelStyle, color: 'var(--color-primary)' }}>
                  Goal Match ({activeProfile?.goal || 'Balanced'})
                </td>
                {products.map(p => (
                  <td key={p.product_id} style={tdValStyle}>
                    <div style={{ fontSize: '1.3rem', fontWeight: 800, color: p.has_allergen_conflict ? '#c62828' : 'var(--color-primary)' }}>
                      {p.personalized_score != null ? `${p.personalized_score}/100` : 'N/A'}
                    </div>
                    {p.personalized_score == null && (
                      <span style={{ fontSize: '0.7rem', color: 'var(--color-text-subtle)', fontWeight: 600 }}>
                        Incomplete Data
                      </span>
                    )}
                    {p.has_allergen_conflict && (
                      <span style={{ fontSize: '0.7rem', color: '#c62828', fontWeight: 700 }}>
                        Allergen Warning Overrides Score
                      </span>
                    )}
                  </td>
                ))}
              </tr>

              {/* Row 3: Energy */}
              <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                <td style={tdLabelStyle}>Energy (kcal per 100g)</td>
                {products.map(p => (
                  <td key={p.product_id} style={tdValStyle}>
                    <strong>{p.energy_kcal != null ? `${p.energy_kcal} kcal` : 'Missing'}</strong>
                  </td>
                ))}
              </tr>

              {/* Row 4: Total Sugars */}
              <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                <td style={tdLabelStyle}>Total Sugars</td>
                {products.map(p => (
                  <td key={p.product_id} style={tdValStyle}>
                    <span style={{ color: p.sugars_g > 15 ? '#c62828' : 'inherit', fontWeight: p.sugars_g > 15 ? 700 : 500 }}>
                      {p.sugars_g != null ? `${p.sugars_g}g` : 'Missing'}
                    </span>
                  </td>
                ))}
              </tr>

              {/* Row 5: Sodium */}
              <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                <td style={tdLabelStyle}>Sodium</td>
                {products.map(p => (
                  <td key={p.product_id} style={tdValStyle}>
                    <span style={{ color: p.sodium_mg > 600 ? '#e65100' : 'inherit', fontWeight: p.sodium_mg > 600 ? 700 : 500 }}>
                      {p.sodium_mg != null ? `${Math.round(p.sodium_mg)}mg` : 'Missing'}
                    </span>
                  </td>
                ))}
              </tr>

              {/* Row 6: Protein */}
              <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                <td style={tdLabelStyle}>Protein</td>
                {products.map(p => (
                  <td key={p.product_id} style={tdValStyle}>
                    <span style={{ color: p.protein_g >= 10 ? '#2e7d32' : 'inherit', fontWeight: p.protein_g >= 10 ? 700 : 500 }}>
                      {p.protein_g != null ? `${p.protein_g}g` : 'Missing'}
                    </span>
                  </td>
                ))}
              </tr>

              {/* Row 7: Saturated Fat */}
              <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                <td style={tdLabelStyle}>Saturated Fat</td>
                {products.map(p => (
                  <td key={p.product_id} style={tdValStyle}>
                    <span style={{ color: p.saturated_fat_g > 5 ? '#e65100' : 'inherit' }}>
                      {p.saturated_fat_g != null ? `${p.saturated_fat_g}g` : 'Missing'}
                    </span>
                  </td>
                ))}
              </tr>

              {/* Row 8: Dietary Fibre */}
              <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                <td style={tdLabelStyle}>Dietary Fibre</td>
                {products.map(p => (
                  <td key={p.product_id} style={tdValStyle}>
                    <span style={{ color: p.dietary_fibre_g >= 6 ? '#2e7d32' : 'inherit', fontWeight: p.dietary_fibre_g >= 6 ? 700 : 500 }}>
                      {p.dietary_fibre_g != null ? `${p.dietary_fibre_g}g` : 'Missing'}
                    </span>
                  </td>
                ))}
              </tr>

              {/* Row 9: Allergen Warnings */}
              <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                <td style={tdLabelStyle}>Allergen Alerts</td>
                {products.map(p => (
                  <td key={p.product_id} style={tdValStyle}>
                    {p.has_allergen_conflict ? (
                      <span style={{ color: '#c62828', fontWeight: 700, fontSize: '0.78rem' }}>
                        ⚠️ Conflict: {p.allergen_conflicts?.map(c => c.allergen).join(', ')}
                      </span>
                    ) : (
                      <span style={{ color: '#2e7d32', fontSize: '0.78rem' }}>
                        ✓ No allergen alerts
                      </span>
                    )}
                  </td>
                ))}
              </tr>

              {/* Action Row */}
              <tr>
                <td style={tdLabelStyle}>Full Assessment</td>
                {products.map(p => (
                  <td key={p.product_id} style={{ padding: '16px 20px' }}>
                    <button
                      className="btn-primary"
                      style={{ padding: '6px 14px', fontSize: '0.8rem', width: '100%', justifyContent: 'center' }}
                      onClick={() => onSelectProduct(p.product_id)}
                    >
                      <span>View Details</span>
                      <ChevronRight size={14} />
                    </button>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {/* Add Product Modal */}
      {showSearchModal && (
        <div className="modal-overlay" onClick={() => setShowSearchModal(false)}>
          <div className="modal-card" onClick={e => e.stopPropagation()} style={{ maxWidth: 520 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <h3 style={{ fontSize: '1.2rem', margin: 0 }}>Add Product to Comparison</h3>
              <button onClick={() => setShowSearchModal(false)}><X size={18} /></button>
            </div>
            <input
              type="text"
              autoFocus
              placeholder="Search product name or brand..."
              value={searchQuery}
              onChange={e => handleSearch(e.target.value)}
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: 8,
                border: '1px solid var(--color-border)',
                fontSize: '0.9rem',
                marginBottom: 16
              }}
            />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {searchError && <p role="alert" style={{ color: '#c62828', fontSize: '0.85rem' }}>{searchError}</p>}
              {searchResults.map(p => (
                <div 
                  key={p.product_id}
                  onClick={() => addProductToCompare(p.product_id)}
                  style={{
                    padding: '10px 12px',
                    borderRadius: 6,
                    border: '1px solid var(--color-border)',
                    cursor: 'pointer',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: '#fff'
                  }}
                >
                  <div>
                    <span style={{ fontSize: '0.72rem', color: 'var(--color-text-subtle)' }}>{p.brand}</span>
                    <div style={{ fontWeight: 600, fontSize: '0.88rem' }}>{p.product_name}</div>
                  </div>
                  <Plus size={16} color="var(--color-accent)" />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const tdLabelStyle = {
  padding: '14px 20px',
  fontWeight: 700,
  color: 'var(--color-text-muted)',
  fontSize: '0.85rem'
};

const tdValStyle = {
  padding: '14px 20px',
  fontSize: '0.88rem'
};
