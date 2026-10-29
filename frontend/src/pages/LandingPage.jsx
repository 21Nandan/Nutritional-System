import React from 'react';
import { 
  ScanLine, Search, ShieldCheck, ArrowRight, AlertTriangle, HeartPulse, Scale 
} from 'lucide-react';

export default function LandingPage({ setActivePage, onSelectProduct, activeProfile, onOpenProfile }) {
  // Sample demonstration products for quick interactive preview
  const SAMPLE_SNACK_ID = "IND_PKG_001"; // Haldiram's Bhujia Sev

  return (
    <div className="landing-page">
      {/* 1. Hero Section */}
      <section style={{
        padding: '50px 0 60px',
        textAlign: 'center',
        maxWidth: 880,
        margin: '0 auto'
      }}>
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
          <strong> EATGOOD</strong> turns nutrition panels into a simple grade, a personal fit score and allergen warnings, with every number explained.
        </p>

        <div style={{ display: 'flex', justifyContent: 'center', gap: 14, flexWrap: 'wrap' }}>
          <button 
            className="btn-primary" 
            style={{ padding: '14px 28px', fontSize: '1rem' }}
            onClick={() => setActivePage('scanner')}
          >
            <ScanLine size={18} />
            <span>Find a Product</span>
          </button>
          
          <button 
            className="btn-secondary" 
            style={{ padding: '14px 28px', fontSize: '1rem' }}
            onClick={() => setActivePage('catalogue')}
          >
            <Search size={18} />
            <span>Explore Indian Products</span>
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
      <section className="transformation-section">
        <div style={{ textAlign: 'center', maxWidth: 640, margin: '0 auto 32px' }}>
          <span style={{ textTransform: 'uppercase', fontSize: '0.75rem', fontWeight: 800, color: 'var(--color-accent)', letterSpacing: '0.08em' }}>
            The EATGOOD Transformation Engine
          </span>
          <h2 style={{ fontSize: '1.8rem', color: 'var(--color-primary)', marginTop: 6 }}>
            From a confusing label to a clear answer
          </h2>
          <p style={{ fontSize: '0.9rem', color: 'var(--color-text-muted)', marginTop: 6 }}>
            Label values are checked for consistency, compared with category thresholds, and matched to your profile.
          </p>
        </div>

        <div className="transformation-grid">
          {/* Left: Raw Label Simulation */}
          <div className="transformation-card raw-label-card" style={{
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

          {/* Center: Processing Arrow (auto-rotates downwards on mobile screens) */}
          <div className="transformation-arrow-wrapper">
            <div className="transformation-arrow-icon">
              <ArrowRight size={20} />
            </div>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--color-text-subtle)', textTransform: 'uppercase' }}>
              3-Layer Engine
            </span>
          </div>

          {/* Right: EATGOOD Assessment */}
          <div className="transformation-card assessment-preview-card" style={{
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
          <h2 style={{ fontSize: '2rem', color: 'var(--color-primary)' }}>Built to be clear and checkable</h2>
          <p style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem', marginTop: 6 }}>
            Every grade shows the thresholds it used and the documents they are informed by.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 20 }}>
          <div className="card">
            <div style={{ width: 40, height: 40, borderRadius: 10, background: 'var(--color-accent-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16 }}>
              <Scale size={20} color="var(--color-primary)" />
            </div>
            <h3 style={{ fontSize: '1.1rem', marginBottom: 8 }}>1. General Nutrition Assessment</h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', lineHeight: 1.5 }}>
              Objective category benchmarks (Snacks, Cereals, Beverages) established using documented WHO SEARO and FSSAI Indian Nutrition Rating (INR) reference criteria.
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

      {/* 4. How the System Works — Simple 4-Step Process */}
      <section style={{
        background: 'var(--color-primary-dark)',
        color: '#fff',
        borderRadius: 'var(--radius-lg)',
        padding: '40px 32px',
        marginBottom: 60
      }}>
        <div style={{ textAlign: 'center', maxWidth: 640, margin: '0 auto 36px' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--color-accent-light)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            How It Works
          </span>
          <h2 style={{ fontSize: '1.9rem', color: '#fff', marginTop: 6 }}>How EATGOOD Evaluates Foods</h2>
          <p style={{ fontSize: '0.9rem', color: '#b0c9bb', marginTop: 6 }}>
            A transparent, 4-step process from food label to personalized assessment.
          </p>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 16
        }}>
          {[
            { step: '01', title: 'Scan or Search', desc: 'Search a world database of packaged foods, scan a barcode, or enter values manually.' },
            { step: '02', title: 'Confirm Nutrition', desc: 'Verify extracted serving size, ingredients, and nutrients with an editable confirmation step.' },
            { step: '03', title: 'Standards Benchmark', desc: 'Assess nutrient levels against established WHO and FSSAI guidelines for high sugar, sodium, and fat.' },
            { step: '04', title: 'Personalized Result', desc: 'Get a tailored suitability score, clear allergen alerts, and healthier same-category alternatives.' }
          ].map(s => (
            <div key={s.step} style={{ background: 'rgba(255,255,255,0.06)', borderRadius: 10, padding: 20, border: '1px solid rgba(255,255,255,0.1)' }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 800, color: 'var(--color-accent-light)', marginBottom: 6 }}>
                STEP {s.step}
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
              Limits you should know about
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', lineHeight: 1.6, marginBottom: 12 }}>
              • <strong>Data sources:</strong> barcode lookups and product search use Open Food Facts, a community database. Always check values against the pack.
              <br />
              • <strong>Thresholds:</strong> grades use category thresholds informed by WHO and FSSAI reference documents; these bodies have not reviewed or endorsed EATGOOD. Chocolates, sweets and condiments get no grade.
              <br />
              • <strong>Missing values:</strong> a nutrient missing from the label is shown as &ldquo;Not stated&rdquo; and never counted as zero.
              <br />
              • <strong>Not medical advice:</strong> EATGOOD is informational only.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}

