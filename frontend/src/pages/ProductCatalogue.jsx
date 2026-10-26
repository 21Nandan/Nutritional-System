import React, { useState, useEffect } from 'react';
import { Search, Filter, AlertCircle, CheckCircle2, ChevronRight, Bookmark, ArrowLeftRight, Shield } from 'lucide-react';

export default function ProductCatalogue({ onSelectProduct, onCompareProduct, activeProfile }) {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [calibratedCats, setCalibratedCats] = useState([]);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState('');
  const [selectedCat, setSelectedCat] = useState('All');
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const pageSize = 30;

  useEffect(() => {
    fetch('/api/products/categories')
      .then(res => res.json())
      .then(data => {
        setCategories(data.categories || []);
        setCalibratedCats(data.calibrated_categories || []);
      })
      .catch(err => console.error(err));
  }, []);

  useEffect(() => {
    fetchProducts();
  }, [query, selectedCat, page]);

  const fetchProducts = () => {
    setLoading(true);
    const params = new URLSearchParams({
      query,
      category: selectedCat,
      limit: pageSize,
      offset: page * pageSize
    });
    fetch(`/api/products?${params.toString()}`)
      .then(res => res.json())
      .then(data => {
        setProducts(data.products || []);
        setTotal(data.total || 0);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  };

  const isCalibrated = (cat) => calibratedCats.includes(cat);

  return (
    <div className="product-catalogue">
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: '2.2rem', color: 'var(--color-primary)', marginBottom: 8 }}>
          Indian Packaged Food Catalogue
        </h1>
        <p style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem' }}>
          Explore 852 audited retail products across 8 categories with authentic nutritional and ingredient profiles.
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

        {/* Category Pills */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
          <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--color-text-subtle)', marginRight: 4 }}>
            CATEGORY:
          </span>
          {categories.map(cat => {
            const isSelected = selectedCat === cat;
            const calibrated = cat !== 'All' && isCalibrated(cat);
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
                {calibrated && (
                  <span style={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    background: isSelected ? '#82c733' : '#58a834'
                  }} title="Calibrated Category" />
                )}
              </button>
            );
          })}
        </div>

        {/* Calibrated Notice */}
        <div style={{
          marginTop: 14,
          paddingTop: 12,
          borderTop: '1px solid var(--color-border)',
          fontSize: '0.78rem',
          color: 'var(--color-text-muted)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div>
            <span style={{ fontWeight: 700, color: 'var(--color-primary)' }}>Calibrated Scope (Active Benchmarking):</span>
            <span style={{ marginLeft: 6 }}>Snacks, Breakfast Cereals, Packaged Beverages</span>
          </div>
          <div style={{ fontWeight: 600 }}>
            Showing {products.length} of {total} products
          </div>
        </div>
      </div>

      {/* Product Grid */}
      {loading ? (
        <div style={{ padding: '60px 0', textAlign: 'center', color: 'var(--color-text-muted)' }}>
          Loading products...
        </div>
      ) : products.length === 0 ? (
        <div style={{ padding: '60px 0', textAlign: 'center', background: '#fff', borderRadius: 12, border: '1px solid var(--color-border)' }}>
          <AlertCircle size={36} color="var(--color-text-subtle)" style={{ margin: '0 auto 12px' }} />
          <h3 style={{ fontSize: '1.2rem', marginBottom: 6 }}>No matching products found</h3>
          <p style={{ color: 'var(--color-text-muted)', fontSize: '0.88rem' }}>Try adjusting your search terms or selecting 'All' categories.</p>
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: 16
        }}>
          {products.map(prod => {
            const calibrated = isCalibrated(prod.category);
            const isDiscrepancy = prod.data_confidence_status && prod.data_confidence_status.includes('Anomaly');

            return (
              <div 
                key={prod.product_id}
                className="card"
                style={{ padding: '18px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}
              >
                <div>
                  {/* Top Badges */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-text-subtle)', textTransform: 'uppercase' }}>
                      {prod.brand}
                    </span>
                    <div style={{ display: 'flex', gap: 4 }}>
                      {calibrated ? (
                        <span className="badge badge-verified" style={{ fontSize: '0.68rem', padding: '2px 6px' }}>
                          Calibrated Scope
                        </span>
                      ) : (
                        <span className="badge badge-neutral" style={{ fontSize: '0.68rem', padding: '2px 6px' }}>
                          Uncalibrated Category
                        </span>
                      )}
                    </div>
                  </div>

                  <h3 style={{ fontSize: '1.05rem', color: 'var(--color-primary)', marginBottom: 8, lineHeight: 1.3 }}>
                    {prod.product_name}
                  </h3>

                  <div style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)', marginBottom: 12 }}>
                    <span>{prod.category}</span> • <span>{prod.sub_category}</span>
                  </div>

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
      {total > pageSize && (
        <div style={{ display: 'flex', justifyContent: 'center', gap: 12, marginTop: 32 }}>
          <button
            className="btn-secondary"
            disabled={page === 0}
            onClick={() => setPage(p => Math.max(0, p - 1))}
            style={{ opacity: page === 0 ? 0.5 : 1 }}
          >
            Previous
          </button>
          <span style={{ display: 'flex', alignItems: 'center', fontSize: '0.85rem', fontWeight: 600 }}>
            Page {page + 1} of {Math.ceil(total / pageSize)}
          </span>
          <button
            className="btn-secondary"
            disabled={(page + 1) * pageSize >= total}
            onClick={() => setPage(p => p + 1)}
            style={{ opacity: (page + 1) * pageSize >= total ? 0.5 : 1 }}
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
