import React from 'react';
import { 
  ScanLine, Search, ShieldCheck, Sparkles, ArrowRight, CheckCircle2, 
  AlertTriangle, Check, Layers, Cpu, HeartPulse, Scale, FileText, ExternalLink 
} from 'lucide-react';

export default function LandingPage({ setActivePage, onSelectProduct, activeProfile, onOpenProfile }) {
  // Sample demonstration products for quick interactive preview
  const SAMPLE_SNACK_ID = "IND_PKG_001"; // Haldiram's Bhujia Sev
  const SAMPLE_CEREAL_ID = "IND_PKG_221"; // Kellogg's Corn Flakes

  return (
    <div className="landing-page">
      {/* 1. Hero Section */}
      <section style={{
        padding: '50px 0 60px',
        textAlign: 'center',
        maxWidth: 880,
        margin: '0 auto'
      }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 8,
          background: 'var(--color-accent-subtle)',
          color: 'var(--color-primary)',
          padding: '6px 16px',
          borderRadius: 'var(--radius-full)',
          fontSize: '0.85rem',
          fontWeight: 700,
          marginBottom: 20
        }}>
          <Sparkles size={16} color="var(--color-accent)" />
          <span>Academic Experiential Learning Project — AI for Social Good</span>
        </div>

        <h1 style={{
          fontSize: '3.1rem',
          lineHeight: 1.15,
          color: 'var(--color-primary)',
          marginBottom: 20,
          fontWeight: 800
        }}>
          Understand Your Food.<br />
          <span style={{ color: 'var(--color-accent)' }}>Choose What Works for You.</span>
        </h1>

        <p style={{
          fontSize: '1.15rem',
          color: 'var(--color-text-muted)',
          lineHeight: 1.6,
          marginBottom: 36,
          maxWidth: 720,
          margin: '0 auto 36px'
        }}>
          Packaged food labels are filled with complex numbers, deceptive serving sizes, and obscure additives.
          <strong> EATGOOD</strong> translates intricate nutrition panels into simple, evidence-based assessments personalized to your unique health goals and dietary restrictions.
        </p>

        <div style={{ display: 'flex', justifyContent: 'center', gap: 14, flexWrap: 'wrap' }}>
          <button 
            className="btn-primary" 
            style={{ padding: '14px 28px', fontSize: '1rem' }}
            onClick={() => setActivePage('scanner')}
          >
            <ScanLine size={18} />
            <span>Analyze a Food Label</span>
          </button>
          
          <button 
            className="btn-secondary" 
            style={{ padding: '14px 28px', fontSize: '1rem' }}
            onClick={() => setActivePage('catalogue')}
          >
            <Search size={18} />
            <span>Explore 852 Indian Products</span>
          </button>
        </div>

        {/* Current profile indicator */}
        <div style={{
          marginTop: 24,
          fontSize: '0.82rem',
          color: 'var(--color-text-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 6
        }}>
          <span>Active Evaluation Goal:</span>
          <span style={{ fontWeight: 700, color: 'var(--color-primary)' }}>{activeProfile?.goal || 'Balanced Choices'}</span>
          <span>•</span>
          <span style={{ textDecoration: 'underline', cursor: 'pointer', color: 'var(--color-accent)' }} onClick={onOpenProfile}>
            Change Profile
          </span>
        </div>
      </section>

      {/* 2. Visual Food-Analysis Transformation Section */}
      <section style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        padding: '36px 32px',
        marginBottom: 60,
        boxShadow: var_shadow_sm
      }}>
        <div style={{ textAlign: 'center', maxWidth: 640, margin: '0 auto 32px' }}>
          <span style={{ textTransform: 'uppercase', fontSize: '0.75rem', fontWeight: 800, color: 'var(--color-accent)', letterSpacing: '0.08em' }}>
            The EATGOOD Transformation Engine
          </span>
          <h2 style={{ fontSize: '1.8rem', color: 'var(--color-primary)', marginTop: 6 }}>
            From Obscure Label to Actionable Intelligence
          </h2>
          <p style={{ fontSize: '0.9rem', color: 'var(--color-text-muted)', marginTop: 6 }}>
            Raw manufacturer packaging declarations are audited, checked against international standards, and personalized.
          </p>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr auto 1fr',
          gap: 24,
          alignItems: 'center'
        }}>
          {/* Left: Raw Label Simulation */}
          <div style={{
            background: '#fafbfc',
            border: '2px dashed #d0d7de',
            borderRadius: 12,
            padding: 20,
            fontFamily: 'monospace',
            fontSize: '0.82rem'
          }}>
            <div style={{ borderBottom: '2px solid #000', paddingBottom: 6, marginBottom: 8, fontWeight: 800, fontSize: '1rem' }}>
              NUTRITION FACTS
            </div>
            <div style={{ fontSize: '0.75rem', color: '#666', marginBottom: 8 }}>
              Serving size: 30g | Servings: 5 (Varying Basis)
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #e1e4e8', padding: '4px 0' }}>
              <span>Energy (kcal)</span>
              <strong>548.0</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #e1e4e8', padding: '4px 0' }}>
              <span>Total Sugars</span>
              <strong>14.5g</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #e1e4e8', padding: '4px 0' }}>
              <span>Added Sugars</span>
              <strong>Not declared</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #e1e4e8', padding: '4px 0' }}>
              <span>Sodium</span>
              <strong>820.0mg</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid #e1e4e8', padding: '4px 0' }}>
              <span>Saturated Fat</span>
              <strong>12.5g</strong>
            </div>
            <div style={{ marginTop: 10, fontSize: '0.72rem', color: '#888' }}>
              Ingredients: Refined palm olein, wheat starch, INS 621, INS 102, hydrolyzed soy protein...
            </div>
          </div>

          {/* Center: Processing Arrow */}
          <div style={{ textAlign: 'center' }}>
            <div style={{
              width: 44,
              height: 44,
              borderRadius: '50%',
              background: 'var(--color-primary)',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 8px',
              boxShadow: 'var(--shadow-md)'
            }}>
              <ArrowRight size={20} />
            </div>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--color-text-subtle)', textTransform: 'uppercase' }}>
              3-Layer Engine
            </span>
          </div>

          {/* Right: EATGOOD Assessment */}
          <div style={{
            background: '#ffffff',
            border: '1px solid var(--color-border)',
            borderRadius: 12,
            padding: 20,
            boxShadow: 'var(--shadow-sm)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-text-subtle)' }}>General Assessment</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 2 }}>
                  <span className="grade-badge grade-D" style={{ width: 28, height: 28, fontSize: '1rem' }}>D</span>
                  <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>Elevated Nutrients of Concern</span>
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--color-text-subtle)' }}>Your Goal Score</span>
                <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#e65100' }}>42/100</div>
              </div>
            </div>

            <div style={{ background: '#fff3e0', border: '1px solid #ffe0b2', borderRadius: 6, padding: '8px 10px', fontSize: '0.78rem', color: '#b73800', marginBottom: 8 }}>
              <strong>Caution for '{activeProfile?.goal || 'Reduce Sugar'}':</strong> Total sugars (14.5g) exceeds WHO front-of-pack recommendation (&gt;10g/100g).
            </div>

            <div style={{ background: '#ffebee', border: '1px solid #ffcdd2', borderRadius: 6, padding: '8px 10px', fontSize: '0.78rem', color: '#c62828', marginBottom: 8 }}>
              <strong>Allergen Detected:</strong> Contains Wheat (Gluten) and Hydrolyzed Soy Protein.
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10 }}>
              <span style={{ fontSize: '0.75rem', color: '#56695e' }}>2 Healthier Alternatives Available</span>
              <button 
                className="btn-accent" 
                style={{ padding: '4px 10px', fontSize: '0.78rem' }}
                onClick={() => { onSelectProduct(SAMPLE_SNACK_ID); setActivePage('assessment'); }}
              >
                Inspect Sample
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Core Feature Cards */}
      <section style={{ marginBottom: 60 }}>
        <div style={{ textAlign: 'center', marginBottom: 36 }}>
          <h2 style={{ fontSize: '2rem', color: 'var(--color-primary)' }}>Engineered for Clarity & Scientific Integrity</h2>
          <p style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem', marginTop: 6 }}>
            Unlike black-box calorie counters, every score in EATGOOD is traceable to documented guidelines.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 20 }}>
          <div className="card">
            <div style={{ width: 40, height: 40, borderRadius: 10, background: 'var(--color-accent-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16 }}>
              <Scale size={20} color="var(--color-primary)" />
            </div>
            <h3 style={{ fontSize: '1.1rem', marginBottom: 8 }}>1. General Nutrition Assessment</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', lineHeight: 1.5 }}>
              Objective category benchmarks (Snacks, Cereals, Beverages) calibrated using documented WHO SEARO and FSSAI Indian Nutrition Rating (INR) reference criteria.
            </p>
          </div>

          <div className="card">
            <div style={{ width: 40, height: 40, borderRadius: 10, background: 'var(--color-accent-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16 }}>
              <HeartPulse size={20} color="var(--color-primary)" />
            </div>
            <h3 style={{ fontSize: '1.1rem', marginBottom: 8 }}>2. Personalized Goal Suitability</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', lineHeight: 1.5 }}>
              Tailored 0–100 suitability scores aligned to Reduce Sugar, Reduce Sodium, Increase Fibre, Increase Protein, or Balanced Choices with transparent rule deductions.
            </p>
          </div>

          <div className="card">
            <div style={{ width: 40, height: 40, borderRadius: 10, background: 'var(--color-accent-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16 }}>
              <ShieldCheck size={20} color="var(--color-primary)" />
            </div>
            <h3 style={{ fontSize: '1.1rem', marginBottom: 8 }}>3. Hard Allergen Safety Exclusions</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', lineHeight: 1.5 }}>
              Distinguishes declared allergens from ingredient matches. Critical conflicts set suitability score to zero and strictly eliminate products from recommendation.
            </p>
          </div>

          <div className="card">
            <div style={{ width: 40, height: 40, borderRadius: 10, background: 'var(--color-accent-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16 }}>
              <AlertTriangle size={20} color="var(--color-primary)" />
            </div>
            <h3 style={{ fontSize: '1.1rem', marginBottom: 8 }}>4. Misleading Claim Auditor</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', lineHeight: 1.5 }}>
              Evaluates packaging marketing claims ("High Protein", "Zero Sugar", "No Added Sugar", "Low Fat") against quantitative facts to catch hidden syrups and false claims.
            </p>
          </div>
        </div>
      </section>

      {/* 4. How the System Works — Research Methodology Flow */}
      <section style={{
        background: 'var(--color-primary-dark)',
        color: '#fff',
        borderRadius: 'var(--radius-lg)',
        padding: '40px 32px',
        marginBottom: 60
      }}>
        <div style={{ textAlign: 'center', maxWidth: 640, margin: '0 auto 36px' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--color-accent-light)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            System Architecture
          </span>
          <h2 style={{ fontSize: '1.9rem', color: '#fff', marginTop: 6 }}>How EATGOOD Evaluates Foods</h2>
          <p style={{ fontSize: '0.9rem', color: '#b0c9bb', marginTop: 6 }}>
            Our 8-phase experiential learning pipeline integrates OCR, standard calibration, and explainable AI.
          </p>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 16
        }}>
          {[
            { step: '01', title: 'Data Audit', desc: '852 Indian packaged products audited for Atwater consistency and serving size anomalies.' },
            { step: '02', title: 'OCR Extraction', desc: 'AI-assisted OCR captures labels with mandatory user-editable confirmation.' },
            { step: '03', title: 'Standard Calibration', desc: 'WHO SEARO & FSSAI INR criteria applied strictly to calibrated categories.' },
            { step: '04', title: 'Personalized Scoring', desc: '0-100 score reflects user goals while hard allergen conflicts trigger red exclusions.' }
          ].map(s => (
            <div key={s.step} style={{ background: 'rgba(255,255,255,0.06)', borderRadius: 10, padding: 20, border: '1px solid rgba(255,255,255,0.1)' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 800, color: 'var(--color-accent-light)', marginBottom: 6 }}>
                PHASE {s.step}
              </div>
              <h4 style={{ color: '#fff', fontSize: '1.05rem', marginBottom: 6 }}>{s.title}</h4>
              <p style={{ fontSize: '0.8rem', color: '#b0c9bb', lineHeight: 1.5, margin: 0 }}>{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 5. Scientific Limitations & Data Transparency Callout */}
      <section style={{
        background: '#fff',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        padding: '30px',
        marginBottom: 40
      }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
          <div style={{ width: 44, height: 44, borderRadius: 10, background: '#fff3e0', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <AlertTriangle size={24} color="#e65100" />
          </div>
          <div>
            <h3 style={{ fontSize: '1.15rem', color: 'var(--color-primary)', marginBottom: 6 }}>
              Responsible AI & Data Transparency Commitments
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', lineHeight: 1.6, marginBottom: 12 }}>
              • <strong>Experimental Model Disclosure:</strong> The trained model in <code>models/eatgood_model.joblib</code> was trained on 1,500 simulated user-product examples. Its 100% test accuracy is an artifact of synthetic data generation and does not represent independent clinical efficacy.
              <br />
              • <strong>No Silent Zeros:</strong> Missing sugar, sodium, or fibre declarations are kept explicitly missing and are never silently converted into zeroes.
              <br />
              • <strong>Uncalibrated Scope:</strong> Only Snacks, Breakfast Cereals, and Packaged Beverages receive automated general grades. Other categories display raw nutrition facts with an explicit calibration disclaimer.
            </p>
            <div style={{ display: 'flex', gap: 14 }}>
              <button 
                className="btn-secondary" 
                style={{ padding: '6px 14px', fontSize: '0.82rem' }}
                onClick={() => setActivePage('audit')}
              >
                Inspect Data Quality Audit Report (78 Flagged Products)
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

const var_shadow_sm = '0 1px 3px rgba(20, 56, 40, 0.05)';
