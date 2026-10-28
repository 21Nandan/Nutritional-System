import React, { useState, useEffect } from 'react';
import { Search, Filter, AlertCircle, CheckCircle2, ChevronRight, ChevronDown, ChevronUp, Bookmark, ArrowLeftRight, Shield, Image as ImageIcon } from 'lucide-react';
import ProductImageFallback from '../components/ProductImageFallback';

export default function ProductCatalogue({ onSelectProduct, onCompareProduct, activeProfile }) {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState('');
  const [selectedCat, setSelectedCat] = useState('All');
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [savedIds, setSavedIds] = useState([]);
  const [pageSize, setPageSize] = useState('All');
  const [hasImageFilter, setHasImageFilter] = useState(false);
  const [semanticIntent, setSemanticIntent] = useState(null);

  // Filter Drawer State & Nutritional Filter States (Default: show everything / all products)
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [sugarFilter, setSugarFilter] = useState('all'); // 'all', 'healthy' (<= 10g), 'low' (<= 5g)
  const [sodiumFilter, setSodiumFilter] = useState('all'); // 'all', 'healthy' (<= 400mg), 'low' (<= 140mg)
  const [satFatFilter, setSatFatFilter] = useState('all'); // 'all', 'healthy' (<= 4g), 'low' (<= 1.5g)
  const [fibreFilter, setFibreFilter] = useState('all'); // 'all', 'good' (>= 3g), 'high' (>= 6g)
  const [proteinFilter, setProteinFilter] = useState('all'); // 'all', 'good' (>= 7g), 'high' (>= 12g)

  const isHealthyLevel = sugarFilter === 'healthy' && sodiumFilter === 'healthy' && satFatFilter === 'healthy' && fibreFilter === 'all' && proteinFilter === 'all';
  const isFiltered = sugarFilter !== 'all' || sodiumFilter !== 'all' || satFatFilter !== 'all' || fibreFilter !== 'all' || proteinFilter !== 'all';

  const applyHealthyDefaults = () => {
    setSugarFilter('healthy');
    setSodiumFilter('healthy');
    setSatFatFilter('healthy');
    setFibreFilter('all');
    setProteinFilter('all');
    setIsFilterOpen(true);
    setPage(0);
  };

  const clearAllFilters = () => {
    setSugarFilter('all');
    setSodiumFilter('all');
    setSatFatFilter('all');
    setFibreFilter('all');
    setProteinFilter('all');
    setPage(0);
  };

  useEffect(() => {
    fetch('/api/products/categories')
      .then(res => res.json())
      .then(data => {
        setCategories(data.categories || []);
      })
      .catch(err => console.error(err));

    fetch('/api/saved')
      .then(res => res.json())
      .then(data => {
        const ids = (data.saved_products || []).map(p => p.product_id);
        setSavedIds(ids);
      })
      .catch(err => console.error(err));
  }, []);

  const toggleSaveInCatalogue = (prod) => {
    fetch(`/api/saved/${prod.product_id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(prod)
    })
      .then(res => res.json())
      .then(data => {
        setSavedIds(prev => 
          data.is_saved ? [...prev, prod.product_id] : prev.filter(id => id !== prod.product_id)
        );
      })
      .catch(err => console.error(err));
  };

  useEffect(() => {
    fetchProducts();
  }, [query, selectedCat, page, pageSize, sugarFilter, sodiumFilter, satFatFilter, fibreFilter, proteinFilter, hasImageFilter]);

  const fetchProducts = () => {
    setLoading(true);
    const limitNum = pageSize === 'All' ? 1000 : Number(pageSize);
    const offsetNum = pageSize === 'All' ? 0 : page * limitNum;
    const params = new URLSearchParams({
      query,
      category: selectedCat,
      limit: limitNum,
      offset: offsetNum
    });

    if (hasImageFilter) params.append('has_image', 'true');

    if (sugarFilter === 'healthy') params.append('max_sugars', '10');
    else if (sugarFilter === 'low') params.append('max_sugars', '5');

    if (sodiumFilter === 'healthy') params.append('max_sodium', '400');
    else if (sodiumFilter === 'low') params.append('max_sodium', '140');

    if (satFatFilter === 'healthy') params.append('max_sat_fat', '4');
    else if (satFatFilter === 'low') params.append('max_sat_fat', '1.5');

    if (fibreFilter === 'good') params.append('min_fibre', '3');
    else if (fibreFilter === 'high') params.append('min_fibre', '6');

    if (proteinFilter === 'good') params.append('min_protein', '7');
    else if (proteinFilter === 'high') params.append('min_protein', '12');

    const cid = localStorage.getItem('eatgood_client_id') || activeProfile?.user_id || 'USR_DEFAULT';
    fetch(`/api/products?${params.toString()}&user_id=${encodeURIComponent(cid)}`, {
      headers: { 'X-User-Id': cid }
    })
      .then(res => res.json())
      .then(data => {
        setProducts(data.products || []);
        setTotal(data.total || 0);
        setSemanticIntent(data.interpreted_intent || null);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  };

  return (
    <div className="product-catalogue">
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: '2.2rem', color: 'var(--color-primary)', marginBottom: 8 }}>
          Indian Packaged Food Catalogue
        </h1>
        <p style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem' }}>
          Explore audited retail products across categories with authentic nutritional and ingredient profiles.
        </p>
      </div>

      {/* Search and Category Filter Toolbar */}
      <div style={{
        background: '#fff',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        padding: '20px',
        marginBottom: 24,
        boxShadow: 'var(--shadow-sm)'
      }}>
        {/* Search input */}
        <div style={{ position: 'relative', marginBottom: 16 }}>
          <Search size={18} color="var(--color-text-subtle)" style={{ position: 'absolute', left: 14, top: 13 }} />
          <input
            type="text"
            placeholder="Search by product name, brand (e.g. Haldiram's, Lay's, Kellogg's), ingredient, or barcode..."
            value={query}
            onChange={e => { setQuery(e.target.value); setPage(0); }}
            style={{
              width: '100%',
              padding: '11px 14px 11px 42px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border)',
              fontSize: '0.95rem',
              outline: 'none',
              transition: 'border-color 0.2s'
            }}
          />
        </div>

        {semanticIntent && (semanticIntent.nutrient_focus?.length > 0 || semanticIntent.excluded_allergens?.length > 0) && (
          <div style={{ marginTop: -8, marginBottom: 16, padding: '8px 12px', background: 'var(--color-surface-alt)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)', display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', fontSize: '0.8rem', color: 'var(--color-primary)' }}>
            <span style={{ fontWeight: 700 }}>🔍 Interpreted Intent:</span>
            {semanticIntent.category && <span className="badge badge-neutral" style={{ fontSize: '0.72rem' }}>{semanticIntent.category}</span>}
            {semanticIntent.nutrient_focus?.map((f, i) => <span key={i} className="badge badge-verified" style={{ fontSize: '0.72rem' }}>{f}</span>)}
            {semanticIntent.excluded_allergens?.map((a, i) => <span key={i} className="badge badge-warning" style={{ fontSize: '0.72rem' }}>Excluding {a}</span>)}
          </div>
        )}

        {/* Category Pills */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
          <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--color-text-subtle)', marginRight: 4 }}>
            CATEGORY:
          </span>
          {categories.map(cat => {
            const isSelected = selectedCat === cat;
            return (
              <button
                key={cat}
                onClick={() => { setSelectedCat(cat); setPage(0); }}
                style={{
                  padding: '6px 12px',
                  borderRadius: 'var(--radius-full)',
                  fontSize: '0.8rem',
                  fontWeight: isSelected ? 700 : 500,
                  border: isSelected ? '1px solid var(--color-primary)' : '1px solid var(--color-border)',
                  background: isSelected ? 'var(--color-primary)' : '#fff',
                  color: isSelected ? '#fff' : 'var(--color-text-main)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4
                }}
              >
                <span>{cat}</span>
              </button>
            );
          })}
        </div>

        {/* Filter Options Toolbar (Collapsible via arrow at the side) */}
        <div style={{
          marginTop: 16,
          paddingTop: 16,
          borderTop: '1px solid var(--color-border)'
        }}>
          <div 
            onClick={() => setIsFilterOpen(prev => !prev)}
            style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center', 
              flexWrap: 'wrap', 
              gap: 10,
              cursor: 'pointer',
              userSelect: 'none',
              padding: '4px 0'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Filter size={16} color="var(--color-primary)" />
                <span style={{ fontSize: '0.82rem', fontWeight: 800, color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                  Filter Options:
                </span>
              </div>
              {isHealthyLevel ? (
                <span style={{
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  padding: '3px 9px',
                  borderRadius: 12,
                  background: '#e8f5e9',
                  color: '#2e7d32',
                  border: '1px solid #c8e6c9',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4
                }}>
                  <CheckCircle2 size={13} />
                  Healthy Level (Sugar ≤ 10g • Sodium ≤ 400mg • Sat Fat ≤ 4g)
                </span>
              ) : isFiltered ? (
                <span style={{
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  padding: '3px 9px',
                  borderRadius: 12,
                  background: '#fff3e0',
                  color: '#e65100',
                  border: '1px solid #ffe0b2'
                }}>
                  Custom Filters Active
                </span>
              ) : (
                <span style={{
                  fontSize: '0.72rem',
                  fontWeight: 600,
                  padding: '3px 9px',
                  borderRadius: 12,
                  background: '#f5f5f5',
                  color: 'var(--color-text-subtle)'
                }}>
                  All Packaged Foods
                </span>
              )}
            </div>

            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setHasImageFilter(prev => !prev);
                  setPage(0);
                }}
                style={{
                  padding: '5px 12px',
                  fontSize: '0.76rem',
                  fontWeight: hasImageFilter ? 800 : 600,
                  borderRadius: 6,
                  border: hasImageFilter ? '1px solid var(--color-primary)' : '1px solid var(--color-border)',
                  background: hasImageFilter ? 'var(--color-primary)' : '#fff',
                  color: hasImageFilter ? '#fff' : 'var(--color-text-main)',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4
                }}
              >
                <ImageIcon size={13} />
                <span>Photos Only</span>
              </button>

              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  applyHealthyDefaults();
                }}
                style={{
                  padding: '5px 12px',
                  fontSize: '0.76rem',
                  fontWeight: isHealthyLevel ? 800 : 600,
                  borderRadius: 6,
                  border: isHealthyLevel ? '1px solid #2e7d32' : '1px solid var(--color-border)',
                  background: isHealthyLevel ? '#e8f5e9' : '#fff',
                  color: isHealthyLevel ? '#2e7d32' : 'var(--color-text-main)',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4
                }}
              >
                <span>🌿 Reset to Healthy Level</span>
              </button>

              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  clearAllFilters();
                }}
                style={{
                  padding: '5px 12px',
                  fontSize: '0.76rem',
                  fontWeight: !isFiltered ? 800 : 500,
                  borderRadius: 6,
                  border: !isFiltered ? '1px solid var(--color-primary)' : '1px solid var(--color-border)',
                  background: !isFiltered ? 'var(--color-primary)' : '#fff',
                  color: !isFiltered ? '#fff' : 'var(--color-text-muted)',
                  cursor: 'pointer'
                }}
              >
                Reset Filters
              </button>

              {/* Arrow toggle button at the side */}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setIsFilterOpen(prev => !prev);
                }}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '5px 10px',
                  fontSize: '0.76rem',
                  fontWeight: 700,
                  borderRadius: 6,
                  border: '1px solid var(--color-border)',
                  background: isFilterOpen ? 'var(--color-surface-alt)' : '#fff',
                  color: 'var(--color-primary)',
                  cursor: 'pointer',
                  marginLeft: 4
                }}
                title={isFilterOpen ? "Collapse filter options" : "Open filter options"}
              >
                <span>{isFilterOpen ? 'Hide' : 'Open Filters'}</span>
                <ChevronDown 
                  size={15} 
                  style={{
                    transform: isFilterOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                    transition: 'transform 0.2s ease'
                  }}
                />
              </button>
            </div>
          </div>

          {/* Filter Pills Grid (Collapsible) */}
          {isFilterOpen && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: 12,
            background: 'var(--color-surface-alt)',
            padding: '12px 14px',
            borderRadius: 8,
            border: '1px solid var(--color-border)',
            marginTop: 12
          }}>
            {/* Sugar Filter */}
            <div>
              <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--color-text-subtle)', display: 'block', marginBottom: 6, textTransform: 'uppercase' }}>
                Sugar (per 100g)
              </span>
              <div style={{ display: 'flex', gap: 4 }}>
                {[
                  { id: 'healthy', label: 'Healthy (≤10g)' },
                  { id: 'low', label: 'Low (≤5g)' },
                  { id: 'all', label: 'All' }
                ].map(opt => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => { setSugarFilter(opt.id); setPage(0); }}
                    style={{
                      flex: 1,
                      padding: '5px 6px',
                      fontSize: '0.72rem',
                      fontWeight: sugarFilter === opt.id ? 800 : 500,
                      borderRadius: 4,
                      border: sugarFilter === opt.id ? '1px solid #2e7d32' : '1px solid var(--color-border)',
                      background: sugarFilter === opt.id ? '#2e7d32' : '#fff',
                      color: sugarFilter === opt.id ? '#fff' : 'var(--color-text-main)',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Sodium Filter */}
            <div>
              <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--color-text-subtle)', display: 'block', marginBottom: 6, textTransform: 'uppercase' }}>
                Sodium (per 100g)
              </span>
              <div style={{ display: 'flex', gap: 4 }}>
                {[
                  { id: 'healthy', label: 'Healthy (≤400mg)' },
                  { id: 'low', label: 'Low (≤140mg)' },
                  { id: 'all', label: 'All' }
                ].map(opt => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => { setSodiumFilter(opt.id); setPage(0); }}
                    style={{
                      flex: 1,
                      padding: '5px 6px',
                      fontSize: '0.72rem',
                      fontWeight: sodiumFilter === opt.id ? 800 : 500,
                      borderRadius: 4,
                      border: sodiumFilter === opt.id ? '1px solid #2e7d32' : '1px solid var(--color-border)',
                      background: sodiumFilter === opt.id ? '#2e7d32' : '#fff',
                      color: sodiumFilter === opt.id ? '#fff' : 'var(--color-text-main)',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Saturated Fat Filter */}
            <div>
              <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--color-text-subtle)', display: 'block', marginBottom: 6, textTransform: 'uppercase' }}>
                Saturated Fat
              </span>
              <div style={{ display: 'flex', gap: 4 }}>
                {[
                  { id: 'healthy', label: 'Healthy (≤4g)' },
                  { id: 'low', label: 'Low (≤1.5g)' },
                  { id: 'all', label: 'All' }
                ].map(opt => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => { setSatFatFilter(opt.id); setPage(0); }}
                    style={{
                      flex: 1,
                      padding: '5px 6px',
                      fontSize: '0.72rem',
                      fontWeight: satFatFilter === opt.id ? 800 : 500,
                      borderRadius: 4,
                      border: satFatFilter === opt.id ? '1px solid #2e7d32' : '1px solid var(--color-border)',
                      background: satFatFilter === opt.id ? '#2e7d32' : '#fff',
                      color: satFatFilter === opt.id ? '#fff' : 'var(--color-text-main)',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Dietary Fibre */}
            <div>
              <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--color-text-subtle)', display: 'block', marginBottom: 6, textTransform: 'uppercase' }}>
                Dietary Fibre
              </span>
              <div style={{ display: 'flex', gap: 4 }}>
                {[
                  { id: 'all', label: 'All' },
                  { id: 'good', label: 'Source (≥3g)' },
                  { id: 'high', label: 'High (≥6g)' }
                ].map(opt => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => { setFibreFilter(opt.id); setPage(0); }}
                    style={{
                      flex: 1,
                      padding: '5px 6px',
                      fontSize: '0.72rem',
                      fontWeight: fibreFilter === opt.id ? 800 : 500,
                      borderRadius: 4,
                      border: fibreFilter === opt.id ? '1px solid var(--color-primary)' : '1px solid var(--color-border)',
                      background: fibreFilter === opt.id ? 'var(--color-primary)' : '#fff',
                      color: fibreFilter === opt.id ? '#fff' : 'var(--color-text-main)',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Protein */}
            <div>
              <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--color-text-subtle)', display: 'block', marginBottom: 6, textTransform: 'uppercase' }}>
                Protein
              </span>
              <div style={{ display: 'flex', gap: 4 }}>
                {[
                  { id: 'all', label: 'All' },
                  { id: 'good', label: 'Source (≥7g)' },
                  { id: 'high', label: 'High (≥12g)' }
                ].map(opt => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => { setProteinFilter(opt.id); setPage(0); }}
                    style={{
                      flex: 1,
                      padding: '5px 6px',
                      fontSize: '0.72rem',
                      fontWeight: proteinFilter === opt.id ? 800 : 500,
                      borderRadius: 4,
                      border: proteinFilter === opt.id ? '1px solid var(--color-primary)' : '1px solid var(--color-border)',
                      background: proteinFilter === opt.id ? 'var(--color-primary)' : '#fff',
                      color: proteinFilter === opt.id ? '#fff' : 'var(--color-text-main)',
                      cursor: 'pointer',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
          )}
        </div>

        {/* Page Size Selector */}
        <div style={{
          marginTop: 14,
          paddingTop: 12,
          borderTop: '1px solid var(--color-border)',
          fontSize: '0.78rem',
          color: 'var(--color-text-muted)',
          display: 'flex',
          justifyContent: 'flex-end',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 10
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.78rem' }}>
              <span style={{ color: 'var(--color-text-subtle)' }}>Show:</span>
              {[30, 60, 'All'].map(size => (
                <button
                  key={size}
                  onClick={() => { setPageSize(size); setPage(0); }}
                  style={{
                    padding: '3px 9px',
                    borderRadius: 4,
                    fontSize: '0.75rem',
                    fontWeight: pageSize === size ? 700 : 500,
                    border: '1px solid var(--color-border)',
                    background: pageSize === size ? 'var(--color-primary)' : '#fff',
                    color: pageSize === size ? '#fff' : 'var(--color-text-main)',
                    cursor: 'pointer'
                  }}
                >
                  {size}
                </button>
              ))}
            </div>
            <div style={{ fontWeight: 700, color: 'var(--color-primary)' }}>
              {selectedCat === 'All' ? 'Indian Packaged Foods' : `${selectedCat}`}
              {isFiltered ? ' • Filter Active' : ''}
              {hasImageFilter ? ' • Packaging Photos' : ''}
            </div>
          </div>
        </div>
      </div>

      {/* Product Grid */}
      {loading ? (
        <div style={{ padding: '60px 0', textAlign: 'center', color: 'var(--color-text-muted)' }}>
          Loading products...
        </div>
      ) : products.length === 0 ? (
        <div style={{ padding: '60px 20px', textAlign: 'center', background: '#fff', borderRadius: 12, border: '1px solid var(--color-border)' }}>
          <AlertCircle size={36} color="var(--color-text-subtle)" style={{ margin: '0 auto 12px' }} />
          <h3 style={{ fontSize: '1.2rem', marginBottom: 6 }}>No matching products found</h3>
          <p style={{ color: 'var(--color-text-muted)', fontSize: '0.88rem', maxWidth: 480, margin: '0 auto 16px' }}>
            {isFiltered
              ? `No products in ${selectedCat === 'All' ? 'the catalogue' : selectedCat} meet all currently active nutritional limits.`
              : 'Try adjusting your search terms or selecting another category.'}
          </p>
          {isFiltered && (
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
              <button
                className="btn-primary"
                onClick={clearAllFilters}
                style={{ padding: '8px 18px', fontSize: '0.85rem' }}
              >
                Show All Products (Clear Filters)
              </button>
              <button
                className="btn-secondary"
                onClick={() => { setSatFatFilter('all'); setSodiumFilter('all'); setPage(0); }}
                style={{ padding: '8px 18px', fontSize: '0.85rem' }}
              >
                Relax Sodium & Fat Limits
              </button>
            </div>
          )}
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: 16
        }}>
          {products.map(prod => {
            const isDiscrepancy = prod.data_confidence_status && prod.data_confidence_status.includes('Anomaly');

            return (
              <div 
                key={prod.product_id}
                className="card"
                style={{ padding: '16px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}
              >
                <div>
                  {/* Product Packaging Image Container */}
                  <div style={{
                    width: '100%',
                    height: 140,
                    borderRadius: 8,
                    background: '#f8f9fa',
                    marginBottom: 12,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    overflow: 'hidden',
                    position: 'relative',
                    border: '1px solid rgba(0, 0, 0, 0.05)'
                  }}>
                    {prod.image_small_url || prod.image_url ? (
                      <img
                        src={prod.image_small_url || prod.image_url}
                        alt={prod.product_name}
                        loading="lazy"
                        onError={(e) => {
                          e.currentTarget.style.display = 'none';
                          const fallback = e.currentTarget.parentElement.querySelector('.image-fallback-container');
                          if (fallback) fallback.style.display = 'flex';
                        }}
                        style={{
                          width: '100%',
                          height: '100%',
                          objectFit: 'contain',
                          padding: 6
                        }}
                      />
                    ) : null}
                    <div 
                      className="image-fallback-container"
                      style={{
                        display: (prod.image_small_url || prod.image_url) ? 'none' : 'flex',
                        width: '100%',
                        height: '100%'
                      }}
                    >
                      <ProductImageFallback
                        category={prod.category}
                        brand={prod.brand}
                        productName={prod.product_name}
                        height={140}
                      />
                    </div>
                  </div>

                  {/* Brand */}
                  <div style={{ marginBottom: 6 }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-text-subtle)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                      {prod.brand}
                    </span>
                  </div>

                  <h3 style={{ fontSize: '1.05rem', color: 'var(--color-primary)', marginBottom: 8, lineHeight: 1.3 }}>
                    {prod.product_name}
                  </h3>

                  <div style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)', marginBottom: 10 }}>
                    <span>{prod.category}</span> • <span>{prod.sub_category}</span>
                  </div>

                  {prod.semantic_reason && (
                    <div style={{ fontSize: '0.72rem', color: 'var(--color-primary)', background: 'var(--color-accent-subtle)', padding: '4px 8px', borderRadius: 4, marginBottom: 10, fontWeight: 600 }}>
                      ✨ {prod.semantic_reason}
                    </div>
                  )}

                  {/* Nutrition Highlights Grid */}
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(3, 1fr)',
                    gap: 6,
                    background: 'var(--color-surface-alt)',
                    padding: '8px 10px',
                    borderRadius: 8,
                    marginBottom: 12,
                    fontSize: '0.75rem'
                  }}>
                    <div>
                      <span style={{ color: 'var(--color-text-subtle)', display: 'block' }}>Energy</span>
                      <strong>{prod.energy_kcal != null ? `${prod.energy_kcal} kcal` : 'N/A'}</strong>
                    </div>
                    <div>
                      <span style={{ color: 'var(--color-text-subtle)', display: 'block' }}>Sugars</span>
                      <strong style={{ color: prod.sugars_g > 15 ? '#c62828' : 'inherit' }}>
                        {prod.sugars_g != null ? `${prod.sugars_g}g` : 'Missing'}
                      </strong>
                    </div>
                    <div>
                      <span style={{ color: 'var(--color-text-subtle)', display: 'block' }}>Sodium</span>
                      <strong style={{ color: prod.sodium_mg > 600 ? '#e65100' : 'inherit' }}>
                        {prod.sodium_mg != null ? `${int(prod.sodium_mg)}mg` : 'Missing'}
                      </strong>
                    </div>
                  </div>

                  {/* Data confidence indicator */}
                  {isDiscrepancy && (
                    <div style={{ fontSize: '0.72rem', color: '#c62828', background: '#ffebee', padding: '4px 8px', borderRadius: 4, marginBottom: 10 }}>
                      ⚠️ Audit: Calorie discrepancy detected
                    </div>
                  )}
                </div>

                {/* Bottom Actions */}
                <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                  <button
                    className="btn-primary"
                    style={{ flex: 1, padding: '7px 12px', fontSize: '0.82rem', justifyContent: 'center' }}
                    onClick={() => onSelectProduct(prod.product_id)}
                  >
                    <span>View Assessment</span>
                    <ChevronRight size={14} />
                  </button>

                  <button
                    className="btn-secondary"
                    style={{ padding: '7px 10px', color: savedIds.includes(prod.product_id) ? '#c62828' : 'inherit' }}
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleSaveInCatalogue(prod);
                    }}
                    title={savedIds.includes(prod.product_id) ? "Remove from Saved" : "Save Product"}
                  >
                    <Bookmark size={14} fill={savedIds.includes(prod.product_id) ? '#c62828' : 'none'} />
                  </button>

                  <button
                    className="btn-secondary"
                    style={{ padding: '7px 10px' }}
                    onClick={() => onCompareProduct(prod.product_id)}
                    title="Add to Compare"
                  >
                    <ArrowLeftRight size={14} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination */}
      {pageSize !== 'All' && (page > 0 || products.length >= Number(pageSize)) && (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 14, marginTop: 32 }}>
          <button
            className="btn-secondary"
            disabled={page === 0}
            onClick={() => setPage(p => Math.max(0, p - 1))}
            style={{ opacity: page === 0 ? 0.5 : 1 }}
          >
            Previous
          </button>
          <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--color-primary)' }}>
            Page {page + 1}
          </span>
          <button
            className="btn-secondary"
            disabled={products.length < Number(pageSize)}
            onClick={() => setPage(p => p + 1)}
            style={{ opacity: products.length < Number(pageSize) ? 0.5 : 1 }}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

function int(val) {
  return Math.round(val || 0);
}
