import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, AlertTriangle, CheckCircle2, Bookmark, 
  ArrowRight, Scale, Info, ChevronRight, ChevronDown, ChevronUp, Edit3, X, Sliders, RefreshCw, Camera
} from 'lucide-react';
import { useLockBodyScroll } from '../components/useLockBodyScroll';
import ProductImageFallback from '../components/ProductImageFallback';
import { apiFetch } from '../api';
import { isSaved as isProductSaved, recordHistory, toggleSavedProduct } from '../storage';

// Every custom scan shares the id CUSTOM_SCAN, so saved scans are keyed by name and brand instead.
const saveKeyFor = (a) => (a.is_custom ? `CUSTOM:${a.product_name}|${a.brand || ''}` : a.product_id);

// Layer 1 Presentation Helper Functions
const getGradeSummary = (l1) => {
  if (!l1) return '';
  const grade = l1.grade;
  if (grade === 'A') return 'A strong overall nutritional profile with low levels of nutrients to limit.';
  if (grade === 'B') return 'A good nutritional balance with favorable overall values.';
  if (grade === 'C') return 'A moderate nutritional balance with some nutrients to monitor.';
  if (grade === 'D') return 'Contains elevated levels in one or more nutrients of concern.';
  if (grade === 'E') return 'Higher in sugar, sodium, or saturated fat relative to category benchmarks.';
  if (l1.status === 'Insufficient Data') return 'Incomplete nutritional declarations on the packaging prevent an overall grade.';
  if (l1.status === 'Data Contradiction') return 'Conflicting nutrition values on packaging prevent an accurate grade.';
  if (l1.status === 'Uncalibrated Category') return 'Category benchmarks are not yet established for this food type; nutrition panel is displayed without an estimated grade.';
  return l1.explanation || 'Nutritional assessment based on category benchmarks.';
};

const formatNutrientStatus = (rawStatus) => {
  if (!rawStatus) return 'Within benchmark';
  const s = rawStatus.toLowerCase();
  if (s.includes('optimal (0g)')) return 'Zero / Optimal';
  if (s.includes('excessive') || s.includes('>2x')) return 'Well above benchmark';
  if (s.includes('elevated') || s.includes('>threshold')) return 'Above benchmark';
  if (s.includes('optimal') || s.includes('favourable') || s.includes('heart healthy') || s.includes('low')) return 'Low';
  if (s.includes('high') || s.includes('good source')) return 'High';
  if (s.includes('source')) return 'Good source';
  if (s.includes('moderate') || s.includes('within')) return 'Within benchmark';
  return rawStatus.replace(/\([^)]*\)/g, '').trim();
};

const getNutrientLabel = (nutKey) => {
  const map = {
    sugars: 'Sugar',
    sodium: 'Sodium',
    saturated_fat: 'Saturated fat',
    protein: 'Protein',
    fibre: 'Fibre',
    dietary_fibre: 'Dietary fibre',
    total_fat: 'Total fat',
    energy: 'Energy',
    trans_fat: 'Trans fat'
  };
  return map[nutKey] || nutKey.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

const cleanHighlightText = (text) => {
  if (!text) return '';
  return text
    .replace(/\s*—\s*meets Codex[^.]*/gi, '')
    .replace(/\s*relative to regional nutrient guidelines\s*\([^)]*\)/gi, '')
    .replace(/\s*relative to category guidelines\s*\([^)]*\)/gi, '')
    .replace(/\s*above WHO SEARO recommended benchmark\s*\([^)]*\)/gi, ' above benchmark')
    .replace(/\s*—\s*exceeds standard\s*\([^)]*\)\s*by more than double/gi, ' is more than double the benchmark')
    .replace(/\s*—\s*exceeds category threshold\s*\([^)]*\)\s*significantly/gi, ' significantly exceeds the benchmark')
    .replace(/\s*—\s*exceeds category threshold\s*\([^)]*\)\s*by over 100%/gi, ' exceeds the benchmark by over 100%')
    .replace(/\s*supporting cardiovascular health guidelines/gi, '')
    .trim();
};

const deduplicateStandards = (standards) => {
  if (!Array.isArray(standards)) return [];
  const seen = new Set();
  const result = [];
  for (const s of standards) {
    const trimmed = (typeof s === 'string' ? s : s?.standard_name || '').trim();
    if (trimmed && !seen.has(trimmed)) {
      seen.add(trimmed);
      result.push(trimmed);
    }
  }
  return result;
};

