import React, { useState, useEffect, useMemo, useId } from 'react';
import { Chevron, Collapse } from '../components/Expandable';
import { X, Plus, ChevronRight, Check, AlertTriangle } from 'lucide-react';
import { useLockBodyScroll } from '../components/useLockBodyScroll';
import { apiFetch } from '../api';
import { basisLabel } from '../format';
import { GradeBadge, GoalMatchMeter } from '../components/ScoreDisplay';
import { loadSavedProducts } from '../storage';
import {
  COMPARE_METRICS, basisComparison, compareMetric, compareGrades, compareGoalMatch, allergenState, buildVerdict, relativeScores,
} from '../compare';

export default function ProductComparison({ productIds = [], onChangeIds, onSelectProduct, activeProfile }) {
  const selectedIds = productIds;
  const [comparedData, setComparedData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [showSearchModal, setShowSearchModal] = useState(false);

  useLockBodyScroll(showSearchModal);

  // Saved products the compare API can load (custom scans have no server record), re-read on open.
  const savedForCompare = useMemo(
    () => (showSearchModal ? loadSavedProducts().filter((p) => !p.is_custom && !p.product_id.startsWith('CUSTOM')) : []),
    [showSearchModal],
  );
  const savedNotSelected = savedForCompare.filter((p) => !selectedIds.includes(p.product_id));
  // Products ticked in the dialog, added together; at most 4 products are compared.
  const [picked, setPicked] = useState([]);
  const room = 4 - selectedIds.length;

  const [compareError, setCompareError] = useState(null);
  const [searchError, setSearchError] = useState(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    if (selectedIds.length === 0) {
      setComparedData(null);
      return undefined;
    }
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

  const closeSearchModal = () => {
    setShowSearchModal(false);
    setPicked([]);
    setSearchQuery('');
    setSearchResults([]);
  };

  const togglePick = (pid) => {
    setPicked((prev) => {
      if (prev.includes(pid)) return prev.filter((id) => id !== pid);
      return prev.length < room ? [...prev, pid] : prev;
    });
  };

  const pickAllSaved = () => {
    setPicked((prev) => {
      const extra = savedNotSelected.map((p) => p.product_id).filter((id) => !prev.includes(id));
      return [...prev, ...extra].slice(0, room);
    });
  };

  const addPickedToCompare = () => {
    onChangeIds([...selectedIds, ...picked.filter((id) => !selectedIds.includes(id))].slice(0, 4));
    closeSearchModal();
  };

  const removeProduct = (pid) => {
    onChangeIds(selectedIds.filter((id) => id !== pid));
  };
  const removeUnavailable = () => {
    const bad = new Set(unavailable.map((u) => u.product_id));
    onChangeIds(selectedIds.filter((id) => !bad.has(id)));
  };

  const products = useMemo(() => comparedData?.products_compared || [], [comparedData]);
  const unavailable = comparedData?.unavailable || [];
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
      relative: relativeScores(products, basis.comparable),
      verdict: buildVerdict(products, goal, profileAllergens),
    };
  }, [products, goal, profileAllergens]);

  // Patterns across the products, a plain explanation and a swap idea for the lowest-priority product,
  // loaded after the table. Each part is left out if it can't be loaded.
  const [insight, setInsight] = useState(null);
  useEffect(() => {
    setInsight(null);
    if (!comparison || products.length < 2) return undefined;
    const controller = new AbortController();
    const ids = products.map((p) => p.product_id);
    const priority = Object.fromEntries(
      products.map((p, i) => [p.product_id, comparison.relative.cells[i]?.rank]).filter(([, r]) => r != null),
    );
    const ranked = products
      .map((p, i) => ({ p, rank: comparison.relative.cells[i]?.rank ?? 0 }))
      .filter((r) => !r.p.has_allergen_conflict)
      .sort((a, b) => b.rank - a.rank);
    const worst = comparison.relative.available && ranked.length && ranked[0].rank > 1 ? ranked[0].p : null;
    Promise.all([
      apiFetch('/api/compare/explain', { method: 'POST', body: { product_ids: ids, priority }, signal: controller.signal }).catch(() => null),
      worst
        ? apiFetch(`/api/alternatives/${encodeURIComponent(worst.product_id)}?limit=1`, { signal: controller.signal }).catch(() => null)
        : Promise.resolve(null),
    ]).then(([explained, alts]) => {
      if (controller.signal.aborted) return;
      const swap = alts?.alternatives?.find((a) => !ids.includes(a.product_id));
      setInsight({
        explanation: explained?.explanation || null,
        patterns: explained?.patterns || [],
        swap: swap && worst ? { from: worst.product_name, to: swap } : null,
      });
    });
    return () => controller.abort();
  }, [comparison, products]);

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
        {/* The empty state has its own add button, so this one shows only beside a comparison */}
        {selectedIds.length < 4 && products.length >= 2 && !loading && (
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

      {!loading && unavailable.length > 0 && (
        <div className="compare-unavailable" role="alert">
          <p className="compare-unavailable-title">
            <AlertTriangle size={16} aria-hidden="true" />
            {unavailable.length === 1 ? '1 selected product couldn\u2019t be loaded' : `${unavailable.length} selected products couldn\u2019t be loaded`}
          </p>
          <ul>
            {unavailable.map((u) => (
              <li key={u.product_id}>
                <span><strong>{u.product_id}</strong>: {u.message}</span>
                <button type="button" className="btn-secondary btn-compact" onClick={() => removeProduct(u.product_id)}>Remove</button>
              </li>
            ))}
          </ul>
          <div className="compare-unavailable-actions">
            <button type="button" className="btn-primary btn-compact" onClick={removeUnavailable}>Remove unavailable products</button>
            {unavailable.some((u) => u.retryable) && (
              <button type="button" className="btn-secondary btn-compact" onClick={() => setReloadToken((t) => t + 1)}>Try again</button>
            )}
          </div>
        </div>
      )}

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
        <div className="compare-empty">
          {products.length === 1 ? (
            <>
              <p><strong>{products[0].product_name}</strong> is selected. Add at least one more product to compare.</p>
              <button type="button" className="btn-secondary btn-compact" onClick={() => removeProduct(products[0].product_id)}>
                Remove {products[0].product_name}
              </button>
            </>
          ) : (
            <p>No products selected yet. Add two to four products to compare them side by side.</p>
          )}
          <button type="button" className="btn-primary btn-compact" onClick={() => setShowSearchModal(true)}>
            <Plus size={16} aria-hidden="true" /> <span>Add Product to Compare</span>
          </button>
        </div>
      ) : (
        <>
          <CompareVerdict verdict={comparison.verdict} insight={insight} onSelectProduct={onSelectProduct} />

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
                        <GradeBadge grade={cell.grade} size="sm" showLabel={false} reason={cell.reason} />
                        {cell.reason && <span className="compare-grade-reason">{cell.reason}</span>}
                        {cell.note && <span className="compare-grade-reason">{cell.note}</span>}
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
                      <GoalMatchMeter score={p.personalized_score} allergenConflict={p.has_allergen_conflict} size="md" />
                      {comparison.goalMatch.cells[i].isBest && (
                        <span className="compare-best" style={{ marginTop: 6 }}><Check size={12} aria-hidden="true" /> Higher match</span>
                      )}
                    </td>
                  ))}
                </tr>

                {comparison.relative.available && (
                  <tr className="compare-relative-row">
                    <th scope="row" className="compare-label-col">
                      Nutrient Priority
                      <span className="compare-help">
                        1 = best balance among these products, from {comparison.relative.metrics.join(', ').toLowerCase()} (equal weight)
                      </span>
                    </th>
                    {comparison.relative.cells.map((cell, i) => (
                      <td key={products[i].product_id}>
                        {cell.rank === null ? (
                          <span className="compare-value is-missing">Not enough values</span>
                        ) : (
                          <span className="compare-cell">
                            <span className={`compare-priority${cell.rank === 1 ? ' is-first' : ''}`} aria-label={`Priority ${cell.rank} of ${products.length}${cell.tied ? ', tied' : ''}`}>
                              #{cell.rank}{cell.tied && <span>tied</span>}
                            </span>
                            {cell.isBest && <span className="compare-best"><Check size={12} aria-hidden="true" /> Best nutrient balance</span>}
                          </span>
                        )}
                      </td>
                    ))}
                  </tr>
                )}

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
        <div className="modal-overlay" onClick={closeSearchModal}>
          <div className="modal-card" onClick={e => e.stopPropagation()} style={{ maxWidth: 520 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <h3 style={{ fontSize: '1.2rem', margin: 0 }}>Add Products to Comparison</h3>
              <button type="button" onClick={closeSearchModal} aria-label="Close"><X size={18} aria-hidden="true" /></button>
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
              {!searchQuery.trim() && (
                <div className="compare-saved">
                  <div className="compare-saved-head">
                    <span>Saved products</span>
                    {savedNotSelected.length > 1 && (
                      <button type="button" className="btn-secondary btn-compact" onClick={pickAllSaved}>
                        {savedNotSelected.length <= room ? 'Select all' : `Select ${room} (max 4)`}
                      </button>
                    )}
                  </div>
                  {savedForCompare.length === 0 ? (
                    <p className="compare-saved-empty">Products you save appear here. Or search above.</p>
                  ) : savedNotSelected.length === 0 ? (
                    <p className="compare-saved-empty">All your saved products are already in this comparison.</p>
                  ) : (
                    savedNotSelected.map((p) => <PickRow key={p.product_id} product={p} picked={picked.includes(p.product_id)} disabled={!picked.includes(p.product_id) && picked.length >= room} onPick={togglePick} />)
                  )}
                </div>
              )}
              {searchResults.filter((p) => !selectedIds.includes(p.product_id)).map((p) => (
                <PickRow key={p.product_id} product={p} picked={picked.includes(p.product_id)} disabled={!picked.includes(p.product_id) && picked.length >= room} onPick={togglePick} />
              ))}
            </div>
            <div className="compare-pick-footer">
              <span>
                {picked.length === 0
                  ? `Tick up to ${room} product${room === 1 ? '' : 's'}`
                  : `${picked.length} selected${picked.length >= room ? ' (max 4 in a comparison)' : ''}`}
              </span>
              <button type="button" className="btn-primary btn-compact" disabled={picked.length === 0} onClick={addPickedToCompare}>
                {selectedIds.length + picked.length >= 2 ? `Compare ${selectedIds.length + picked.length} products` : 'Add to comparison'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function PickRow({ product, picked, disabled, onPick }) {
  return (
    <button
      type="button"
      aria-pressed={picked}
      disabled={disabled}
      onClick={() => onPick(product.product_id)}
      style={{
        width: '100%',
        textAlign: 'left',
        font: 'inherit',
        color: 'inherit',
        padding: '10px 12px',
        borderRadius: 6,
        border: picked ? '1.5px solid var(--color-primary)' : '1px solid var(--color-border)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        background: picked ? 'var(--color-accent-subtle)' : '#fff'
      }}
    >
      <div>
        <span style={{ fontSize: '0.72rem', color: 'var(--color-text-subtle)' }}>{product.brand}</span>
        <div style={{ fontWeight: 600, fontSize: '0.88rem' }}>{product.product_name}</div>
      </div>
      {picked
        ? <Check size={16} color="var(--color-primary)" aria-hidden="true" />
        : <Plus size={16} color="var(--color-accent)" aria-hidden="true" />}
    </button>
  );
}

// The verdict shows its highlights; the written explanation and the patterns across the products
// open from the "Show explanation" toggle.
function CompareVerdict({ verdict, insight, onSelectProduct }) {
  const { headline, advantages, tradeoffs, subject, comparedWith, tie, notes } = verdict;
  const detailsId = useId();
  const [showDetails, setShowDetails] = useState(false);
  const hasDetails = Boolean(insight?.explanation || insight?.patterns?.length);
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
      {/* Notes stay visible: they include allergen warnings */}
      {notes.map((n) => <p key={n} className="compare-verdict-note">{n}</p>)}
      {insight?.swap && (
        <p className="compare-verdict-swap">
          Swap idea for {insight.swap.from}:{' '}
          <button type="button" className="compare-swap-link" onClick={() => onSelectProduct(insight.swap.to.product_id)}>
            {insight.swap.to.product_name}
          </button>
          {insight.swap.to.brand ? ` (${insight.swap.to.brand})` : ''}, grade {insight.swap.to.general_grade}
          {insight.swap.to.comparative_advantages?.[0] ? `: ${insight.swap.to.comparative_advantages[0]}` : ''}
        </p>
      )}
      {hasDetails && (
        <>
          <button type="button" className="compare-verdict-toggle" aria-expanded={showDetails} aria-controls={detailsId} onClick={() => setShowDetails((v) => !v)}>
            <Chevron open={showDetails} />
            <span>{showDetails ? 'Hide explanation' : 'Show explanation'}</span>
          </button>
          <Collapse id={detailsId} open={showDetails}>
            {insight?.explanation && <p className="compare-verdict-explain">{insight.explanation}</p>}
            {insight?.patterns?.length > 0 && (
              <div className="compare-verdict-patterns">
                <strong>Across these products</strong>
                <ul>{insight.patterns.map((t) => <li key={t}>{t}</li>)}</ul>
              </div>
            )}
          </Collapse>
        </>
      )}
      <p className="compare-verdict-note">Goal Match reflects your selected goal, not overall healthiness. Always read the pack.</p>
    </section>
  );
}
