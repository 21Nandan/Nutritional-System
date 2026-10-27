import React, { useState, useEffect } from 'react';
import { 
  BarChart3, Bookmark, Clock, User, ShieldCheck, 
  ArrowRight, ScanLine, Search, ChevronRight, Award, AlertCircle 
} from 'lucide-react';

export default function Dashboard({ setActivePage, onSelectProduct, activeProfile, onOpenProfile, onRetakeOnboarding }) {
  const [history, setHistory] = useState([]);
  const [savedProducts, setSavedProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = () => {
    Promise.all([
      fetch('/api/history').then(res => res.json()),
      fetch('/api/saved').then(res => res.json())
    ])
      .then(([histData, savedData]) => {
        setHistory(histData || []);
        setSavedProducts(savedData.saved_products || []);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  };

  const handleRemoveSaved = (productId) => {
    fetch(`/api/saved/${productId}`, { method: 'POST' })
      .then(res => res.json())
      .then(() => {
        setSavedProducts(prev => prev.filter(p => p.product_id !== productId));
      })
      .catch(err => console.error(err));
  };

  return (
    <div className="dashboard-page">
      <div style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: '2.2rem', color: 'var(--color-primary)', marginBottom: 8 }}>
          User Profile & Nutrition Overview
        </h1>
        <p style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem' }}>
          Manage your dietary preferences, track your product assessments, and view saved food items.
        </p>
      </div>

      {/* Profile Overview Banner */}
      <div className="card" style={{
        background: 'linear-gradient(135deg, var(--color-surface) 0%, var(--color-surface-alt) 100%)',
        marginBottom: 24,
        padding: 24
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
          <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
            <div style={{
              width: 50,
              height: 50,
              borderRadius: '50%',
              background: 'var(--color-primary)',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <User size={24} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <h3 style={{ fontSize: '1.25rem', color: 'var(--color-primary)', margin: 0 }}>
                  {activeProfile?.name || 'Guest User'}
                </h3>
                <span className="badge badge-verified" style={{ fontSize: '0.72rem' }}>
                  {activeProfile?.dietary_preference || 'No preference'}
                </span>
                <span className="badge badge-neutral" style={{ fontSize: '0.72rem' }}>
                  Activity: {activeProfile?.activity_level || 'Moderately active'}
                </span>
              </div>
              <div style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
                Goal: <strong style={{ color: 'var(--color-primary)' }}>{activeProfile?.goal || 'Balanced Choices'}</strong>
                <span style={{ marginLeft: 8, color: 'var(--color-text-muted)' }}>
                  • Activity Level: <strong style={{ color: 'var(--color-primary)' }}>{activeProfile?.activity_level || 'Moderately active'}</strong>
                </span>
                {activeProfile?.allergens_to_avoid && (
                  <span style={{ marginLeft: 8, color: '#c62828' }}>
                    • Allergens: {activeProfile.allergens_to_avoid}
                  </span>
                )}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button className="btn-secondary" onClick={onOpenProfile} style={{ padding: '8px 16px', fontSize: '0.85rem' }}>
              Configure Profile & Activity
            </button>
            {onRetakeOnboarding && (
              <button 
                className="btn-secondary" 
                onClick={onRetakeOnboarding} 
                style={{ padding: '8px 14px', fontSize: '0.82rem', background: '#fff' }}
                title="Review terms of service and retake the initial onboarding setup"
              >
                Review Terms & Setup
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Grid: Recent History & Saved Products */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 24 }}>
        
        {/* Recent Analysis History */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Clock size={18} color="var(--color-primary)" />
              <h3 style={{ fontSize: '1.15rem', color: 'var(--color-primary)', margin: 0 }}>
                Recent Assessments
              </h3>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)' }}>
              {history.length} logged
            </span>
          </div>

          {loading ? (
            <div style={{ padding: 20, textAlign: 'center', color: '#888' }}>Loading history...</div>
          ) : history.length === 0 ? (
            <div style={{ padding: '36px 20px', textAlign: 'center', background: 'var(--color-surface-alt)', borderRadius: 10 }}>
              <ScanLine size={32} color="var(--color-text-subtle)" style={{ margin: '0 auto 10px' }} />
              <h4 style={{ fontSize: '1rem', marginBottom: 4 }}>No food analyses yet</h4>
              <p style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', marginBottom: 14 }}>
                Analyze a product label or search the catalogue to populate your evaluation history.
              </p>
              <button 
                className="btn-primary" 
                onClick={() => setActivePage('scanner')}
                style={{ padding: '8px 16px', fontSize: '0.85rem' }}
              >
                Scan Your First Food
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {history.map(item => (
                <div
                  key={item.id}
                  onClick={() => onSelectProduct(item.product_id)}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '12px 14px',
                    borderRadius: 8,
                    border: '1px solid var(--color-border)',
                    background: '#fff',
                    cursor: 'pointer',
                    transition: 'all 0.15s'
                  }}
                >
                  <div>
                    <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--color-text-subtle)' }}>
                      {item.brand}
                    </span>
                    <h4 style={{ fontSize: '0.92rem', color: 'var(--color-primary)', margin: '2px 0 4px' }}>
                      {item.product_name}
                    </h4>
                    <span style={{ fontSize: '0.72rem', color: 'var(--color-text-subtle)' }}>
                      {item.analysis_source} • {item.timestamp ? new Date(item.timestamp).toLocaleDateString() : 'Recent'}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{ textAlign: 'right' }}>
                      <span className={`grade-badge grade-${item.general_grade || 'NA'}`} style={{ width: 22, height: 22, fontSize: '0.75rem' }}>
                        {item.general_grade || 'NA'}
                      </span>
                      <div style={{ fontSize: '0.8rem', fontWeight: 800, color: 'var(--color-primary)', marginTop: 2 }}>
                        {item.personalized_score != null ? `${item.personalized_score}/100` : 'N/A'}
                      </div>
                    </div>
                    <ChevronRight size={16} color="var(--color-text-subtle)" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Saved Favorites */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Bookmark size={18} color="var(--color-primary)" />
              <h3 style={{ fontSize: '1.15rem', color: 'var(--color-primary)', margin: 0 }}>
                Saved Products
              </h3>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)' }}>
              {savedProducts.length} saved
            </span>
          </div>

          {loading ? (
            <div style={{ padding: 20, textAlign: 'center', color: '#888' }}>Loading saved products...</div>
          ) : savedProducts.length === 0 ? (
            <div style={{ padding: '36px 20px', textAlign: 'center', background: 'var(--color-surface-alt)', borderRadius: 10 }}>
              <Bookmark size={32} color="var(--color-text-subtle)" style={{ margin: '0 auto 10px' }} />
              <h4 style={{ fontSize: '1rem', marginBottom: 4 }}>No saved products</h4>
              <p style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', marginBottom: 14 }}>
                Bookmark food items from the catalogue or assessment view for quick future reference.
              </p>
              <button 
                className="btn-secondary" 
                onClick={() => setActivePage('catalogue')}
                style={{ padding: '8px 16px', fontSize: '0.85rem' }}
              >
                Browse Catalogue
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {savedProducts.map(p => (
                <div
                  key={p.product_id}
                  onClick={() => onSelectProduct(p.product_id)}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '12px 14px',
                    borderRadius: 8,
                    border: '1px solid var(--color-border)',
                    background: '#fff',
                    cursor: 'pointer'
                  }}
                >
                  <div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--color-text-subtle)' }}>{p.brand}</span>
                    <h4 style={{ fontSize: '0.92rem', color: 'var(--color-primary)', margin: '2px 0 2px' }}>
                      {p.product_name}
                    </h4>
                    <span style={{ fontSize: '0.72rem', color: 'var(--color-text-subtle)' }}>
                      {p.category}
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemoveSaved(p.product_id);
                      }}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        cursor: 'pointer',
                        padding: 4,
                        color: '#c62828'
                      }}
                      title="Remove from Saved"
                    >
                      <Bookmark size={16} fill="#c62828" />
                    </button>
                    <ChevronRight size={16} color="var(--color-text-subtle)" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