export default function ProductAssessment({ 
  productId, 
  assessmentData: initialAssessment, 
  onBack, 
  onSelectProduct, 
  activeProfile,
  onEditCustomData,
  onUpdateAssessment
}) {
  const [assessment, setAssessment] = useState(initialAssessment || null);
  const [loading, setLoading] = useState(!initialAssessment);
  const [alternatives, setAlternatives] = useState([]);
  const [isSaved, setIsSaved] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [savingEdit, setSavingEdit] = useState(false);
  const [showDetailedL1, setShowDetailedL1] = useState(false);
  const [expandedClaimIdx, setExpandedClaimIdx] = useState({});

  // Grounded AI Food Assistant State
  const [assistantQuestion, setAssistantQuestion] = useState('');
  const [assistantLoading, setAssistantLoading] = useState(false);
  const [assistantResponse, setAssistantResponse] = useState(null);

  const handleAskAssistant = (qText) => {
    const q = (qText || assistantQuestion).trim();
    if (!q || !assessment?.product_id) return;
    setAssistantLoading(true);
    setAssistantResponse(null);
    apiFetch('/api/assistant/ask', { method: 'POST', body: { product_id: assessment.product_id, question: q } })
      .then((data) => setAssistantResponse(data))
      .catch((err) => setAssistantResponse({ error: err.message }))
      .finally(() => setAssistantLoading(false));
  };

  const formatBasis = (b) => {
    if (!b) return 'Per 100 g';
    const s = String(b).trim().toLowerCase();
    if (s.includes('100ml') || s.includes('100 ml')) return 'Per 100 ml';
    if (s.includes('100g') || s.includes('100 g')) return 'Per 100 g';
    if (s.includes('serving')) return 'Per Serving';
    return String(b).trim();
  };

  useLockBodyScroll(showEditModal);
  const [editForm, setEditForm] = useState({
    product_name: '',
    brand: '',
    category: 'Snacks',
    serving_size: '100',
    serving_size_unit: 'g',
    measurement_basis: 'per 100g',
    energy_kcal: '',
    carbohydrates_g: '',
    sugars_g: '',
    added_sugars_g: '',
    protein_g: '',
    total_fat_g: '',
    saturated_fat_g: '',
    trans_fat_g: '',
    sodium_mg: '',
    dietary_fibre_g: '',
    ingredients: '',
    allergens_declared: '',
    marketing_claims: ''
  });

  const [loadError, setLoadError] = useState(null);
  const [alternativesError, setAlternativesError] = useState(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    if (initialAssessment) {
      setAssessment(initialAssessment);
      recordHistory(initialAssessment);
      setIsSaved(isProductSaved(saveKeyFor(initialAssessment)));
      setLoading(false);
      return undefined;
    }
    if (!productId) return undefined;

    const controller = new AbortController();
    setLoading(true);
    setLoadError(null);
    setAlternativesError(null);
    apiFetch(`/api/products/${encodeURIComponent(productId)}`, { signal: controller.signal })
      .then((data) => {
        setAssessment(data);
        recordHistory(data);
        setIsSaved(isProductSaved(saveKeyFor(data)));
        setLoading(false);
      })
      .catch((err) => {
        if (err.name === 'AbortError') return;
        setLoadError(err.message);
        setLoading(false);
      });
    apiFetch(`/api/alternatives/${encodeURIComponent(productId)}`, { signal: controller.signal })
      .then((data) => setAlternatives(data.alternatives))
      .catch((err) => {
        if (err.name !== 'AbortError') setAlternativesError(err.message);
      });
    return () => controller.abort();
  }, [productId, initialAssessment, activeProfile, reloadToken]);

  const handleToggleSave = () => {
    if (!assessment?.product_id) return;
    const nf = assessment.nutrition_facts || {};
    try {
      setIsSaved(
        toggleSavedProduct({
          product_id: saveKeyFor(assessment),
          product_name: assessment.product_name,
          brand: assessment.brand,
          category: assessment.category,
          image_small_url: assessment.image_small_url || assessment.image_url || null,
          is_custom: Boolean(assessment.is_custom),
          // Custom scans have no server record, so keep the confirmed values to re-assess later.
          raw_input: assessment.is_custom ? assessment.raw_input : undefined,
          energy_kcal: nf.energy_kcal ?? null,
          sugars_g: nf.sugars_g ?? null,
          sodium_mg: nf.sodium_mg ?? null,
        })
      );
    } catch (err) {
      window.alert(err.message);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '80px 0', textAlign: 'center', color: 'var(--color-text-muted)' }}>
        Generating 3-Layer Food Safety & Nutrition Assessment...
      </div>
    );
  }

  if (loadError || !assessment) {
    return (
      <div role="alert" style={{ padding: '60px 0', textAlign: 'center' }}>
        <h3>We couldn't load this assessment</h3>
        {loadError && <p style={{ color: 'var(--color-text-muted)', marginTop: 8 }}>{loadError}</p>}
        <div style={{ display: 'flex', gap: 10, justifyContent: 'center', marginTop: 16 }}>
          {loadError && (
            <button className="btn-primary" onClick={() => setReloadToken((t) => t + 1)}>Try again</button>
          )}
          <button className="btn-secondary" onClick={onBack}>Back to catalogue</button>
        </div>
      </div>
    );
  }

  const l1 = assessment.layer1_general || {};
  const l2 = assessment.layer2_personalized || {};
  const l3_allg = assessment.layer3_allergens || {};
  const l3_add = assessment.layer3_additives || {};
  const claims = assessment.marketing_claims_analysis || [];
  const nuts = assessment.nutrition_facts || {};

  const isCustom = Boolean(
    initialAssessment || 
    assessment?.is_custom || 
    assessment?.product_id === 'CUSTOM_SCAN' || 
    assessment?.data_confidence_status === 'User-Verified Custom Data' ||
    assessment?.data_source === 'User / OCR Input'
  );

  const openEditModal = () => {
    const raw = assessment?.raw_input || {};
    const nf = assessment?.nutrition_facts || {};
    setEditForm({
      product_name: assessment?.product_name || raw.product_name || '',
      brand: (assessment?.brand && assessment.brand !== 'Custom') ? assessment.brand : (raw.brand || ''),
      category: assessment?.category || raw.category || 'Snacks',
      serving_size: String(assessment?.serving_size || raw.serving_size || 100),
      serving_size_unit: assessment?.serving_size_unit || raw.serving_size_unit || 'g',
      measurement_basis: assessment?.measurement_basis || raw.measurement_basis || 'per 100g',
      energy_kcal: nf.energy_kcal != null ? String(nf.energy_kcal) : (raw.energy_kcal != null ? String(raw.energy_kcal) : ''),
      carbohydrates_g: nf.carbohydrates_g != null ? String(nf.carbohydrates_g) : (raw.carbohydrates_g != null ? String(raw.carbohydrates_g) : ''),
      sugars_g: nf.sugars_g != null ? String(nf.sugars_g) : (raw.sugars_g != null ? String(raw.sugars_g) : ''),
      added_sugars_g: nf.added_sugars_g != null ? String(nf.added_sugars_g) : (raw.added_sugars_g != null ? String(raw.added_sugars_g) : ''),
      protein_g: nf.protein_g != null ? String(nf.protein_g) : (raw.protein_g != null ? String(raw.protein_g) : ''),
      total_fat_g: nf.total_fat_g != null ? String(nf.total_fat_g) : (raw.total_fat_g != null ? String(raw.total_fat_g) : ''),
      saturated_fat_g: nf.saturated_fat_g != null ? String(nf.saturated_fat_g) : (raw.saturated_fat_g != null ? String(raw.saturated_fat_g) : ''),
      trans_fat_g: nf.trans_fat_g != null ? String(nf.trans_fat_g) : (raw.trans_fat_g != null ? String(raw.trans_fat_g) : ''),
      sodium_mg: nf.sodium_mg != null ? String(nf.sodium_mg) : (raw.sodium_mg != null ? String(raw.sodium_mg) : ''),
      dietary_fibre_g: nf.dietary_fibre_g != null ? String(nf.dietary_fibre_g) : (raw.dietary_fibre_g != null ? String(raw.dietary_fibre_g) : ''),
      ingredients: assessment?.ingredients || raw.ingredients || '',
      allergens_declared: assessment?.allergens_declared || raw.allergens_declared || '',
      marketing_claims: assessment?.marketing_claims || raw.marketing_claims || ''
    });
    setShowEditModal(true);
  };

  const handleSaveEditedData = async (e) => {
    e.preventDefault();
    if (!editForm.product_name.trim()) {
      window.alert('Please enter a product name.');
      return;
    }
    setSavingEdit(true);
    const parseNum = (v) => (v === '' || v === null || isNaN(Number(v))) ? null : Number(v);
    const payload = {
      product_name: editForm.product_name,
      brand: editForm.brand || 'Custom',
      category: editForm.category,
      serving_size: parseNum(editForm.serving_size) || 100,
      serving_size_unit: editForm.serving_size_unit,
      measurement_basis: editForm.measurement_basis,
      energy_kcal: parseNum(editForm.energy_kcal),
      carbohydrates_g: parseNum(editForm.carbohydrates_g),
      sugars_g: parseNum(editForm.sugars_g),
      added_sugars_g: parseNum(editForm.added_sugars_g),
      protein_g: parseNum(editForm.protein_g),
      total_fat_g: parseNum(editForm.total_fat_g),
      saturated_fat_g: parseNum(editForm.saturated_fat_g),
      trans_fat_g: parseNum(editForm.trans_fat_g),
      sodium_mg: parseNum(editForm.sodium_mg),
      dietary_fibre_g: parseNum(editForm.dietary_fibre_g),
      ingredients: editForm.ingredients,
      allergens_declared: editForm.allergens_declared,
      marketing_claims: editForm.marketing_claims
    };

    try {
      const newAssessment = await apiFetch('/api/products/assess', { method: 'POST', body: payload });
      setAssessment(newAssessment);
      recordHistory(newAssessment);
      if (onUpdateAssessment) {
        onUpdateAssessment(newAssessment, editForm);
      }
      setShowEditModal(false);
    } catch (err) {
      window.alert(err.message);
    } finally {
      setSavingEdit(false);
    }
  };

  return (
    <div className="product-assessment-page" style={{ maxWidth: 1040, margin: '0 auto' }}>
      {/* Back button and Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, flexWrap: 'wrap', gap: 10 }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <button 
            className="btn-secondary" 
            onClick={isCustom && onEditCustomData ? onEditCustomData : onBack} 
            style={{ padding: '8px 14px', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: 6 }}
          >
            <ArrowLeft size={16} />
            <span>{isCustom ? 'Back to Edit Data' : 'Back to Catalogue'}</span>
          </button>
          {isCustom && (
            <button 
              className="btn-secondary" 
              onClick={onBack} 
              style={{ padding: '8px 14px', fontSize: '0.85rem' }}
            >
              <span>Catalogue</span>
            </button>
          )}
        </div>

        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          {isCustom && (
            <button 
              className="btn-primary" 
              onClick={openEditModal}
              style={{ 
                padding: '8px 16px', 
                fontSize: '0.85rem', 
                display: 'flex', 
                alignItems: 'center', 
                gap: 6,
                background: 'var(--color-primary)',
                fontWeight: 700
              }}
            >
              <Edit3 size={15} />
              <span>Edit Entered Data</span>
            </button>
          )}

          <button 
            className="btn-secondary" 
            onClick={handleToggleSave}
            style={{ padding: '8px 14px', fontSize: '0.85rem', color: isSaved ? '#c62828' : 'inherit' }}
          >
            <Bookmark size={16} fill={isSaved ? '#c62828' : 'none'} />
            <span>{isSaved ? 'Saved to Favorites' : 'Save Product'}</span>
          </button>
        </div>
      </div>

      {/* Hard Safety Alert Banner (Layer 3 Critical Allergen Conflict) */}
      {assessment.safety_override?.allergen_conflict && (
        <div role="alert" style={{
          background: '#ffebee',
          border: '2px solid #c62828',
          borderRadius: 12,
          padding: '18px 24px',
          marginBottom: 24,
          display: 'flex',
          gap: 16,
          alignItems: 'center'
        }}>
          <AlertTriangle size={32} color="#c62828" style={{ flexShrink: 0 }} aria-hidden="true" />
          <div>
            <h3 style={{ color: '#c62828', fontSize: '1.15rem', marginBottom: 4 }}>
              Not suitable for you: contains {assessment.safety_override.allergens.join(', ')}
            </h3>
            <p style={{ color: '#b71c1c', fontSize: '0.88rem', margin: 0 }}>
              {l2.allergen_conflicts.map(c => `${c.allergen}: ${c.status}`).join(' · ')}. You listed{' '}
              {assessment.safety_override.allergens.length > 1 ? 'these' : 'this'} in your profile, so your personal
              score is set to 0 regardless of the nutrition grade.
            </p>
          </div>
        </div>
      )}

      {assessment.safety_override?.allergen_check_incomplete && !assessment.safety_override?.allergen_conflict && (
        <div role="alert" style={{ background: 'var(--color-warning-bg)', border: '2px solid var(--color-warning)', borderRadius: 12, padding: '14px 20px', marginBottom: 24, display: 'flex', gap: 14, alignItems: 'center' }}>
          <AlertTriangle size={26} color="var(--color-warning)" style={{ flexShrink: 0 }} aria-hidden="true" />
          <p style={{ margin: 0, fontSize: '0.9rem', color: '#7a3300' }}>
            <strong>Allergen information is missing for this product.</strong> We can&apos;t check it against the
            allergens in your profile. Read the pack before eating it.
          </p>
        </div>
      )}

      {assessment.profile_source === 'default' && (
        <p style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', marginBottom: 16 }}>
          You haven&apos;t set up a profile on this device, so no allergens or personal goals were applied.
        </p>
      )}

      {/* Quick Edit Banner for Custom Scans */}
      {isCustom && (
        <div style={{
          background: '#f0f9eb',
          border: '1px solid #c8e6c9',
          borderRadius: 8,
          padding: '12px 18px',
          marginBottom: 20,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 10
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Sliders size={18} color="var(--color-primary)" />
            <span style={{ fontSize: '0.85rem', color: 'var(--color-primary)', fontWeight: 600 }}>
              Need to change your entered values or add missing declarations? You can edit and recalculate anytime.
            </span>
          </div>
          <button 
            className="btn-secondary"
            onClick={openEditModal}
            style={{ 
              padding: '6px 14px', 
              fontSize: '0.8rem', 
              background: '#fff', 
              fontWeight: 700, 
              display: 'flex', 
              alignItems: 'center', 
              gap: 6 
            }}
          >
            <Edit3 size={14} />
            <span>Edit Values Now</span>
          </button>
        </div>
      )}

      {/* Product Overview Card */}
      <div className="card" style={{ marginBottom: 24, padding: 28 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 20 }}>
          <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start', flex: 1, minWidth: 280 }}>
            {/* Product Packaging Image / Vector Fallback */}
            <div style={{ flexShrink: 0, width: 110, height: 110 }}>
              {assessment.image_url ? (
                <img 
                  src={assessment.image_url} 
                  alt={assessment.product_name} 
                  onError={(e) => {
                    e.currentTarget.style.display = 'none';
                    const fallback = e.currentTarget.parentElement.querySelector('.assessment-image-fallback');
                    if (fallback) fallback.style.display = 'block';
                  }}
                  style={{ 
                    width: 110, 
                    height: 110, 
                    objectFit: 'contain', 
                    borderRadius: 10, 
                    background: '#fff', 
                    border: '1px solid var(--color-border)', 
                    padding: 6,
                    boxShadow: '0 2px 8px rgba(0,0,0,0.06)'
                  }} 
                />
              ) : null}
              <div 
                className="assessment-image-fallback"
                style={{ 
                  display: assessment.image_url ? 'none' : 'block',
                  width: 110,
                  height: 110
                }}
              >
                <ProductImageFallback
                  category={assessment.category}
                  brand={assessment.brand}
                  productName={assessment.product_name}
                  height={110}
                  width={110}
                />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginBottom: 6 }}>
                <span style={{ fontSize: '0.82rem', fontWeight: 800, color: 'var(--color-accent)', textTransform: 'uppercase' }}>
                  {assessment.brand || 'Brand'}
                </span>
                <span>•</span>
                <span style={{ fontSize: '0.82rem', color: 'var(--color-text-subtle)' }}>
                  {assessment.category} ({assessment.sub_category})
                </span>
                <span className="badge badge-warning" style={{ fontSize: '0.7rem' }} title="How far you can rely on these values">
                  {assessment.data_confidence_status}
                </span>
              </div>
              
              <h1 style={{ fontSize: '2.1rem', color: 'var(--color-primary)', lineHeight: 1.2, marginBottom: 8 }}>
                {assessment.product_name}
              </h1>

              <div style={{ fontSize: '0.8rem', color: 'var(--color-text-subtle)', lineHeight: 1.6 }}>
                {assessment.barcode && (
                  <span style={{ marginRight: 12 }}>
                    Barcode: <strong style={{ fontFamily: 'monospace' }}>{assessment.barcode}</strong>
                  </span>
                )}
                {assessment.quantity && (
                  <span style={{ marginRight: 12 }}>
                    Package: <strong>{assessment.quantity}</strong>
                  </span>
                )}
                <span style={{ marginRight: 12 }}>
                  Basis: <strong>{assessment.measurement_basis || 'per 100g'}</strong>
                </span>
                <span>
                  Serving: {assessment.serving_size || 100}{assessment.serving_size_unit || 'g'}
                </span>
              </div>

              {assessment.data_source && (
                <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
                  Source: <strong>{assessment.data_source}</strong>
                  {assessment.retrieved_at && ` • Retrieved: ${new Date(assessment.retrieved_at).toLocaleDateString()}`}
                </div>
              )}

              {assessment.openfoodfacts_attribution && (
                <div style={{ marginTop: 8, fontSize: '0.75rem', color: 'var(--color-text-muted)', background: '#f8f9fa', border: '1px solid #e9ecef', padding: '4px 10px', borderRadius: 6, display: 'inline-block' }}>
                  {assessment.openfoodfacts_attribution}
                </div>
              )}
            </div>
          </div>

          {/* Quick Dual Score Pill */}
          <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
            {/* General Grade */}
            <div style={{ textAlign: 'center', padding: '10px 16px', background: 'var(--color-surface-alt)', borderRadius: 12, border: '1px solid var(--color-border)', minWidth: 95 }}>
              <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--color-text-subtle)', display: 'block', textTransform: 'uppercase' }}>
                General Grade
              </span>
              {['A', 'B', 'C', 'D', 'E'].includes(l1.grade) ? (
                <span className={`grade-badge grade-${l1.grade}`} style={{ width: 38, height: 38, fontSize: '1.4rem', margin: '4px auto 0' }}>
                  {l1.grade}
                </span>
              ) : (
                <div style={{ marginTop: 2 }}>
                  <span style={{ fontSize: '1.25rem', fontWeight: 800, color: '#757575', display: 'block' }}>N/A</span>
                  <span style={{ fontSize: '0.65rem', color: '#9e9e9e', fontWeight: 600 }}>
                    {l1.status === 'Insufficient Data' ? 'Incomplete' : (l1.status === 'Uncalibrated Category' ? 'Not rated' : 'Pending')}
                  </span>
                </div>
              )}
            </div>

            {/* Personalized Match */}
            <div style={{ textAlign: 'center', padding: '10px 16px', background: 'var(--color-surface-alt)', borderRadius: 12, border: '1px solid var(--color-border)', minWidth: 95 }}>
              <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--color-text-subtle)', display: 'block', textTransform: 'uppercase' }}>
                Goal Match
              </span>
              {l2.personalized_score != null ? (
                <div style={{ fontSize: '1.5rem', fontWeight: 800, color: l2.color === 'red' ? '#c62828' : (l2.color === 'green' ? '#2e7d32' : '#e65100'), marginTop: 2 }}>
                  {l2.personalized_score}/100
                </div>
              ) : (
                <div style={{ marginTop: 2 }}>
                  <span style={{ fontSize: '1.25rem', fontWeight: 800, color: '#757575', display: 'block' }}>N/A</span>
                  <span style={{ fontSize: '0.65rem', color: '#9e9e9e', fontWeight: 600 }}>Incomplete</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Grid: Layer 1 (General) & Layer 2 (Personalized) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 20, marginBottom: 24 }}>
        
        {/* Layer 1: General Nutritional Assessment */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            {/* Header: Title, Grade Badge, and Dynamic Grade Explanation */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, marginBottom: 12 }}>
              <div>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-primary)', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                  Layer 1 — General Nutrition
                </span>
                <h3 style={{ fontSize: '1.25rem', color: 'var(--color-primary)', margin: '4px 0 2px', fontWeight: 800 }}>
                  {l1.grade_label || (['A', 'B', 'C', 'D', 'E'].includes(l1.grade) ? `Grade ${l1.grade}` : 'Overall Grade Unavailable')}
                </h3>
                <p style={{ fontSize: '0.84rem', color: 'var(--color-text-muted)', margin: 0, lineHeight: 1.45 }}>
                  {getGradeSummary(l1)}
                </p>
              </div>

              {['A', 'B', 'C', 'D', 'E'].includes(l1.grade) ? (
                <span className={`grade-badge grade-${l1.grade}`} style={{ width: 38, height: 38, fontSize: '1.35rem', flexShrink: 0 }}>
                  {l1.grade}
                </span>
              ) : (
                <span style={{
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  padding: '4px 10px',
                  borderRadius: 6,
                  flexShrink: 0,
                  background: l1.status === 'Insufficient Data' ? '#fff3e0' : '#f1f5f9',
                  color: l1.status === 'Insufficient Data' ? '#b73800' : '#475569'
                }}>
                  {l1.status === 'Insufficient Data' ? 'Incomplete' : (l1.status === 'Uncalibrated Category' ? 'Not rated' : 'Unavailable')}
                </span>
              )}
            </div>

            {/* Uncalibrated Category Context Notice */}
            {l1.status === 'Uncalibrated Category' && (
              <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: '10px 14px', marginBottom: 14 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Info size={15} color="#64748b" />
                  <span style={{ fontSize: '0.8rem', color: '#334155', fontWeight: 600 }}>
                    Nutrition panel displayed without an estimated letter grade.
                  </span>
                </div>
                <p style={{ fontSize: '0.76rem', color: '#64748b', margin: '6px 0 0', lineHeight: 1.45 }}>
                  Statutory front-of-pack benchmark criteria have not been calibrated for this specific food category. Nutrition declarations are shown for transparency.
                </p>
              </div>
            )}

            {/* Missing Critical Fields Warning */}
            {((l1.missing_fields && l1.missing_fields.length > 0) || (l1.missing_field_labels && l1.missing_field_labels.length > 0)) && (
              <div style={{ background: '#fff3e0', border: '1px solid #ffe0b2', padding: '8px 12px', borderRadius: 6, fontSize: '0.78rem', color: '#b73800', marginBottom: 12 }}>
                ℹ️ <strong>Missing Declarations:</strong> {(l1.missing_field_labels || l1.missing_fields).join(', ')}
              </div>
            )}

            {/* Key Nutrient Summary Cards */}
            {l1.key_contributing_nutrients && Object.keys(l1.key_contributing_nutrients).length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--color-text-subtle)', textTransform: 'uppercase', letterSpacing: '0.04em', display: 'block', marginBottom: 8 }}>
                  Key Nutrients
                </span>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 8 }}>
                  {Object.entries(l1.key_contributing_nutrients).map(([nutKey, data]) => {
                    const statusText = formatNutrientStatus(data.status);
                    const isConcern = data.status?.includes('Excessive') || data.status?.includes('Elevated') || data.status?.includes('Non-compliant');
                    const isPositive = data.status?.includes('High') || data.status?.includes('Optimal') || data.status?.includes('Source') || data.status?.includes('Low');
                    const label = getNutrientLabel(nutKey);

                    return (
                      <div
                        key={nutKey}
                        style={{
                          padding: '8px 10px',
                          borderRadius: 8,
                          border: isConcern ? '1px solid #fed7aa' : (isPositive ? '1px solid #bbf7d0' : '1px solid var(--color-border)'),
                          background: isConcern ? '#fff7ed' : (isPositive ? '#f0fdf4' : 'var(--color-surface-alt)'),
                          display: 'flex',
                          flexDirection: 'column',
                          justifyContent: 'space-between',
                          gap: 2
                        }}
                      >
                        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--color-text-subtle)' }}>
                          {label}
                        </span>
                        <div style={{ fontSize: '0.92rem', fontWeight: 700, color: 'var(--color-primary)' }}>
                          {data.value != null ? `${data.value} ${data.unit || 'g'}` : '—'}
                        </div>
                        <span style={{
                          fontSize: '0.72rem',
                          fontWeight: 600,
                          color: isConcern ? '#c2410c' : (isPositive ? '#15803d' : 'var(--color-text-muted)')
                        }}>
                          {statusText}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Nutritional Highlights: Max 3 positive findings + 1 or 2 important concerns */}
            {((l1.strengths && l1.strengths.length > 0) || (l1.concerns && l1.concerns.length > 0)) && (
              <div style={{ marginBottom: 14 }}>
                <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--color-text-subtle)', textTransform: 'uppercase', letterSpacing: '0.04em', display: 'block', marginBottom: 6 }}>
                  Highlights
                </span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {/* Top <= 3 Positive Findings */}
                  {l1.strengths && l1.strengths.slice(0, 3).map((str, i) => (
                    <div key={`str-${i}`} style={{ display: 'flex', alignItems: 'flex-start', gap: 6, fontSize: '0.82rem', color: '#166534', lineHeight: 1.4 }}>
                      <CheckCircle2 size={15} color="#16a34a" style={{ flexShrink: 0, marginTop: 2 }} />
                      <span>{cleanHighlightText(str)}</span>
                    </div>
                  ))}

                  {/* Top <= 2 Important Concerns */}
                  {l1.concerns && l1.concerns.slice(0, 2).map((con, i) => (
                    <div key={`con-${i}`} style={{ display: 'flex', alignItems: 'flex-start', gap: 6, fontSize: '0.82rem', color: '#9a3412', lineHeight: 1.4 }}>
                      <AlertTriangle size={15} color="#ea580c" style={{ flexShrink: 0, marginTop: 2 }} />
                      <span>{cleanHighlightText(con)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Section 4: Expandable Detailed Assessment for Transparency */}
          <div style={{ marginTop: 12, paddingTop: 10, borderTop: '1px solid var(--color-border)' }}>
            <button
              type="button"
              onClick={() => setShowDetailedL1(prev => !prev)}
              style={{
                width: '100%',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                background: 'none',
                border: 'none',
                padding: '6px 0',
                cursor: 'pointer',
                color: 'var(--color-primary)',
                fontSize: '0.78rem',
                fontWeight: 600
              }}
            >
              <span>{showDetailedL1 ? 'Hide detailed assessment' : 'View detailed assessment'}</span>
              {showDetailedL1 ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>

            {showDetailedL1 && (
              <div style={{ marginTop: 10, padding: 12, background: 'var(--color-surface-alt)', borderRadius: 8, border: '1px solid var(--color-border)', fontSize: '0.76rem', color: 'var(--color-text-main)' }}>
                {/* Methodology & Basis */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10 }}>
                  {l1.methodology_name && (
                    <span style={{ background: '#fff', border: '1px solid var(--color-border)', padding: '2px 8px', borderRadius: 4, fontWeight: 600 }}>
                      ⚖️ {l1.methodology_name}
                    </span>
                  )}
                  {l1.standards_version && l1.standards_version !== 'N/A' && !l1.standards_version.includes('PENDING') && !l1.standards_version.includes('EXCLUSION') && (
                    <span style={{ background: '#eef2ff', border: '1px solid #c7d2fe', padding: '2px 8px', borderRadius: 4, color: '#3730a3', fontWeight: 600 }}>
                      Version: {l1.standards_version}
                    </span>
                  )}
                  {l1.reference_basis && (
                    <span style={{ background: '#fff', border: '1px solid var(--color-border)', padding: '2px 8px', borderRadius: 4, color: 'var(--color-text-muted)' }}>
                      Basis: {formatBasis(l1.reference_basis)}
                    </span>
                  )}
                </div>

                {/* Benchmark Thresholds & Scoring Table */}
                {l1.key_contributing_nutrients && Object.keys(l1.key_contributing_nutrients).length > 0 && (
                  <div style={{ marginBottom: 12 }}>
                    <div style={{ fontWeight: 700, marginBottom: 6, color: 'var(--color-primary)' }}>
                      Nutrient Benchmark Limits & Points
                    </div>
                    <div style={{ overflowX: 'auto' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.72rem' }}>
                        <thead>
                          <tr style={{ borderBottom: '1px solid var(--color-border)', textAlign: 'left', color: 'var(--color-text-subtle)' }}>
                            <th style={{ padding: '4px 6px' }}>Nutrient</th>
                            <th style={{ padding: '4px 6px' }}>Value</th>
                            <th style={{ padding: '4px 6px' }}>Benchmark Limit</th>
                            <th style={{ padding: '4px 6px' }}>Points</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(l1.key_contributing_nutrients).map(([nutKey, data]) => (
                            <tr key={nutKey} style={{ borderBottom: '1px solid rgba(0,0,0,0.04)' }}>
                              <td style={{ padding: '4px 6px', fontWeight: 600 }}>{getNutrientLabel(nutKey)}</td>
                              <td style={{ padding: '4px 6px' }}>{data.value} {data.unit || 'g'}</td>
                              <td style={{ padding: '4px 6px' }}>{data.threshold != null ? `${data.threshold} ${data.unit || 'g'}` : '—'}</td>
                              <td style={{ padding: '4px 6px', fontWeight: 600, color: data.points < 0 ? '#b73800' : (data.points > 0 ? '#1b5e20' : 'inherit') }}>
                                {data.points > 0 ? `+${data.points}` : (data.points < 0 ? `${data.points}` : '0')}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Deduplicated Standards Actually Applied */}
                {deduplicateStandards(l1.standards_applied).length > 0 && (
                  <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid var(--color-border)' }}>
                    <div style={{ fontWeight: 700, marginBottom: 4, color: 'var(--color-primary)' }}>
                      Applicable Standards Referenced:
                    </div>
                    <ul style={{ margin: 0, paddingLeft: 16, lineHeight: 1.45, color: 'var(--color-text-subtle)' }}>
                      {deduplicateStandards(l1.standards_applied).map((std, idx) => (
                        <li key={idx} style={{ marginBottom: 2 }}>{std}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Accuracy & Regulatory Disclaimer */}
                <p style={{ margin: '8px 0 0', fontSize: '0.68rem', color: 'var(--color-text-muted)', lineHeight: 1.4, fontStyle: 'italic' }}>
                  * Benchmark evaluations reflect public health nutrient profiling criteria (e.g. WHO SEARO / FSSAI INR models) to indicate overall nutritional quality and are distinct from statutory regulatory compliance.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Layer 2: Personalized Suitability */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--color-accent)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                LAYER 2 — PERSONALIZED SUITABILITY
              </span>
              <span className="badge badge-verified">
                Goal: {l2.user_goal}
              </span>
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', marginBottom: 14 }}>
              Evaluated independently of statutory food grading, tailored to your active profile goals and dietary preferences.
            </div>

            {/* Incomplete Data State */}
            {(l2.has_insufficient_data || l2.personalized_score == null) ? (
              <div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 8 }}>
                  <span style={{ fontSize: '2.5rem', fontWeight: 800, color: '#757575' }}>
                    N/A
                  </span>
                  <span style={{ fontSize: '1rem', color: 'var(--color-text-subtle)' }}>/ 100</span>
                  <span style={{
                    fontSize: '0.82rem',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: 4,
                    background: '#f5f5f5',
                    color: '#616161'
                  }}>
                    Incomplete Data
                  </span>
                </div>

                <h4 style={{ fontSize: '1.05rem', color: '#c62828', marginBottom: 8 }}>
                  Score Unavailable — Incomplete Nutrition Panel
                </h4>
                
                <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', lineHeight: 1.5, marginBottom: 12 }}>
                  A personalized health score (1–100) cannot be computed because essential nutrition declarations (Energy, Sugars, Sodium, or Saturated Fat) are missing.
                </p>

                {l2.goal_concerns && l2.goal_concerns.length > 0 && (
                  <div style={{ background: '#fff3e0', border: '1px solid #ffe0b2', borderRadius: 6, padding: '10px 12px', fontSize: '0.82rem', color: '#b73800', marginBottom: 14 }}>
                    ℹ️ {l2.goal_concerns[0]}
                  </div>
                )}

                {isCustom && (
                  <button 
                    className="btn-primary" 
                    onClick={openEditModal}
                    style={{ 
                      padding: '8px 16px', 
                      fontSize: '0.82rem', 
                      display: 'inline-flex', 
                      alignItems: 'center', 
                      gap: 6,
                      background: 'var(--color-primary)',
                      fontWeight: 700,
                      borderRadius: 6
                    }}
                  >
                    <Edit3 size={14} />
                    <span>Enter Missing Values Now</span>
                  </button>
                )}
              </div>
            ) : (
              /* Complete Valid Data State */
              <div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 8 }}>
                  <span style={{ fontSize: '2.5rem', fontWeight: 800, color: l2.color === 'red' ? '#c62828' : (l2.color === 'green' ? '#2e7d32' : '#e65100') }}>
                    {l2.personalized_score}
                  </span>
                  <span style={{ fontSize: '1rem', color: 'var(--color-text-subtle)' }}>/ 100</span>
                  <span style={{
                    fontSize: '0.82rem',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: 4,
                    background: l2.color === 'green' ? '#e8f5e9' : (l2.color === 'red' ? '#ffebee' : '#fff3e0'),
                    color: l2.color === 'green' ? '#2e7d32' : (l2.color === 'red' ? '#c62828' : '#e65100')
                  }}>
                    {l2.suitability_badge}
                  </span>
                </div>

                {/* Visual 1–100 Profile Scale Bar */}
                <div style={{ margin: '12px 0 16px 0', background: 'var(--color-surface-alt)', padding: '10px 12px', borderRadius: 8, border: '1px solid var(--color-border)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--color-text-subtle)', textTransform: 'uppercase' }}>
                      Profile Scale (1 = Unhealthy • 100 = Healthiest)
                    </span>
                    <span style={{ fontSize: '0.75rem', fontWeight: 800, color: l2.color === 'red' ? '#c62828' : (l2.color === 'green' ? '#2e7d32' : '#e65100') }}>
                      {l2.personalized_score} / 100
                    </span>
                  </div>
                  
                  {/* Gradient Track with Marker */}
                  <div style={{ position: 'relative', height: 10, borderRadius: 5, background: 'linear-gradient(to right, #d32f2f 0%, #ff9800 40%, #00897b 70%, #2e7d32 100%)', margin: '8px 0' }}>
                    <div style={{
                      position: 'absolute',
                      top: -4,
                      left: `calc(${Math.min(100, Math.max(1, l2.personalized_score))}% - 6px)`,
                      width: 12,
                      height: 18,
                      background: '#1b1b1b',
                      border: '2px solid #ffffff',
                      borderRadius: 3,
                      boxShadow: '0 2px 4px rgba(0,0,0,0.35)',
                      transition: 'left 0.3s ease'
                    }} title={`Score: ${l2.personalized_score}/100`} />
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--color-text-subtle)', marginTop: 2 }}>
                    <span><strong>1</strong> Unhealthy</span>
                    <span><strong>50</strong> Moderate</span>
                    <span><strong>100</strong> Healthiest</span>
                  </div>
                </div>

                <h4 style={{ fontSize: '1.05rem', color: 'var(--color-primary)', marginBottom: 8 }}>
                  {l2.suitability_status}
                </h4>

                {/* Goal Strengths */}
                {l2.goal_strengths && l2.goal_strengths.length > 0 && (
                  <div style={{ marginBottom: 10 }}>
                    <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#2e7d32', display: 'block', marginBottom: 4 }}>
                      Why this fits '{l2.user_goal}':
                    </span>
                    <ul style={{ margin: 0, paddingLeft: 18, fontSize: '0.82rem', color: '#1b5e20' }}>
                      {l2.goal_strengths.map((gs, i) => <li key={i}>{gs}</li>)}
                    </ul>
                  </div>
                )}

                {/* Goal Concerns */}
                {l2.goal_concerns && l2.goal_concerns.length > 0 && (
                  <div style={{ marginBottom: 10 }}>
                    <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#e65100', display: 'block', marginBottom: 4 }}>
                      Concerns for '{l2.user_goal}':
                    </span>
                    <ul style={{ margin: 0, paddingLeft: 18, fontSize: '0.82rem', color: '#b73800' }}>
                      {l2.goal_concerns.map((gc, i) => <li key={i}>{gc}</li>)}
                    </ul>
                  </div>
                )}

                {/* Rules Applied */}
                {l2.rules_applied && l2.rules_applied.length > 0 && (
                  <div style={{ background: 'var(--color-surface-alt)', borderRadius: 8, padding: 10, marginTop: 12 }}>
                    <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--color-text-subtle)', textTransform: 'uppercase' }}>
                      Transparent Rule Points
                    </span>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
                      {l2.rules_applied.map((r, i) => (
                        <span key={i} style={{ fontSize: '0.72rem', background: '#fff', border: '1px solid var(--color-border)', padding: '2px 6px', borderRadius: 4 }}>
                          {r}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          <div style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid var(--color-border)', fontSize: '0.72rem', color: 'var(--color-text-subtle)' }}>
            Dietary preference checked: {l2.dietary_preference}
          </div>
        </div>
      </div>

      {/* Step-by-Step Transparent Score Calculation Ledger (1–100 Scale) */}
      {l2.calculation_breakdown && l2.calculation_breakdown.steps && (
        <div className="card" style={{ marginBottom: 24, padding: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12, marginBottom: 16 }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <Scale size={20} color="var(--color-primary)" />
                <h3 style={{ fontSize: '1.25rem', color: 'var(--color-primary)', margin: 0 }}>
                  How This Score Was Calculated (1 to 100 Scale)
                </h3>
              </div>
              <p style={{ fontSize: '0.84rem', color: 'var(--color-text-muted)', margin: 0 }}>
                Transparent mathematical ledger evaluated for active profile: <strong>{l2.user_goal}</strong> (Base: 70 pts).
              </p>
            </div>

            {/* Scale Gauge Legend */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: 'var(--color-surface-alt)', padding: '6px 12px', borderRadius: 8, border: '1px solid var(--color-border)' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)' }}>Score Scale:</span>
              <span style={{ fontSize: '0.8rem', fontWeight: 800, color: '#c62828' }}>1 (Unhealthy)</span>
              <ArrowRight size={13} color="var(--color-text-subtle)" />
              <span style={{ fontSize: '0.8rem', fontWeight: 800, color: '#2e7d32' }}>100 (Healthiest)</span>
            </div>
          </div>

          {/* Steps Table */}
          <div className="responsive-table-wrapper">
            <table style={{ width: '100%', minWidth: 580, borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ background: 'var(--color-surface-alt)', borderBottom: '2px solid var(--color-border)' }}>
                  <th style={{ padding: '10px 14px', width: 60, color: 'var(--color-text-subtle)' }}>Step</th>
                  <th style={{ padding: '10px 14px', color: 'var(--color-text-subtle)' }}>Factor / Metric</th>
                  <th style={{ padding: '10px 14px', color: 'var(--color-text-subtle)' }}>Packaging Declaration</th>
                  <th style={{ padding: '10px 14px', color: 'var(--color-text-subtle)' }}>Evaluation Rule Applied</th>
                  <th style={{ padding: '10px 14px', textAlign: 'center', color: 'var(--color-text-subtle)' }}>Points</th>
                  <th style={{ padding: '10px 14px', textAlign: 'right', color: 'var(--color-text-subtle)' }}>Running Total</th>
                </tr>
              </thead>
              <tbody>
                {l2.calculation_breakdown.steps.map((st, idx) => {
                  const isBase = st.type === 'base';
                  const isFinal = st.type === 'final';
                  const isBonus = st.type === 'bonus';
                  const isPenalty = st.type === 'penalty';
                  const isOverride = st.type === 'override';
                  return (
                    <tr 
                      key={idx} 
                      style={{ 
                        borderBottom: '1px solid var(--color-border)',
                        background: isFinal ? '#f0f9eb' : (isBase ? '#f8f9fa' : 'transparent'),
                        fontWeight: (isBase || isFinal) ? 700 : 'normal'
                      }}
                    >
                      <td style={{ padding: '10px 14px', color: 'var(--color-text-subtle)' }}>
                        {isFinal ? '🏁' : `#${st.step || idx + 1}`}
                      </td>
                      <td style={{ padding: '10px 14px', color: 'var(--color-primary)' }}>
                        <strong>{st.factor}</strong>
                      </td>
                      <td style={{ padding: '10px 14px', fontFamily: 'monospace', fontSize: '0.82rem' }}>
                        {st.metric}
                      </td>
                      <td style={{ padding: '10px 14px', color: 'var(--color-text-muted)' }}>
                        <div>{st.rule}</div>
                        {st.threshold_source && (
                          <div style={{ fontSize: '0.7rem', color: 'var(--color-text-subtle)', marginTop: 2 }}>
                            Ref: {st.threshold_source}
                          </div>
                        )}
                      </td>
                      <td style={{ padding: '10px 14px', textAlign: 'center' }}>
                        <span style={{
                          display: 'inline-block',
                          padding: '2px 8px',
                          borderRadius: 4,
                          fontSize: '0.82rem',
                          fontWeight: 700,
                          background: isBonus ? '#e8f5e9' : (isPenalty ? '#ffebee' : (isOverride ? '#fff3e0' : '#f5f5f5')),
                          color: isBonus ? '#2e7d32' : (isPenalty ? '#c62828' : (isOverride ? '#e65100' : 'var(--color-primary)'))
                        }}>
                          {st.points_str}
                        </span>
                      </td>
                      <td style={{ padding: '10px 14px', textAlign: 'right', fontFamily: 'monospace', fontSize: '0.95rem', fontWeight: 800 }}>
                        <span style={{ color: isFinal ? (l2.color === 'red' ? '#c62828' : (l2.color === 'green' ? '#2e7d32' : '#e65100')) : 'inherit' }}>
                          {st.running_total} {isFinal && '/ 100'}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Formula Summary Footnote */}
          <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid var(--color-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--color-text-subtle)' }}>
              Formula: <strong>Base Neutral (70)</strong> + Target Goal Rewards - High Concern Penalties ➔ Clamped [1, 100]
            </div>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--color-primary)' }}>
              Personalized Nutrition Score: <span style={{ color: l2.color === 'red' ? '#c62828' : (l2.color === 'green' ? '#2e7d32' : '#e65100') }}>{l2.personalized_score} / 100</span> ({l2.suitability_badge})
            </div>
          </div>
        </div>
      )}

      {/* External Community Indicators (Open Food Facts) if present */}
      {assessment.source_indicators && (assessment.source_indicators.nutriscore_grade || assessment.source_indicators.nova_group) && (
        <div className="card" style={{ marginBottom: 24, padding: 18, background: '#f8fafc', border: '1px solid #e2e8f0' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
            <div>
              <span style={{ fontSize: '0.72rem', fontWeight: 800, color: 'var(--color-text-subtle)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                External Source Ratings (Open Food Facts Community)
              </span>
              <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', margin: '2px 0 0' }}>
                Supplied by Open Food Facts; separate from EATGOOD's own assessment.
              </p>
            </div>

            <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
              {assessment.source_indicators.nutriscore_grade && (
                <div style={{ textAlign: 'center', padding: '6px 12px', background: '#fff', borderRadius: 8, border: '1px solid #cbd5e1' }}>
                  <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--color-text-subtle)', display: 'block' }}>
                    Nutri-Score
                  </span>
                  <span style={{ fontSize: '1.1rem', fontWeight: 800, color: '#0284c7' }}>
                    Grade {assessment.source_indicators.nutriscore_grade}
                  </span>
                </div>
              )}

              {assessment.source_indicators.nova_group && (
                <div style={{ textAlign: 'center', padding: '6px 12px', background: '#fff', borderRadius: 8, border: '1px solid #cbd5e1' }}>
                  <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--color-text-subtle)', display: 'block' }}>
                    NOVA Group
                  </span>
                  <span style={{ fontSize: '1.1rem', fontWeight: 800, color: assessment.source_indicators.nova_group >= 4 ? '#e11d48' : '#16a34a' }}>
                    Group {assessment.source_indicators.nova_group}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Nutrition Facts Breakdown Table */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 8 }}>
          <h3 style={{ fontSize: '1.2rem', color: 'var(--color-primary)', margin: 0 }}>
            Nutritional Panel ({assessment.measurement_basis || 'per 100g'})
          </h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)', background: 'var(--color-surface-alt)', padding: '4px 10px', borderRadius: 6 }}>
            Serving: {assessment.serving_size || 100}{assessment.serving_size_unit || 'g'}
          </span>
        </div>
        
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: 12,
          textAlign: 'center'
        }}>
          {[
            { label: 'Energy', val: nuts.energy_kcal, unit: 'kcal' },
            { label: 'Carbohydrates', val: nuts.carbohydrates_g, unit: 'g' },
            { label: 'Total Sugars', val: nuts.sugars_g, unit: 'g', concern: nuts.sugars_g > 10 },
            { label: 'Added Sugars', val: nuts.added_sugars_g, unit: 'g' },
            { label: 'Protein', val: nuts.protein_g, unit: 'g', good: nuts.protein_g >= 10 },
            { label: 'Total Fat', val: nuts.total_fat_g, unit: 'g' },
            { label: 'Saturated Fat', val: nuts.saturated_fat_g, unit: 'g', concern: nuts.saturated_fat_g > 4 },
            { label: 'Trans Fat', val: nuts.trans_fat_g, unit: 'g', concern: nuts.trans_fat_g > 0.1 },
            { label: 'Sodium', val: nuts.sodium_mg, unit: 'mg', concern: nuts.sodium_mg > 400 },
            { label: 'Dietary Fibre', val: nuts.dietary_fibre_g, unit: 'g', good: nuts.dietary_fibre_g >= 6 }
          ].map(item => (
            <div key={item.label} style={{
              background: 'var(--color-surface-alt)',
              padding: '12px 10px',
              borderRadius: 8,
              border: item.concern ? '1px solid #ffcc80' : (item.good ? '1px solid #c8e6c9' : '1px solid var(--color-border)')
            }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)', display: 'block', marginBottom: 4 }}>
                {item.label}
              </span>
              <strong style={{
                fontSize: '1.15rem',
                color: item.concern ? '#e65100' : (item.good ? '#2e7d32' : 'var(--color-primary)')
              }}>
                {item.val != null ? `${item.val} ${item.unit}` : 'Not declared'}
              </strong>
            </div>
          ))}
        </div>
      </div>

      {/* Packaging Photo Evidence Gallery (When Available from Open Food Facts) */}
      {(assessment.image_url || assessment.image_ingredients_url || assessment.image_nutrition_url) && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Camera size={18} color="var(--color-primary)" />
              <h3 style={{ fontSize: '1.2rem', color: 'var(--color-primary)', margin: 0 }}>
                Packaging Photo Evidence
              </h3>
            </div>
            <span style={{ fontSize: '0.72rem', color: 'var(--color-text-subtle)', background: 'var(--color-surface-alt)', padding: '3px 8px', borderRadius: 6 }}>
              Open Food Facts (ODbL License)
            </span>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: 16
          }}>
            {assessment.image_url && (
              <div style={{ background: '#f8f9fa', border: '1px solid var(--color-border)', borderRadius: 8, padding: 12, textAlign: 'center' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-text-subtle)', display: 'block', marginBottom: 8, textTransform: 'uppercase' }}>
                  Front of Pack
                </span>
                <a href={assessment.image_url} target="_blank" rel="noopener noreferrer">
                  <img
                    src={assessment.image_url}
                    alt="Front of Pack"
                    style={{ width: '100%', height: 160, objectFit: 'contain', borderRadius: 4, background: '#fff' }}
                  />
                </a>
                <span style={{ fontSize: '0.7rem', color: 'var(--color-text-subtle)', display: 'block', marginTop: 6 }}>
                  Click to view full photo ↗
                </span>
              </div>
            )}

            {assessment.image_ingredients_url && (
              <div style={{ background: '#f8f9fa', border: '1px solid var(--color-border)', borderRadius: 8, padding: 12, textAlign: 'center' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-text-subtle)', display: 'block', marginBottom: 8, textTransform: 'uppercase' }}>
                  Ingredients Label
                </span>
                <a href={assessment.image_ingredients_url} target="_blank" rel="noopener noreferrer">
                  <img
                    src={assessment.image_ingredients_url}
                    alt="Ingredients Label"
                    style={{ width: '100%', height: 160, objectFit: 'contain', borderRadius: 4, background: '#fff' }}
                  />
                </a>
                <span style={{ fontSize: '0.7rem', color: 'var(--color-text-subtle)', display: 'block', marginTop: 6 }}>
                  Click to view full photo ↗
                </span>
              </div>
            )}

            {assessment.image_nutrition_url && (
              <div style={{ background: '#f8f9fa', border: '1px solid var(--color-border)', borderRadius: 8, padding: 12, textAlign: 'center' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-text-subtle)', display: 'block', marginBottom: 8, textTransform: 'uppercase' }}>
                  Nutrition Facts Table
                </span>
                <a href={assessment.image_nutrition_url} target="_blank" rel="noopener noreferrer">
                  <img
                    src={assessment.image_nutrition_url}
                    alt="Nutrition Table"
                    style={{ width: '100%', height: 160, objectFit: 'contain', borderRadius: 4, background: '#fff' }}
                  />
                </a>
                <span style={{ fontSize: '0.7rem', color: 'var(--color-text-subtle)', display: 'block', marginTop: 6 }}>
                  Click to view full photo ↗
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Layer 3: Ingredients & Allergen Analysis */}
      <div className="card" style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: '1.2rem', color: 'var(--color-primary)', marginBottom: 12 }}>
          Layer 3 — Ingredients, Allergens & Additive Safety
        </h3>

        {/* Ingredients Text */}
        <div style={{ marginBottom: 18 }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--color-text-subtle)', textTransform: 'uppercase' }}>
            Ingredients List
          </span>
          <p style={{ fontSize: '0.85rem', color: 'var(--color-text-main)', background: 'var(--color-surface-alt)', padding: 12, borderRadius: 8, marginTop: 4, lineHeight: 1.5 }}>
            {assessment.ingredients || 'Ingredients list not provided on package.'}
          </p>
        </div>

        {/* Allergens Table */}
        <div style={{ marginBottom: 20 }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--color-text-subtle)', textTransform: 'uppercase', display: 'block', marginBottom: 8 }}>
            Allergen Status Breakdown
          </span>

          {l3_allg.detected_allergens && l3_allg.detected_allergens.length > 0 ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10 }}>
              {l3_allg.detected_allergens.map((allg, i) => (
                <div key={i} style={{
                  padding: 10,
                  borderRadius: 8,
                  border: allg.conflicts_user ? '1px solid #c62828' : '1px solid var(--color-border)',
                  background: allg.conflicts_user ? '#ffebee' : '#fff'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong style={{ fontSize: '0.85rem', color: allg.conflicts_user ? '#c62828' : 'inherit' }}>
                      {allg.allergen}
                    </strong>
                    <span style={{ fontSize: '0.7rem', fontWeight: 700, color: allg.conflicts_user ? '#c62828' : '#e65100' }}>
                      {allg.status}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
                    {allg.evidence?.join(', ')}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ fontSize: '0.82rem', color: '#2e7d32', background: '#e8f5e9', padding: 10, borderRadius: 6 }}>
              ✓ No major declared allergens detected in text. (Always verify package markings for cross-contact).
            </div>
          )}
        </div>

        {/* Additives List */}
        {l3_add.additives_list && l3_add.additives_list.length > 0 && (
          <div>
            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--color-text-subtle)', textTransform: 'uppercase', display: 'block', marginBottom: 8 }}>
              Permitted Additives (Authoritative Regulatory Context)
            </span>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 8 }}>
              {l3_add.additives_list.map((add, i) => (
                <div key={i} style={{ background: 'var(--color-surface-alt)', padding: 10, borderRadius: 6, fontSize: '0.78rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700 }}>
                    <span>{add.code} — {add.name}</span>
                    <span style={{ color: 'var(--color-text-subtle)' }}>{add.functional_class}</span>
                  </div>
                  <p style={{ margin: '4px 0 0', color: 'var(--color-text-muted)', fontSize: '0.74rem' }}>
                    {add.regulatory_context}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Front-of-Pack Marketing Claim Auditor */}
      {claims.length > 0 && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 8 }}>
            <div>
              <h3 style={{ fontSize: '1.2rem', color: 'var(--color-primary)', margin: 0 }}>
                Front-of-Pack Marketing Claim Auditor
              </h3>
              <p style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', margin: '2px 0 0' }}>
                Compares the claims printed on the pack with the nutrition values, using criteria informed by FSSAI and Codex documents.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {claims.map((cl, i) => {
              const compStatus = cl.compliance_status || cl.status;
              const isConsistent = compStatus === 'Consistent with available data' || compStatus === 'Consistent with the checked criteria';
              const isInconsistent = compStatus === 'Potential inconsistency' || compStatus === 'Potentially inconsistent with the checked criteria';
              const isInsufficient = compStatus === 'Insufficient evidence to assess compliance' || compStatus === 'Needs verification';
              const isReviewRequired = compStatus === 'Potential concern — review required';
              const isSensory = compStatus?.includes('non-statutory sensory claim') || compStatus === 'Descriptive / Sensory Claim';

              let borderColor = 'var(--color-border)';
              let bgColor = '#fff';
              let badgeColor = '#56695e';
              let badgeBg = '#f1f5ef';

              if (isConsistent) {
                borderColor = '#a5d6a7';
                bgColor = '#f1f8e9';
                badgeColor = '#2e7d32';
                badgeBg = '#e8f5e9';
              } else if (isInconsistent) {
                borderColor = '#ef9a9a';
                bgColor = '#ffebee';
                badgeColor = '#c62828';
                badgeBg = '#ffebee';
              } else if (isReviewRequired) {
                borderColor = '#ffcc80';
                bgColor = '#fff8e1';
                badgeColor = '#e65100';
                badgeBg = '#fff3e0';
              } else if (isInsufficient) {
                borderColor = '#ffe082';
                bgColor = '#fffde7';
                badgeColor = '#f57f17';
                badgeBg = '#fff8e1';
              } else if (isSensory) {
                borderColor = '#cfd8dc';
                bgColor = '#f8fafc';
                badgeColor = '#455a64';
                badgeBg = '#eceff1';
              }

              return (
                <div key={i} style={{
                  border: `1px solid ${borderColor}`,
                  background: bgColor,
                  padding: '16px',
                  borderRadius: 10,
                  boxShadow: 'var(--shadow-sm)'
                }}>
                  {/* Top Bar: Claim Text & Status Badge */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 8, marginBottom: 8 }}>
                    <div>
                      <span style={{ fontSize: '1.02rem', fontWeight: 800, color: 'var(--color-text-main)' }}>
                        "{cl.claim || cl.original_claim}"
                      </span>
                      {/* Detected Taxonomy Types */}
                      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 4 }}>
                        {(cl.detected_claim_types || [cl.primary_claim_type || "Marketing Claim"]).map((type, tIdx) => (
                          <span key={tIdx} style={{
                            fontSize: '0.72rem',
                            fontWeight: 700,
                            padding: '2px 8px',
                            borderRadius: 12,
                            background: 'var(--color-primary)',
                            color: '#fff'
                          }}>
                            {type}
                          </span>
                        ))}
                      </div>
                    </div>

                    <span style={{
                      fontSize: '0.75rem',
                      fontWeight: 800,
                      color: badgeColor,
                      background: badgeBg,
                      padding: '4px 10px',
                      borderRadius: 6,
                      border: `1px solid ${borderColor}`
                    }}>
                      {compStatus}
                    </span>
                  </div>

                  {/* Evidence Available */}
                  <div style={{ fontSize: '0.8rem', color: 'var(--color-text-main)', marginBottom: 4 }}>
                    <strong>Evidence:</strong> {cl.evidence_available || cl.evidence}
                  </div>

                  {/* Explanation Narrative */}
                  {cl.explanation && (
                    <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', margin: '4px 0 6px', lineHeight: 1.45 }}>
                      {cl.explanation}
                    </p>
                  )}

                  {/* Missing Information Callout */}
                  {cl.missing_information && cl.missing_information.length > 0 && (
                    <div style={{ background: 'rgba(0,0,0,0.03)', padding: '6px 10px', borderRadius: 6, margin: '6px 0', fontSize: '0.74rem' }}>
                      <strong style={{ color: '#b71c1c' }}>Missing for substantiation:</strong> {cl.missing_information.join('; ')}
                    </div>
                  )}

                  {/* Expandable Regulatory Citation & Requirements */}
                  {(cl.regulatory_source || cl.classification_rationale || cl.evidence_required) && (
                    <div style={{ marginTop: 6, borderTop: '1px solid rgba(0,0,0,0.06)', paddingTop: 6 }}>
                      <button
                        type="button"
                        onClick={() => setExpandedClaimIdx(prev => ({ ...prev, [i]: !prev[i] }))}
                        style={{
                          background: 'none',
                          border: 'none',
                          padding: 0,
                          fontSize: '0.74rem',
                          fontWeight: 600,
                          color: 'var(--color-primary)',
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 4
                        }}
                      >
                        <span>{expandedClaimIdx[i] ? 'Hide regulatory reference' : 'Regulatory reference & requirements ▾'}</span>
                      </button>

                      {expandedClaimIdx[i] && (
                        <div style={{ marginTop: 6, fontSize: '0.72rem', color: 'var(--color-text-muted)', lineHeight: 1.4 }}>
                          {cl.classification_rationale && (
                            <div style={{ marginBottom: 4 }}>
                              <strong>Rationale:</strong> {cl.classification_rationale}
                            </div>
                          )}
                          {cl.evidence_required && (
                            <div style={{ marginBottom: 4 }}>
                              <strong>Evidence Required:</strong> {cl.evidence_required}
                            </div>
                          )}
                          {(cl.regulatory_source || cl.criterion_applied) && (
                            <div>
                              <strong>Statutory Benchmark:</strong> {cl.regulatory_source || cl.criterion_applied}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
          
          <div style={{ marginTop: 12, fontSize: '0.72rem', color: 'var(--color-text-subtle)', textAlign: 'right' }}>
            Automated claim auditing evaluates available packaging data against benchmark criteria. It does not constitute a formal legal or regulatory determination.
          </div>
        </div>
      )}

      {/* Healthier Alternatives */}
      {alternativesError && (
        <div role="alert" className="card" style={{ marginBottom: 24, color: '#c62828', fontSize: '0.88rem' }}>
          Healthier alternatives couldn&apos;t be loaded: {alternativesError}
        </div>
      )}
      {alternatives.length > 0 && (
        <div className="card" style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <div>
              <h3 style={{ fontSize: '1.25rem', color: 'var(--color-primary)' }}>
                Goal-Aligned Healthier Alternatives
              </h3>
              <p style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', marginTop: 2 }}>
                Same category substitutes respecting your dietary preferences and strictly excluding allergens.
              </p>
            </div>
            <span className="badge badge-verified">
              Goal: {activeProfile?.goal || 'Balanced Choices'}
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: 14 }}>
            {alternatives.map(alt => (
              <div 
                key={alt.product_id}
                style={{
                  border: '1px solid var(--color-border)',
                  borderRadius: 8,
                  padding: 14,
                  background: '#fff',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  boxShadow: 'var(--shadow-sm)'
                }}
              >
                <div>
                  <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', marginBottom: 8 }}>
                    {(alt.image_small_url || alt.image_url) && (
                      <img
                        src={alt.image_small_url || alt.image_url}
                        alt={alt.product_name}
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
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 }}>
                        <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--color-text-subtle)' }}>
                          {alt.brand}
                        </span>
                        <span className={`grade-badge grade-${alt.general_grade || 'NA'}`} style={{ width: 22, height: 22, fontSize: '0.75rem' }}>
                          {alt.general_grade || 'NA'}
                        </span>
                      </div>
                      <h4 style={{ fontSize: '0.92rem', color: 'var(--color-primary)', margin: 0, lineHeight: 1.25 }}>
                        {alt.product_name}
                      </h4>
                    </div>
                  </div>

                  <div style={{ fontSize: '0.78rem', color: '#2e7d32', fontWeight: 700, marginBottom: 8 }}>
                    Suitability Score: {alt.personalized_score != null ? `${alt.personalized_score}/100` : 'N/A'}
                  </div>

                  <ul style={{ margin: 0, paddingLeft: 16, fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                    {alt.comparative_advantages?.map((adv, i) => (
                      <li key={i}>{adv}</li>
                    ))}
                  </ul>
                </div>

                <button
                  className="btn-accent"
                  style={{ width: '100%', marginTop: 12, padding: '6px 10px', fontSize: '0.78rem', justifyContent: 'center' }}
                  onClick={() => onSelectProduct(alt.product_id)}
                >
                  <span>Inspect Alternative</span>
                  <ChevronRight size={12} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Rule-based product Q&A */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div>
            <h3 style={{ fontSize: '1.25rem', color: 'var(--color-primary)', display: 'flex', alignItems: 'center', gap: 8, margin: 0 }}>
              <span>Ask about this product</span>
              <span className="badge badge-neutral" style={{ fontSize: '0.7rem' }}>Rule-based answers</span>
            </h3>
            <p style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
              Answers are generated by fixed rules from this product&apos;s values, the thresholds shown above and your profile. They are not written by an AI model and are not medical advice.
            </p>
          </div>
        </div>

        {/* Quick query chips */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 14 }}>
          {[
            'Is this suitable for a diabetic?',
            'Why did this get its current score?',
            'Is this high in sodium for blood pressure?',
            'Can I eat this with an allergy?'
          ].map((promptText, idx) => (
            <button
              key={idx}
              type="button"
              className="btn-secondary"
              onClick={() => {
                setAssistantQuestion(promptText);
                handleAskAssistant(promptText);
              }}
              style={{ fontSize: '0.78rem', padding: '6px 12px', borderRadius: 20 }}
            >
              💬 {promptText}
            </button>
          ))}
        </div>

        {/* Input box */}
        <form onSubmit={(e) => { e.preventDefault(); handleAskAssistant(); }} style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
          <input
            type="text"
            placeholder="Ask anything about this food (e.g. Does this have too much salt? Is it good for workout recovery?)..."
            value={assistantQuestion}
            onChange={(e) => setAssistantQuestion(e.target.value)}
            style={{
              flex: 1,
              padding: '10px 14px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--color-border)',
              fontSize: '0.9rem'
            }}
          />
          <button
            type="submit"
            className="btn-primary"
            disabled={assistantLoading || !assistantQuestion.trim()}
            style={{ padding: '10px 18px', fontSize: '0.9rem' }}
          >
            {assistantLoading ? 'Evaluating...' : 'Ask Assistant'}
          </button>
        </form>

        {/* Answer Display */}
        {assistantResponse?.error && (
          <p role="alert" style={{ color: '#c62828', fontSize: '0.88rem' }}>{assistantResponse.error}</p>
        )}
        {assistantResponse && !assistantResponse.error && (
          <div style={{
            background: 'var(--color-surface-alt)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--color-border)',
            padding: 16
          }}>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--color-primary)', marginBottom: 8 }}>
              Q: "{assistantResponse.question}"
            </div>
            <div style={{ fontSize: '0.88rem', color: 'var(--color-text-main)', lineHeight: 1.5, whiteSpace: 'pre-wrap', marginBottom: 12 }}>
              {assistantResponse.answer}
            </div>

            {/* Evidence Citations */}
            {assistantResponse.evidence_citations?.length > 0 && (
              <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: 10, display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--color-text-subtle)' }}>
                  SOURCES USED:
                </span>
                {assistantResponse.evidence_citations.map((cite, i) => (
                  <span key={i} className="badge badge-neutral" style={{ fontSize: '0.72rem' }}>
                    {cite}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Transparency & Limitations */}
      <div style={{
        background: '#fff',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        padding: 20,
        fontSize: '0.8rem',
        color: 'var(--color-text-muted)'
      }}>
        <div style={{ fontWeight: 700, color: 'var(--color-primary)', marginBottom: 4 }}>
          Assessment Data Transparency & Evidence
        </div>
        <div>
          Data Source: {assessment.transparency?.data_source} • Data Quality: {assessment.data_confidence_status}
        </div>
        <div style={{ marginTop: 4 }}>
          {assessment.transparency?.assessment_disclaimer}
        </div>
      </div>

      {/* In-page Edit Modal for Custom Data */}
      {showEditModal && (
        <div 
          className="modal-overlay" 
          onClick={() => setShowEditModal(false)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.55)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 20
          }}
        >
          <div 
            className="modal-card" 
            onClick={e => e.stopPropagation()} 
            style={{
              background: '#fff',
              borderRadius: 12,
              maxWidth: 720,
              width: '100%',
              maxHeight: '90vh',
              overflowY: 'auto',
              overscrollBehavior: 'contain',
              padding: 24,
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.15)'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, borderBottom: '1px solid var(--color-border)', paddingBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Edit3 size={20} color="var(--color-primary)" />
                <h3 style={{ fontSize: '1.25rem', color: 'var(--color-primary)', margin: 0 }}>
                  Edit Entered Nutrition & Ingredients
                </h3>
              </div>
              <button 
                onClick={() => setShowEditModal(false)} 
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSaveEditedData}>
              {/* Product Info */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 14 }}>
                <div>
                  <label style={{ fontSize: '0.8rem', fontWeight: 700, display: 'block', marginBottom: 4 }}>
                    Product Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={editForm.product_name}
                    onChange={e => setEditForm({ ...editForm, product_name: e.target.value })}
                    style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid var(--color-border)', fontSize: '0.9rem' }}
                  />
                </div>
                <div>
                  <label style={{ fontSize: '0.8rem', fontWeight: 700, display: 'block', marginBottom: 4 }}>
                    Brand
                  </label>
                  <input
                    type="text"
                    value={editForm.brand}
                    onChange={e => setEditForm({ ...editForm, brand: e.target.value })}
                    placeholder="e.g. Haldiram's"
                    style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid var(--color-border)', fontSize: '0.9rem' }}
                  />
                </div>
              </div>

              {/* Category, Serving Size, Basis */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 12, marginBottom: 16 }}>
                <div>
                  <label style={{ fontSize: '0.8rem', fontWeight: 700, display: 'block', marginBottom: 4 }}>
                    Category
                  </label>
                  <select
                    value={editForm.category}
                    onChange={e => setEditForm({ ...editForm, category: e.target.value })}
                    style={{ width: '100%', padding: '8px 10px', borderRadius: 6, border: '1px solid var(--color-border)', fontSize: '0.88rem' }}
                  >
                    <option value="Snacks">Snacks</option>
                    <option value="Breakfast Cereals">Breakfast Cereals</option>
                    <option value="Packaged Beverages">Packaged Beverages</option>
                    <option value="Biscuits & Bakery">Biscuits & Bakery</option>
                    <option value="Chocolates & Sweets">Chocolates & Sweets</option>
                    <option value="Condiments & Spreads">Condiments & Spreads</option>
                    <option value="Dairy">Dairy</option>
                    <option value="Instant Foods">Instant Foods</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '0.8rem', fontWeight: 700, display: 'block', marginBottom: 4 }}>
                    Serving Size
                  </label>
                  <div style={{ display: 'flex', gap: 4 }}>
                    <input
                      type="number"
                      step="any"
                      value={editForm.serving_size}
                      onChange={e => setEditForm({ ...editForm, serving_size: e.target.value })}
                      style={{ flex: 2, padding: '8px 10px', borderRadius: 6, border: '1px solid var(--color-border)', fontSize: '0.88rem' }}
                    />
                    <select
                      value={editForm.serving_size_unit}
                      onChange={e => setEditForm({ ...editForm, serving_size_unit: e.target.value })}
                      style={{ flex: 1, padding: '8px 4px', borderRadius: 6, border: '1px solid var(--color-border)', fontSize: '0.85rem' }}
                    >
                      <option value="g">g</option>
                      <option value="ml">ml</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: '0.8rem', fontWeight: 700, display: 'block', marginBottom: 4 }}>
                    Basis
                  </label>
                  <select
                    value={editForm.measurement_basis}
                    onChange={e => setEditForm({ ...editForm, measurement_basis: e.target.value })}
                    style={{ width: '100%', padding: '8px 10px', borderRadius: 6, border: '1px solid var(--color-border)', fontSize: '0.88rem' }}
                  >
                    <option value="per 100g">per 100g</option>
                    <option value="per 100ml">per 100ml</option>
                    <option value="per serving">per serving</option>
                  </select>
                </div>
              </div>

              {/* Nutrition Grid */}
              <div style={{ background: '#f8faf7', border: '1px solid var(--color-border)', borderRadius: 8, padding: 14, marginBottom: 16 }}>
                <span style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--color-primary)', textTransform: 'uppercase', display: 'block', marginBottom: 10 }}>
                  Nutritional Values ({editForm.measurement_basis})
                </span>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 10 }}>
                  {[
                    { key: 'energy_kcal', label: 'Energy', unit: 'kcal' },
                    { key: 'carbohydrates_g', label: 'Carbs', unit: 'g' },
                    { key: 'sugars_g', label: 'Total Sugars', unit: 'g' },
                    { key: 'added_sugars_g', label: 'Added Sugars', unit: 'g' },
                    { key: 'protein_g', label: 'Protein', unit: 'g' },
                    { key: 'total_fat_g', label: 'Total Fat', unit: 'g' },
                    { key: 'saturated_fat_g', label: 'Saturated Fat', unit: 'g' },
                    { key: 'sodium_mg', label: 'Sodium', unit: 'mg' },
                    { key: 'dietary_fibre_g', label: 'Dietary Fibre', unit: 'g' }
                  ].map(f => (
                    <div key={f.key}>
                      <label style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)', display: 'block', marginBottom: 2 }}>
                        {f.label} ({f.unit})
                      </label>
                      <input
                        type="number"
                        step="any"
                        placeholder="Missing"
                        value={editForm[f.key]}
                        onChange={e => setEditForm({ ...editForm, [f.key]: e.target.value })}
                        style={{ width: '100%', padding: '6px 8px', borderRadius: 4, border: '1px solid var(--color-border)', fontSize: '0.85rem' }}
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Ingredients & Allergens */}
              <div style={{ marginBottom: 14 }}>
                <label style={{ fontSize: '0.8rem', fontWeight: 700, display: 'block', marginBottom: 4 }}>
                  Ingredients List
                </label>
                <textarea
                  rows={2}
                  value={editForm.ingredients}
                  onChange={e => setEditForm({ ...editForm, ingredients: e.target.value })}
                  placeholder="e.g. Potatoes, Edible Vegetable Oil, Iodized Salt, Spices..."
                  style={{ width: '100%', padding: '8px 10px', borderRadius: 6, border: '1px solid var(--color-border)', fontSize: '0.85rem' }}
                />
              </div>

              <div style={{ marginBottom: 20 }}>
                <label style={{ fontSize: '0.8rem', fontWeight: 700, display: 'block', marginBottom: 4 }}>
                  Declared Allergens
                </label>
                <input
                  type="text"
                  value={editForm.allergens_declared}
                  onChange={e => setEditForm({ ...editForm, allergens_declared: e.target.value })}
                  placeholder="e.g. Milk, Gluten (Wheat), Soy"
                  style={{ width: '100%', padding: '8px 10px', borderRadius: 6, border: '1px solid var(--color-border)', fontSize: '0.85rem' }}
                />
              </div>

              {/* Modal Actions */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--color-border)', paddingTop: 14 }}>
                {onEditCustomData ? (
                  <button
                    type="button"
                    onClick={() => {
                      setShowEditModal(false);
                      onEditCustomData();
                    }}
                    style={{ background: 'none', border: 'none', color: 'var(--color-accent)', cursor: 'pointer', fontSize: '0.82rem', textDecoration: 'underline' }}
                  >
                    Open in full scanner view →
                  </button>
                ) : <span />}

                <div style={{ display: 'flex', gap: 10 }}>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => setShowEditModal(false)}
                    style={{ padding: '8px 16px', fontSize: '0.85rem' }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn-primary"
                    disabled={savingEdit}
                    style={{ padding: '8px 20px', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: 6 }}
                  >
                    {savingEdit ? (
                      <>
                        <RefreshCw size={14} className="spin" style={{ animation: 'spin 1s linear infinite' }} />
                        <span>Recalculating...</span>
                      </>
                    ) : (
                      <span>Save & Recalculate Assessment</span>
                    )}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
