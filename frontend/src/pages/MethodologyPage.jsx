import React, { useState, useEffect } from 'react';
import { BookOpen, FileText, ArrowRight, CheckCircle2, Cpu, Scale, ShieldAlert, Sparkles } from 'lucide-react';

export default function MethodologyPage() {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch('/api/methodology')
      .then(res => res.json())
      .then(d => setData(d))
      .catch(err => console.error(err));
  }, []);

  return (
    <div className="methodology-page" style={{ maxWidth: 980, margin: '0 auto' }}>
      <div style={{ marginBottom: 32 }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          background: 'var(--color-accent-subtle)',
          color: 'var(--color-primary)',
          padding: '4px 12px',
          borderRadius: 20,
          fontSize: '0.8rem',
          fontWeight: 700,
          marginBottom: 10
        }}>
          <BookOpen size={14} color="var(--color-accent)" />
          <span>Academic Experiential Learning (Phase-I) Research Dossier</span>
        </div>
        <h1 style={{ fontSize: '2.4rem', color: 'var(--color-primary)', marginBottom: 8, lineHeight: 1.2 }}>
          Research Foundation & Methodology
        </h1>
        <p style={{ color: 'var(--color-text-muted)', fontSize: '1rem', lineHeight: 1.6 }}>
          Technical background, literature review citations, research flowchart, and mathematical formulations supporting the EATGOOD AI platform.
        </p>
      </div>

      {/* 1. Introduction & Problem Definition */}
      <section className="card" style={{ marginBottom: 28, padding: 28 }}>
        <h2 style={{ fontSize: '1.4rem', color: 'var(--color-primary)', marginBottom: 12 }}>
          1. Problem Definition & Objectives
        </h2>
        <div style={{ background: 'var(--color-surface-alt)', borderLeft: '4px solid var(--color-accent)', padding: '14px 18px', borderRadius: '0 8px 8px 0', marginBottom: 16 }}>
          <p style={{ fontStyle: 'italic', color: 'var(--color-text-main)', fontSize: '0.92rem', lineHeight: 1.6, margin: 0 }}>
            "{data?.problem_definition || 'Consumers struggle to determine whether packaged food products are nutritionally appropriate and suitable for their individual requirements because of obscure additives, varying serving sizes, and ambiguous health claims.'}"
          </p>
        </div>

        <h4 style={{ fontSize: '1rem', color: 'var(--color-primary)', marginBottom: 8 }}>
          Core Research Objectives:
        </h4>
        <ul style={{ margin: 0, paddingLeft: 22, fontSize: '0.88rem', color: 'var(--color-text-muted)', lineHeight: 1.6 }}>
          <li><strong>Quantitative Ingredient & Nutrient Auditing:</strong> Standardize varying serving sizes and inspect Atwater calorie discrepancies (78 identified in dataset).</li>
          <li><strong>Authoritative Standards Harmonization:</strong> Benchmark products using WHO South-East Asia Regional Nutrient Profile guidelines and FSSAI Draft Indian Nutrition Rating (INR).</li>
          <li><strong>Explainable Personalization:</strong> Implement transparent 0–100 suitability scores aligned with distinct nutritional goals (Reduce Sugar, Reduce Sodium, Increase Fibre, Increase Protein, Balanced Choices).</li>
          <li><strong>Hard Safety Exclusions:</strong> Isolate critical allergen conflicts from numerical scores, guaranteeing that high nutritional points never override an allergen alert.</li>
          <li><strong>Front-of-Pack Claim Auditing:</strong> Cross-examine marketing declarations ("High Protein", "Zero Sugar") against verified quantitative chemical and nutrition data.</li>
        </ul>
      </section>

      {/* 2. Literature Review (The 4 Supplied Presentation Citations) */}
      <section className="card" style={{ marginBottom: 28, padding: 28 }}>
        <h2 style={{ fontSize: '1.4rem', color: 'var(--color-primary)', marginBottom: 8 }}>
          2. Literature Review & Grounding Citations
        </h2>
        <p style={{ fontSize: '0.88rem', color: 'var(--color-text-muted)', marginBottom: 20 }}>
          The system's design directly responds to findings from four primary academic and regulatory publications:
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {data?.research_references?.map(ref => (
            <div key={ref.citation_num} style={{
              background: '#fff',
              border: '1px solid var(--color-border)',
              borderRadius: 10,
              padding: 18,
              boxShadow: 'var(--shadow-sm)'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                <span style={{ fontSize: '0.72rem', fontWeight: 800, color: 'var(--color-accent)', textTransform: 'uppercase' }}>
                  Reference [{ref.citation_num}] • {ref.year}
                </span>
                <span className="badge badge-neutral" style={{ fontSize: '0.7rem' }}>
                  Peer-Reviewed / Regulatory
                </span>
              </div>
              <h4 style={{ fontSize: '1.05rem', color: 'var(--color-primary)', marginBottom: 6, lineHeight: 1.3 }}>
                "{ref.title}"
              </h4>
              <div style={{ fontSize: '0.8rem', color: 'var(--color-text-subtle)', marginBottom: 8 }}>
                Authors: <strong>{ref.authors}</strong>
              </div>
              <div style={{ fontSize: '0.84rem', color: 'var(--color-text-muted)', background: 'var(--color-surface-alt)', padding: '10px 14px', borderRadius: 6, lineHeight: 1.5 }}>
                <strong>Key Finding Applied to EATGOOD:</strong> {ref.finding}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 3. Research Methodology Flowchart */}
      <section className="card" style={{ marginBottom: 28, padding: 28 }}>
        <h2 style={{ fontSize: '1.4rem', color: 'var(--color-primary)', marginBottom: 8 }}>
          3. Research Pipeline Flowchart
        </h2>
        <p style={{ fontSize: '0.88rem', color: 'var(--color-text-muted)', marginBottom: 24 }}>
          Sequential execution flow from raw retail data intake through multi-layered assessment to user evaluation:
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {data?.research_flowchart?.map((step, idx) => (
            <div key={step.step} style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
              <div style={{
                width: 36,
                height: 36,
                borderRadius: '50%',
                background: 'var(--color-primary)',
                color: '#fff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 800,
                fontSize: '0.85rem',
                flexShrink: 0
              }}>
                {step.step}
              </div>
              <div style={{
                flex: 1,
                background: 'var(--color-surface-alt)',
                border: '1px solid var(--color-border)',
                borderRadius: 8,
                padding: '12px 18px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: 8
              }}>
                <div>
                  <strong style={{ fontSize: '0.95rem', color: 'var(--color-primary)' }}>{step.name}</strong>
                  <p style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', margin: '2px 0 0' }}>{step.desc}</p>
                </div>
                <span className="badge badge-verified" style={{ fontSize: '0.7rem' }}>
                  Phase Implemented
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 4. Mathematical Atwater Calorie Formulation */}
      <section className="card" style={{ marginBottom: 28, padding: 28 }}>
        <h2 style={{ fontSize: '1.4rem', color: 'var(--color-primary)', marginBottom: 8 }}>
          4. Nutritional Physics & Atwater Consistency Formulation
        </h2>
        <p style={{ fontSize: '0.88rem', color: 'var(--color-text-muted)', marginBottom: 16, lineHeight: 1.5 }}>
          In our retail audit of 852 Indian products, 78 records displayed large discrepancies between declared energy (kcal) and the thermodynamic sum of their macronutrients:
        </p>

        <div style={{ background: '#f8faf7', border: '1px solid var(--color-border)', padding: 16, borderRadius: 8, fontFamily: 'monospace', fontSize: '0.92rem', marginBottom: 14 }}>
          <strong>Energy_Atwater (kcal) = (4.0 × Carbohydrates_g) + (4.0 × Protein_g) + (9.0 × Total_Fat_g)</strong>
        </div>

        <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', lineHeight: 1.5 }}>
          When <code>|Energy_Reported - Energy_Atwater| &gt; 50 kcal</code> or exceeds 25% relative difference, EATGOOD flags the record with <em>"Source Verification Required"</em> and warns users that the manufacturer's packaging may have omitted fat calories or transcribed metric kilojoules (kJ) as calories.
        </p>
      </section>

      {/* 5. Future Research Roadmap */}
      <section className="card" style={{ padding: 28 }}>
        <h2 style={{ fontSize: '1.4rem', color: 'var(--color-primary)', marginBottom: 8 }}>
          5. Future Research Roadmap
        </h2>
        <p style={{ fontSize: '0.88rem', color: 'var(--color-text-muted)', marginBottom: 16 }}>
          Planned scientific and technical enhancements for subsequent experiential learning phases:
        </p>
        <ul style={{ margin: 0, paddingLeft: 22, fontSize: '0.88rem', color: 'var(--color-text-muted)', lineHeight: 1.6 }}>
          {data?.future_work?.map((fw, i) => (
            <li key={i} style={{ marginBottom: 6 }}>{fw}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
