import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, ShieldCheck, AlertTriangle, CheckCircle2, Bookmark, 
  ArrowRight, Heart, Sparkles, Scale, AlertCircle, Info, ChevronRight, Award
} from 'lucide-react';

export default function ProductAssessment({ 
  productId, 
  assessmentData: initialAssessment, 
  onBack, 
  onSelectProduct, 
  activeProfile 
}) {
  const [assessment, setAssessment] = useState(initialAssessment || null);
  const [loading, setLoading] = useState(!initialAssessment);
  const [alternatives, setAlternatives] = useState([]);
  const [isSaved, setIsSaved] = useState(false);

  useEffect(() => {
    if (productId && !initialAssessment) {
      setLoading(true);
      fetch(`/api/products/${productId}`)
        .then(res => res.json())
        .then(data => {
          setAssessment(data);
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
      setLoading(false);
    }
  }, [productId, initialAssessment, activeProfile]);

  const handleToggleSave = () => {
    if (!assessment?.product_id) return;
    fetch(`/api/saved/${assessment.product_id}`, { method: 'POST' })
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

  return (
    <div className="product-assessment-page" style={{ maxWidth: 1040, margin: '0 auto' }}>
      {/* Back button and Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <button className="btn-secondary" onClick={onBack} style={{ padding: '8px 14px', fontSize: '0.85rem' }}>
          <ArrowLeft size={16} />
          <span>Back to Catalogue</span>
        </button>

        <div style={{ display: 'flex', gap: 10 }}>
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
            <div style={{ textAlign: 'center', padding: '10px 16px', background: 'var(--color-surface-alt)', borderRadius: 12, border: '1px solid var(--color-border)' }}>
              <span style={{ fontSize: '0.7rem', fontWeight: 700, color: 'var(--color-text-subtle)', display: 'block', textTransform: 'uppercase' }}>
                Goal Match
              </span>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: l2.color === 'red' ? '#c62828' : (l2.color === 'green' ? '#2e7d32' : '#e65100'), marginTop: 2 }}>
                {l2.personalized_score}/100
              </div>
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
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
        
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
            <div style={{ background: 'var(--color-surface-alt)', borderRadius: 8, padding: 10, marginTop: 12 }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--color-text-subtle)', textTransform: 'uppercase' }}>
                Transparent Rule Points
              </span>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 }}>
                {l2.rules_applied && l2.rules_applied.map((r, i) => (
                  <span key={i} style={{ fontSize: '0.72rem', background: '#fff', border: '1px solid var(--color-border)', padding: '2px 6px', borderRadius: 4 }}>
                    {r}
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid var(--color-border)', fontSize: '0.72rem', color: 'var(--color-text-subtle)' }}>
            Dietary preference checked: {l2.dietary_preference}
          </div>
        </div>
      </div>

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
                    Suitability Score: {alt.personalized_score}/100
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

      {/* Experimental ML Model Perspective & Disclaimer */}
      {ml_exp.available && (
        <div style={{
          background: 'var(--color-surface-alt)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-lg)',
          padding: 20,
          marginBottom: 24
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <Cpu size={18} color="var(--color-primary)" />
            <span style={{ fontSize: '0.85rem', fontWeight: 800, color: 'var(--color-primary)', textTransform: 'uppercase' }}>
              Experimental Machine Learning Classification
            </span>
            <span className="badge badge-neutral" style={{ fontSize: '0.68rem' }}>
              Simulated Training Labels
            </span>
          </div>

          <p style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', lineHeight: 1.5, marginBottom: 8 }}>
            Prediction: <strong>{ml_exp.is_suitable_prediction ? 'Suitable' : 'Not Suitable'}</strong> (Estimated Probability: {ml_exp.predicted_probability})
          </p>
          <div style={{ fontSize: '0.75rem', color: '#666', background: '#fff', padding: '8px 12px', borderRadius: 6, border: '1px solid var(--color-border)' }}>
            ⚠️ <strong>Model Transparency Note:</strong> {ml_exp.scientific_limitation}
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
    </div>
  );
}
