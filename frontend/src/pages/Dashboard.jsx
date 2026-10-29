import React, { useId, useState } from 'react';
import { apiFetch } from '../api';
import { clearHistory, loadHistory, loadSavedProducts, toggleSavedProduct } from '../storage';
import { Bookmark, Clock, User, ScanLine, ChevronRight, Settings } from 'lucide-react';
import { Chevron, Collapse } from '../components/Expandable';
import { GradeBadge } from '../components/ScoreDisplay';

function splitList(value) {
  return String(value || '').split(',').map((v) => v.trim()).filter(Boolean);
}

// A card whose heading opens and closes its content. The count and any extra actions sit
// beside the heading button, so they stay usable while the section is collapsed.
function CollapsibleSection({ icon: Icon, title, count, actions, children }) {
  const id = useId();
  const [open, setOpen] = useState(true);
  return (
    <section className="card profile-section">
      <div className="profile-section-head">
        <button type="button" className="profile-section-toggle" aria-expanded={open} aria-controls={id} onClick={() => setOpen((v) => !v)}>
          <Icon size={17} aria-hidden="true" />
          <h3>{title}</h3>
          <span className="profile-section-count">{count}</span>
          <Chevron open={open} />
        </button>
        {actions}
      </div>
      <Collapse id={id} open={open}>
        <div className="profile-section-body">{children}</div>
      </Collapse>
    </section>
  );
}

