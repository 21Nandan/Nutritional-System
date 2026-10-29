import React, { useState, useEffect, useMemo } from 'react';
import { X, Plus, ChevronRight, Check, AlertTriangle } from 'lucide-react';
import { useLockBodyScroll } from '../components/useLockBodyScroll';
import { apiFetch } from '../api';
import { basisLabel } from '../format';
import {
  COMPARE_METRICS, basisComparison, compareMetric, compareGrades, compareGoalMatch, allergenState, buildVerdict,
} from '../compare';

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

  const products = useMemo(() => comparedData?.products_compared || [], [comparedData]);
  const [showDifferencesOnly, setShowDifferencesOnly] = useState(false);
  const goal = comparedData?.user_goal || activeProfile?.goal || 'Balanced Choices';
  const profileAllergens = (activeProfile?.allergens_to_avoid || '').trim();

  const comparison = useMemo(() => {
    if (products.length < 2) return null;
    const basis = basisComparison(products);
    return {
      basis,
      rows: COMPARE_METRICS.map((m) => compareMetric(m, products, basis.comparable)),
      grades: compareGrades(products),
      goalMatch: compareGoalMatch(products),
      verdict: buildVerdict(products, goal, profileAllergens),
    };
  }, [products, goal, profileAllergens]);

  const visibleRows = comparison
    ? comparison.rows.filter((r) => !showDifferencesOnly || !comparison.basis.comparable || r.meaningful)
    : [];
  const hiddenCount = comparison ? comparison.rows.length - visibleRows.length : 0;

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
        <>
          <CompareVerdict verdict={comparison.verdict} />

          <div className="compare-toolbar">
            <div className="compare-toggle" role="group" aria-label="Rows to show">
              <button type="button" aria-pressed={!showDifferencesOnly} onClick={() => setShowDifferencesOnly(false)}>
                All metrics
              </button>
              <button type="button" aria-pressed={showDifferencesOnly} onClick={() => setShowDifferencesOnly(true)}>
                Differences only
              </button>
            </div>
            <ul className="compare-legend" aria-label="Legend">
              <li><span className="compare-best"><Check size={12} aria-hidden="true" /> Lowest / Highest</span> better value in this comparison</li>
              <li><span className="compare-concern"><AlertTriangle size={12} aria-hidden="true" /> Above limit</span> over the category limit used for grades</li>
            </ul>
          </div>
          {comparison.basis.reason && <p className="compare-note" role="note">{comparison.basis.reason}</p>}
          {showDifferencesOnly && comparison.basis.comparable && (
            <p className="compare-note" role="status">
              {hiddenCount === 0
                ? 'Every nutrient differs meaningfully, so all rows are shown.'
                : `${hiddenCount} nutrient ${hiddenCount === 1 ? 'row' : 'rows'} with no meaningful difference hidden.`}
            </p>
          )}

          <div className="responsive-table-wrapper compare-table-wrapper">
            <table className="compare-table" style={{ minWidth: 200 + products.length * 170 }}>
              <caption className="sr-only">Nutrition comparison of {products.length} products for your goal, {goal}</caption>
              <thead>
                <tr>
                  <th scope="col" className="compare-label-col">Nutritional Metric</th>
                  {products.map(p => (
                    <th key={p.product_id} scope="col">
                      <div className="compare-product-head">
                        {(p.image_small_url || p.image_url) && (
                          <img
                            src={p.image_small_url || p.image_url}
                            alt=""
                            onError={(e) => { e.currentTarget.style.display = 'none'; }}
                          />
                        )}
                        <div style={{ minWidth: 0 }}>
                          <span className="compare-brand">{p.brand}</span>
                          <span className="compare-name">{p.product_name}</span>
                          <span className="badge badge-neutral" style={{ fontSize: '0.68rem' }}>{p.category}</span>
                          <span className="compare-basis">Values {basisLabel(p.measurement_basis)}</span>
                        </div>
                        <button
                          type="button"
                          className="compare-remove"
                          onClick={() => removeProduct(p.product_id)}
                          aria-label={`Remove ${p.product_name} from comparison`}
                          title="Remove"
                        >
                          <X size={16} aria-hidden="true" />
                        </button>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th scope="row" className="compare-label-col">
                    General Nutrition Grade
                    <span className="compare-help">A (best) to E, against limits for the product&apos;s category</span>
                  </th>
                  {comparison.grades.cells.map((cell, i) => (
                    <td key={products[i].product_id}>
                      <span className="compare-cell">
                        <span className={`grade-badge grade-${cell.grade === 'N/A' ? 'NA' : cell.grade}`} style={{ width: 28, height: 28, fontSize: '1.1rem' }}>
                          {cell.grade}
                        </span>
                        {cell.isBest && <span className="compare-best"><Check size={12} aria-hidden="true" /> Best grade</span>}
                      </span>
                    </td>
                  ))}
                </tr>
                {comparison.grades.note && (
                  <tr className="compare-note-row">
                    <td colSpan={products.length + 1}>{comparison.grades.note}</td>
                  </tr>
                )}

                <tr className="compare-goal-row">
                  <th scope="row" className="compare-label-col">
                    Goal Match ({goal})
                    <span className="compare-help">1–100 fit with your goal; an allergen from your profile sets it to 0</span>
                  </th>
                  {products.map((p, i) => (
                    <td key={p.product_id}>
                      <span className="compare-cell">
                        <span className="compare-score" style={{ color: p.has_allergen_conflict ? '#c62828' : 'var(--color-primary)' }}>
                          {p.personalized_score != null ? `${p.personalized_score}/100` : 'N/A'}
                        </span>
                        {comparison.goalMatch.cells[i].isBest && <span className="compare-best"><Check size={12} aria-hidden="true" /> Higher match</span>}
                      </span>
                      {p.personalized_score == null && <span className="compare-sub">Incomplete data</span>}
                      {p.has_allergen_conflict && <span className="compare-sub" style={{ color: '#c62828', fontWeight: 700 }}>Allergen warning overrides score</span>}
                    </td>
                  ))}
                </tr>

                {visibleRows.map(({ metric, cells }) => (
                  <tr key={metric.key}>
                    <th scope="row" className="compare-label-col">
                      {metric.label}
                      {metric.note && <span className="compare-help">{metric.note}</span>}
                    </th>
                    {cells.map((cell, i) => (
                      <td key={products[i].product_id}>
                        <span className="compare-cell">
                          <span className={cell.isConcern ? 'compare-value is-concern' : cell.isBest ? 'compare-value is-best' : cell.missing ? 'compare-value is-missing' : 'compare-value'}>
                            {cell.display}
                          </span>
                          {cell.isBest && <span className="compare-best"><Check size={12} aria-hidden="true" /> {cell.bestLabel}</span>}
                          {cell.isConcern && (
                            <span className="compare-concern" title={`Above the ${cell.concernLimit} limit for this category`}>
                              <AlertTriangle size={12} aria-hidden="true" /> Above limit
                            </span>
                          )}
                        </span>
                      </td>
                    ))}
                  </tr>
                ))}

                <tr>
                  <th scope="row" className="compare-label-col">Allergen Alerts</th>
                  {products.map(p => {
                    const state = allergenState(p, profileAllergens);
                    return (
                      <td key={p.product_id} className="compare-allergen">
                        {state === 'conflict' && (
                          <span style={{ color: '#c62828', fontWeight: 700 }}>
                            <AlertTriangle size={13} aria-hidden="true" /> Contains your allergen: {p.allergen_conflicts?.map(c => c.allergen).join(', ')}
                          </span>
                        )}
                        {state === 'unknown' && (
                          <span className="compare-concern-text">
                            <AlertTriangle size={13} aria-hidden="true" /> Allergen information not stated: check the pack
                          </span>
                        )}
                        {state === 'none-found' && (
                          <span style={{ color: 'var(--color-success)' }}>
                            <Check size={13} aria-hidden="true" /> None of your allergens found in the label text
                          </span>
                        )}
                        {state === 'no-profile-allergens' && (
                          <span style={{ color: 'var(--color-text-muted)' }}>No allergens set in your profile</span>
                        )}
                      </td>
                    );
                  })}
                </tr>

                <tr>
                  <th scope="row" className="compare-label-col">Full Assessment</th>
                  {products.map(p => (
                    <td key={p.product_id}>
                      <button
                        className="btn-primary"
                        style={{ padding: '6px 14px', fontSize: '0.8rem', width: '100%', justifyContent: 'center' }}
                        onClick={() => onSelectProduct(p.product_id)}
                      >
                        <span>View Details</span>
                        <ChevronRight size={14} aria-hidden="true" />
                      </button>
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Add Product Modal */}
      {showSearchModal && (
        <div className="modal-overlay" onClick={() => setShowSearchModal(false)}>
          <div className="modal-card" onClick={e => e.stopPropagation()} style={{ maxWidth: 520 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <h3 style={{ fontSize: '1.2rem', margin: 0 }}>Add Product to Comparison</h3>
              <button type="button" onClick={() => setShowSearchModal(false)} aria-label="Close"><X size={18} aria-hidden="true" /></button>
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
                <button
                  type="button"
                  key={p.product_id}
                  onClick={() => addProductToCompare(p.product_id)}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    font: 'inherit',
                    color: 'inherit',
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
                  <Plus size={16} color="var(--color-accent)" aria-hidden="true" />
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function CompareVerdict({ verdict }) {
  const { headline, advantages, tradeoffs, subject, comparedWith, tie, notes } = verdict;
  return (
    <section className="compare-verdict" aria-labelledby="compare-verdict-title">
      <h2 id="compare-verdict-title">Verdict for your goal</h2>
      <p className="compare-verdict-headline">{headline}</p>
      {subject && comparedWith && (advantages.length > 0 || tradeoffs.length > 0) && (
        <p>
          {tie ? `${subject.product_name} has ` : 'It has '}
          {advantages.length > 0 ? advantages.join(', ') : 'no clear nutrient advantage'}
          {tradeoffs.length > 0 && <>, but {tradeoffs.join(', ')}</>}
          {` compared with ${comparedWith.product_name}.`}
        </p>
      )}
      {notes.map((n) => <p key={n} className="compare-verdict-note">{n}</p>)}
      <p className="compare-verdict-note">Goal Match reflects your selected goal, not overall healthiness. Always read the pack.</p>
    </section>
  );
}
