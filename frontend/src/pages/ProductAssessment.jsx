import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, ShieldCheck, AlertTriangle, CheckCircle2, Bookmark, 
  ArrowRight, Heart, Sparkles, Scale, AlertCircle, Info, ChevronRight, Award,
  Edit3, X, Sliders, RefreshCw
} from 'lucide-react';
import { useLockBodyScroll } from '../components/useLockBodyScroll';

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

  const recordLocalInteraction = (data) => {
    if (!data || !data.product_id) return;
    try {
      const stored = localStorage.getItem('eatgood_interaction_history');
      let hist = stored ? JSON.parse(stored) : [];
      hist = hist.filter(h => h.product_id !== data.product_id);
      hist.unshift({
        id: Date.now(),
        product_id: data.product_id,
        product_name: data.product_name || 'Food Product',
        brand: data.brand || 'General',
        category: data.category || 'Food Item',
        personalized_score: data.layer2_personalized?.personalized_score ?? null,
        general_grade: data.layer1_general?.grade || 'N/A',
        analysis_source: data.is_custom ? 'Custom Label Scan' : (data.data_source || 'Catalogue Assessment'),
        timestamp: new Date().toISOString()
      });
      localStorage.setItem('eatgood_interaction_history', JSON.stringify(hist.slice(0, 30)));
    } catch (e) {}
  };

  useEffect(() => {
    if (productId && !initialAssessment) {
      setLoading(true);
      fetch(`/api/products/${productId}`)
        .then(res => res.json())
        .then(data => {
          setAssessment(data);
          recordLocalInteraction(data);
          if (data.is_saved !== undefined) {
            setIsSaved(data.is_saved);
          }
          setLoading(false);
        })
        .catch(err => {
          console.error(err);
          setLoading(false);
        });

      // Fetch healthier alternatives
      fetch(`/api/alternatives/${productId}`)
        .then(res => res.json())
        .then(data => setAlternatives(data.alternatives || []))
        .catch(err => console.error(err));
    } else if (initialAssessment) {
      setAssessment(initialAssessment);
      recordLocalInteraction(initialAssessment);
      if (initialAssessment.is_saved !== undefined) {
        setIsSaved(initialAssessment.is_saved);
      }
      setLoading(false);
    }
  }, [productId, initialAssessment, activeProfile]);

  useEffect(() => {
    const pid = productId || initialAssessment?.product_id;
    if (pid) {
      fetch(`/api/saved/check/${pid}`)
        .then(res => res.json())
        .then(data => setIsSaved(Boolean(data.is_saved)))
        .catch(err => console.error(err));
    }
  }, [productId, initialAssessment]);

  const handleToggleSave = () => {
    if (!assessment?.product_id) return;
    fetch(`/api/saved/${assessment.product_id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        product_id: assessment.product_id,
        product_name: assessment.product_name,
        brand: assessment.brand,
        category: assessment.category,
        sub_category: assessment.sub_category,
        energy_kcal: assessment.nutrition_facts?.energy_kcal ?? assessment.energy_kcal,
        sugars_g: assessment.nutrition_facts?.sugars_g ?? assessment.sugars_g,
        sodium_mg: assessment.nutrition_facts?.sodium_mg ?? assessment.sodium_mg,
        protein_g: assessment.nutrition_facts?.protein_g ?? assessment.protein_g,
        dietary_fibre_g: assessment.nutrition_facts?.dietary_fibre_g ?? assessment.dietary_fibre_g,
        saturated_fat_g: assessment.nutrition_facts?.saturated_fat_g ?? assessment.saturated_fat_g,
        ingredients: assessment.ingredients,
        allergens_declared: assessment.allergens_declared,
        measurement_basis: assessment.measurement_basis,
        serving_size: assessment.serving_size,
        serving_size_unit: assessment.serving_size_unit,
        data_confidence_status: assessment.data_confidence_status
      })
    })
      .then(res => res.json())
      .then(data => setIsSaved(data.is_saved))
      .catch(err => console.error(err));
  };

  if (loading) {
    return (
      <div style={{ padding: '80px 0', textAlign: 'center', color: 'var(--color-text-muted)' }}>
        Generating 3-Layer Food Safety & Nutrition Assessment...
      </div>
    );
  }

  if (!assessment) {
    return (
      <div style={{ padding: '60px 0', textAlign: 'center' }}>
        <h3>Assessment not available</h3>
        <button className="btn-secondary" onClick={onBack} style={{ marginTop: 16 }}>Back</button>
      </div>
    );
  }

  const l1 = assessment.layer1_general || {};
  const l2 = assessment.layer2_personalized || {};
  const l3_allg = assessment.layer3_allergens || {};
  const l3_add = assessment.layer3_additives || {};
  const claims = assessment.marketing_claims_analysis || [];
  const ml_exp = assessment.ml_experimental_insight || {};
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
      alert('Please enter a product name.');
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
      const res = await fetch('/api/products/assess', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const newAssessment = await res.json();
      setAssessment(newAssessment);
      if (onUpdateAssessment) {
        onUpdateAssessment(newAssessment, editForm);
      }
      setSavingEdit(false);
      setShowEditModal(false);
    } catch (err) {
      console.error(err);
      setSavingEdit(false);
      alert('Failed to recalculate assessment.');
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
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
          <div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
              <span style={{ fontSize: '0.82rem', fontWeight: 800, color: 'var(--color-accent)', textTransform: 'uppercase' }}>
                {assessment.brand || 'Brand'}
              </span>
              <span>•</span>
              <span style={{ fontSize: '0.82rem', color: 'var(--color-text-subtle)' }}>
                {assessment.category} ({assessment.sub_category})
              </span>
              <span className="badge badge-verified" style={{ fontSize: '0.7rem' }}>
                {assessment.data_confidence_status}
              </span>
            </div>
            
            <h1 style={{ fontSize: '2.1rem', color: 'var(--color-primary)', lineHeight: 1.2, marginBottom: 8 }}>
              {assessment.product_name}
            </h1>

            <div style={{ fontSize: '0.8rem', color: 'var(--color-text-subtle)' }}>
              Measurement Basis: <strong>{assessment.measurement_basis || 'per 100g'}</strong> • Serving Size: {assessment.serving_size || 100}{assessment.serving_size_unit || 'g'}
            </div>

            {assessment.openfoodfacts_attribution && (
              <div style={{ marginTop: 8, fontSize: '0.75rem', color: 'var(--color-text-muted)', background: '#f8f9fa', border: '1px solid #e9ecef', padding: '4px 10px', borderRadius: 6, display: 'inline-block' }}>
                {assessment.openfoodfacts_attribution}
              </div>
            )}
          </div>

          {/* Quick Dual Score Pill */}
          <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
            {/* General Grade */}
            <div style={{ textAlign: 'center', padding: '10px 16px', background: 'var(--color-surface-alt)', borderRadius: 12, border: '1px solid var(--color-border)' }}>
              <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--color-text-subtle)', display: 'block', textTransform: 'uppercase' }}>
                General Grade
              </span>
              <span className={`grade-badge grade-${l1.grade || 'NA'}`} style={{ width: 38, height: 38, fontSize: '1.4rem', marginTop: 4 }}>
                {l1.grade || 'N/A'}
              </span>
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

      {/* Hard Safety Alert Banner (Layer 3 Critical Allergen Conflict) */}
      {l2.has_critical_allergen_conflict && (
        <div style={{
          background: '#ffebee',
          border: '2px solid #c62828',
          borderRadius: 12,
          padding: '18px 24px',
          marginBottom: 24,
          display: 'flex',
          gap: 16,
          alignItems: 'center'
        }}>
          <AlertTriangle size={32} color="#c62828" style={{ flexShrink: 0 }} />
          <div>
            <h3 style={{ color: '#c62828', fontSize: '1.15rem', marginBottom: 4 }}>
              CRITICAL SAFETY WARNING — Allergen Conflict Detected
            </h3>
            <p style={{ color: '#b71c1c', fontSize: '0.88rem', margin: 0 }}>
              This product contains or declared: <strong>{l2.allergen_conflicts.map(c => c.allergen).join(', ')}</strong>, 
              which violates the strict safety exclusions set in your active profile. Suitability score is overridden to 0.
            </p>
          </div>
        </div>
      )}

      {/* Grid: Layer 1 (General) & Layer 2 (Personalized) */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 20, marginBottom: 24 }}>
        
        {/* Layer 1: General Nutritional Assessment */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--color-primary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                LAYER 1 — GENERAL NUTRITIONAL ASSESSMENT
              </span>
              <span className={`grade-badge grade-${l1.grade || 'NA'}`} style={{ width: 28, height: 28, fontSize: '1.1rem' }}>
                {l1.grade || 'N/A'}
              </span>
            </div>

            <h3 style={{ fontSize: '1.25rem', color: 'var(--color-primary)', marginBottom: 8 }}>
              {l1.grade_label || 'Assessment Status'}
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginBottom: 16 }}>
              {l1.explanation}
            </p>

            {/* Strengths */}
            {l1.strengths && l1.strengths.length > 0 && (
              <div style={{ marginBottom: 14 }}>
                <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#2e7d32', display: 'block', marginBottom: 6 }}>
                  ✓ NUTRITIONAL STRENGTHS
                </span>
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: '0.82rem', color: '#1b5e20' }}>
                  {l1.strengths.map((str, i) => <li key={i} style={{ marginBottom: 4 }}>{str}</li>)}
                </ul>
              </div>
            )}

            {/* Concerns */}
            {l1.concerns && l1.concerns.length > 0 && (
              <div style={{ marginBottom: 14 }}>
                <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#e65100', display: 'block', marginBottom: 6 }}>
                  ⚠️ NUTRIENTS OF CONCERN
                </span>
                <ul style={{ margin: 0, paddingLeft: 18, fontSize: '0.82rem', color: '#b73800' }}>
                  {l1.concerns.map((con, i) => <li key={i} style={{ marginBottom: 4 }}>{con}</li>)}
                </ul>
              </div>
            )}

            {/* Missing Fields */}
            {l1.missing_fields && l1.missing_fields.length > 0 && (
              <div style={{ background: '#f5f5f5', padding: '8px 12px', borderRadius: 6, fontSize: '0.75rem', color: '#666' }}>
                ℹ️ <strong>Missing Declarations:</strong> {l1.missing_fields.join(', ')}
              </div>
            )}
          </div>

          <div style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid var(--color-border)', fontSize: '0.72rem', color: 'var(--color-text-subtle)' }}>
            Standards applied: {l1.standards_applied?.join(', ') || 'Category guidelines'}
          </div>
        </div>

        {/* Layer 2: Personalized Suitability */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--color-accent)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                LAYER 2 — PERSONALIZED SUITABILITY
              </span>
              <span className="badge badge-verified">
                Goal: {l2.user_goal}
              </span>
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

                {/* Visual 1–100 Calibrated Scale Bar */}
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
                        {st.rule}
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
              Final Calibrated Score: <span style={{ color: l2.color === 'red' ? '#c62828' : (l2.color === 'green' ? '#2e7d32' : '#e65100') }}>{l2.personalized_score} / 100</span> ({l2.suitability_badge})
            </div>
          </div>
        </div>
      )}

      {/* Nutrition Facts Breakdown Table */}
      <div className="card" style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: '1.2rem', color: 'var(--color-primary)', marginBottom: 14 }}>
          Nutritional Panel ({assessment.measurement_basis || 'per 100g'})
        </h3>
        
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: 12,
          textAlign: 'center'
        }}>
          {[
            { label: 'Energy', val: nuts.energy_kcal, unit: 'kcal' },
            { label: 'Total Sugars', val: nuts.sugars_g, unit: 'g', concern: nuts.sugars_g > 10 },
            { label: 'Added Sugars', val: nuts.added_sugars_g, unit: 'g' },
            { label: 'Sodium', val: nuts.sodium_mg, unit: 'mg', concern: nuts.sodium_mg > 400 },
            { label: 'Protein', val: nuts.protein_g, unit: 'g', good: nuts.protein_g >= 10 },
            { label: 'Total Fat', val: nuts.total_fat_g, unit: 'g' },
            { label: 'Saturated Fat', val: nuts.saturated_fat_g, unit: 'g', concern: nuts.saturated_fat_g > 4 },
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
                {item.val != null ? `${item.val} ${item.unit}` : 'Missing'}
              </strong>
            </div>
          ))}
        </div>
      </div>

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

      {/* Misleading Marketing Claims Auditor */}
      {claims.length > 0 && (
        <div className="card" style={{ marginBottom: 24 }}>
          <h3 style={{ fontSize: '1.2rem', color: 'var(--color-primary)', marginBottom: 12 }}>
            Front-of-Pack Marketing Claim Auditor
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {claims.map((cl, i) => {
              const isConsistent = cl.status === 'Consistent with available data';
              const isInconsistent = cl.status === 'Potential inconsistency';
              return (
                <div key={i} style={{
                  border: isInconsistent ? '1px solid #ffcc80' : (isConsistent ? '1px solid #c8e6c9' : '1px solid var(--color-border)'),
                  background: isInconsistent ? '#fff8e1' : (isConsistent ? '#f1f8e9' : '#fff'),
                  padding: 12,
                  borderRadius: 8
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <strong style={{ fontSize: '0.9rem' }}>"{cl.claim}"</strong>
                    <span style={{
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      color: isConsistent ? '#2e7d32' : (isInconsistent ? '#e65100' : '#666')
                    }}>
                      {cl.status}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)' }}>
                    <strong>Evidence:</strong> {cl.evidence}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--color-text-main)', marginTop: 2 }}>
                    {cl.explanation}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Healthier Alternatives */}
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
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--color-text-subtle)' }}>
                      {alt.brand}
                    </span>
                    <span className={`grade-badge grade-${alt.general_grade || 'NA'}`} style={{ width: 22, height: 22, fontSize: '0.75rem' }}>
                      {alt.general_grade || 'NA'}
                    </span>
                  </div>

                  <h4 style={{ fontSize: '0.95rem', color: 'var(--color-primary)', marginBottom: 6 }}>
                    {alt.product_name}
                  </h4>

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
                    <option value="Snacks">Snacks (Calibrated)</option>
                    <option value="Breakfast Cereals">Breakfast Cereals (Calibrated)</option>
                    <option value="Packaged Beverages">Packaged Beverages (Calibrated)</option>
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
