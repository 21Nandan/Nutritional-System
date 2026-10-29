import React, { useState } from 'react';
import { Search, RefreshCw, Package, ArrowRight, Globe, AlertCircle } from 'lucide-react';
import { apiFetch } from '../api';

// Searches the Open Food Facts world database through the EATGOOD API. Each search is one
// request made when the user presses Search; failures are shown, never turned into "no results".
export default function OpenFoodFactsSearch({ onSelectProduct }) {
  const [query, setQuery] = useState('');
  const [searchedQuery, setSearchedQuery] = useState('');
  const [results, setResults] = useState([]);
  const [page, setPage] = useState(0);
  const [count, setCount] = useState(null);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const runSearch = async (term, nextPage) => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch(`/api/products/search/openfoodfacts?q=${encodeURIComponent(term)}&page=${nextPage}`);
      setResults(prev => (nextPage === 1 ? data.products : [...prev, ...data.products]));
      setPage(nextPage);
      setCount(data.count);
      setHasMore(data.has_more);
      setSearchedQuery(term);
    } catch (err) {
      if (nextPage === 1) {
        setResults([]);
        setSearchedQuery(term);
      }
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const term = query.trim();
    if (term.length < 2) {
      setError('Type at least 2 characters to search.');
      return;
    }
    runSearch(term, 1);
  };

  const finishedEmpty = !loading && !error && searchedQuery && results.length === 0;

  return (
    <div className="card off-search" style={{ maxWidth: 760, margin: '0 auto 30px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
        <Globe size={22} color="var(--color-primary)" aria-hidden="true" />
        <h2 style={{ fontSize: '1.25rem', color: 'var(--color-primary)', margin: 0 }}>Search products</h2>
      </div>
      <p style={{ fontSize: '0.88rem', color: 'var(--color-text-muted)', marginBottom: 16 }}>
        Searches Open Food Facts, a free world database of millions of packaged foods. Try a product or brand name.
      </p>

      <form onSubmit={handleSubmit} className="off-search-form" role="search">
        <label htmlFor="off-search-input" className="sr-only">Product or brand name</label>
        <input
          id="off-search-input"
          type="search"
          inputMode="search"
          enterKeyHint="search"
          autoComplete="off"
          maxLength={100}
          placeholder="e.g. Kurkure, Maggi noodles, Amul butter"
          value={query}
          onChange={e => setQuery(e.target.value)}
        />
        <button type="submit" className="btn-primary btn-compact" disabled={loading}>
          {loading && page === 0 ? <RefreshCw size={16} className="spin" aria-hidden="true" /> : <Search size={16} aria-hidden="true" />}
          <span>Search</span>
        </button>
      </form>

      {error && (
        <div role="alert" style={{ marginTop: 14, padding: '10px 12px', borderRadius: 8, background: '#ffebee', color: '#b71c1c', fontSize: '0.86rem', display: 'flex', gap: 8, alignItems: 'flex-start' }}>
          <AlertCircle size={16} style={{ flexShrink: 0, marginTop: 2 }} aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}

      {loading && results.length === 0 && (
        <p role="status" style={{ marginTop: 16, fontSize: '0.88rem', color: 'var(--color-text-muted)', display: 'flex', gap: 8, alignItems: 'center' }}>
          <RefreshCw size={15} className="spin" aria-hidden="true" /> Searching Open Food Facts…
        </p>
      )}

      {finishedEmpty && (
        <p role="status" style={{ marginTop: 16, fontSize: '0.88rem', color: 'var(--color-text-muted)' }}>
          Open Food Facts has no products matching &ldquo;{searchedQuery}&rdquo;. Try another spelling, or scan the barcode.
        </p>
      )}

      {results.length > 0 && (
        <>
          <p role="status" style={{ marginTop: 16, marginBottom: 8, fontSize: '0.8rem', color: 'var(--color-text-subtle)' }}>
            Showing {results.length}{count != null ? ` of ${count.toLocaleString()}` : ''} results for &ldquo;{searchedQuery}&rdquo;
          </p>
          <ul className="off-results">
            {results.map(prod => (
              <li key={prod.barcode}>
                <button type="button" className="off-result" onClick={() => onSelectProduct(`OFF_${prod.barcode}`)}>
                  <span className="off-result-thumb">
                    {prod.image_url ? (
                      <img src={prod.image_url} alt="" loading="lazy" onError={e => { e.currentTarget.style.display = 'none'; }} />
                    ) : (
                      <Package size={20} color="var(--color-text-muted)" aria-hidden="true" />
                    )}
                  </span>
                  <span className="off-result-text">
                    <strong>{prod.product_name}</strong>
                    <span>{[prod.brand, prod.category].filter(Boolean).join(' · ')}</span>
                    {prod.nutrition_summary?.energy_kcal != null && (
                      <span>{Math.round(Number(prod.nutrition_summary.energy_kcal))} kcal {prod.measurement_basis}</span>
                    )}
                  </span>
                  <ArrowRight size={16} color="var(--color-text-muted)" aria-hidden="true" style={{ flexShrink: 0 }} />
                </button>
              </li>
            ))}
          </ul>
          {hasMore && (
            <button
              type="button"
              className="btn-secondary"
              disabled={loading}
              onClick={() => runSearch(searchedQuery, page + 1)}
              style={{ width: '100%', marginTop: 12, minHeight: 44, justifyContent: 'center' }}
            >
              {loading ? 'Loading…' : 'Show more results'}
            </button>
          )}
          <p style={{ marginTop: 12, fontSize: '0.72rem', color: 'var(--color-text-subtle)' }}>
            Data from <a href="https://world.openfoodfacts.org" target="_blank" rel="noreferrer">Open Food Facts</a> (ODbL).
            Community-contributed: check values against the pack.
          </p>
        </>
      )}
    </div>
  );
}