export default function Dashboard({ setActivePage, onSelectProduct, onOpenCustomAssessment, activeProfile, onOpenProfile, onRetakeOnboarding }) {
  // History and saved products are kept only in this browser.
  const [history, setHistory] = useState(() => loadHistory());
  const [savedProducts, setSavedProducts] = useState(() => loadSavedProducts());
  const [openError, setOpenError] = useState(null);

  // Custom scans have no server record, so a saved one is re-assessed from its confirmed values.
  const openSaved = (p) => {
    setOpenError(null);
    if (!p.is_custom) {
      onSelectProduct(p.product_id);
      return;
    }
    apiFetch('/api/products/assess', { method: 'POST', body: p.raw_input })
      .then((assessment) => onOpenCustomAssessment(assessment))
      .catch((err) => setOpenError(err.message));
  };

  const handleClearHistory = () => {
    clearHistory();
    setHistory([]);
  };

  const handleRemoveSaved = (productId) => {
    const product = savedProducts.find((p) => p.product_id === productId);
    if (!product) return;
    try {
      toggleSavedProduct(product);
      setSavedProducts(loadSavedProducts());
    } catch (err) {
      window.alert(err.message);
    }
  };

  const goals = splitList(activeProfile?.goal || 'Balanced Choices');
  const allergens = splitList(activeProfile?.allergens_to_avoid);

  return (
    <div className="dashboard-page">
      <div className="profile-page-head">
        <h1>User Profile &amp; Nutrition Overview</h1>
        <p>Your preferences, recent assessments and saved products. Everything here is stored only in this browser.</p>
      </div>

      <section className="card profile-card" aria-label="Your profile">
        <div className="profile-card-top">
          <div className="profile-identity">
            <span className="profile-avatar" aria-hidden="true"><User size={20} /></span>
            <h2>{activeProfile?.name || 'Guest User'}</h2>
          </div>
          <div className="profile-actions">
            <button type="button" className="btn-primary btn-compact" onClick={onOpenProfile}>
              <Settings size={15} aria-hidden="true" />
              <span>Configure Profile &amp; Activity</span>
            </button>
            {onRetakeOnboarding && (
              <button
                type="button"
                className="btn-secondary btn-compact"
                onClick={onRetakeOnboarding}
                title="Review terms of service and retake the initial onboarding setup"
              >
                Review Terms &amp; Setup
              </button>
            )}
          </div>
        </div>

        <dl className="profile-details">
          <div>
            <dt>Diet</dt>
            <dd>{activeProfile?.dietary_preference || 'No preference'}</dd>
          </div>
          <div>
            <dt>Activity level</dt>
            <dd>{activeProfile?.activity_level || 'Moderately active'}</dd>
          </div>
          <div>
            <dt>Nutrition goals</dt>
            <dd className="profile-chips">
              {goals.map((g) => <span key={g} className="profile-chip">{g}</span>)}
            </dd>
          </div>
          <div>
            <dt>Allergens to avoid</dt>
            <dd className="profile-chips">
              {allergens.length > 0
                ? allergens.map((a) => <span key={a} className="profile-chip profile-chip-allergen">{a}</span>)
                : <span className="profile-muted">None set</span>}
            </dd>
          </div>
        </dl>
      </section>

      <div className="dashboard-columns">
        <CollapsibleSection
          icon={Clock}
          title="Recent Assessments"
          count={`${history.length} logged`}
          actions={history.length > 0 && (
            <button
              type="button"
              className="profile-clear"
              onClick={handleClearHistory}
              title="Clear all recent assessment history on this device"
            >
              Clear History
            </button>
          )}
        >
          {history.length === 0 ? (
            <div className="profile-empty">
              <ScanLine size={28} color="var(--color-text-subtle)" aria-hidden="true" />
              <h4>No food analyses yet</h4>
              <p>Search for a product or scan a barcode to start your history.</p>
              <button type="button" className="btn-primary btn-compact" onClick={() => setActivePage('scanner')}>
                Find a Product
              </button>
            </div>
          ) : (
            <ul className="profile-list">
              {history.map((item) => {
                const isCustom = item.product_id === 'CUSTOM_SCAN';
                return (
                  <li key={`${item.product_id}-${item.timestamp}`}>
                    <button
                      type="button"
                      className="profile-item"
                      onClick={() => onSelectProduct(item.product_id)}
                      disabled={isCustom}
                      title={isCustom ? 'Entered values are not stored. Save an assessment to reopen it.' : undefined}
                    >
                      <span className="profile-item-text">
                        <span className="profile-item-brand">{item.brand}</span>
                        <span className="profile-item-name">{item.product_name}</span>
                        <span className="profile-item-meta">
                          {item.timestamp ? new Date(item.timestamp).toLocaleDateString() : 'Recent'}
                        </span>
                      </span>
                      <span className="profile-item-scores">
                        <GradeBadge grade={item.general_grade || 'N/A'} size="sm" showLabel={false} />
                        <span className="profile-item-goal">
                          {item.personalized_score != null ? <>{item.personalized_score}<small>/100</small></> : 'N/A'}
                        </span>
                      </span>
                      {!isCustom && <ChevronRight size={16} color="var(--color-text-subtle)" aria-hidden="true" />}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </CollapsibleSection>

        <CollapsibleSection icon={Bookmark} title="Saved Items" count={`${savedProducts.length} saved`}>
          {openError && <p role="alert" className="profile-error">{openError}</p>}
          {savedProducts.length === 0 ? (
            <div className="profile-empty">
              <Bookmark size={28} color="var(--color-text-subtle)" aria-hidden="true" />
              <h4>No saved products</h4>
              <p>Bookmark products from the catalogue or a product page to find them quickly later.</p>
              <button type="button" className="btn-secondary btn-compact" onClick={() => setActivePage('catalogue')}>
                Browse Catalogue
              </button>
            </div>
          ) : (
            <ul className="profile-list">
              {savedProducts.map((p) => (
                <li key={p.product_id} className="profile-saved-row">
                  <button type="button" className="profile-item" onClick={() => openSaved(p)}>
                    <span className="profile-item-text">
                      <span className="profile-item-brand">{p.brand}</span>
                      <span className="profile-item-name">{p.product_name}</span>
                      <span className="profile-item-meta">{p.category}</span>
                    </span>
                    <ChevronRight size={16} color="var(--color-text-subtle)" aria-hidden="true" />
                  </button>
                  <button
                    type="button"
                    className="profile-unsave"
                    onClick={() => handleRemoveSaved(p.product_id)}
                    aria-label={`Remove ${p.product_name} from saved items`}
                    title="Remove from Saved"
                  >
                    <Bookmark size={16} fill="currentColor" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </CollapsibleSection>
      </div>
    </div>
  );
}
