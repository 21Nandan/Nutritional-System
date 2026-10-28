import React, { useState, useEffect } from 'react';
import { ShieldCheck, FileSpreadsheet } from 'lucide-react';

export default function DataAuditPage({ onSelectProduct }) {
  const [auditData, setAuditData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/audit')
      .then(res => res.json())
      .then(d => {
        setAuditData(d);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="data-audit-page">
      <div style={{ marginBottom: 28 }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          background: '#e8f5e9',
          color: '#2e7d32',
          padding: '4px 12px',
          borderRadius: 20,
          fontSize: '0.8rem',
          fontWeight: 700,
          marginBottom: 10
        }}>
          <ShieldCheck size={14} color="#2e7d32" />
          <span>Scientific Data Quality & Verification Audit</span>
        </div>
        <h1 style={{ fontSize: '2.2rem', color: 'var(--color-primary)', marginBottom: 8 }}>
          Dataset Quality & Governance Inspection
        </h1>
        <p style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem' }}>
          Real-time audit of the Indian packaged products catalogue, documenting data quality standards, scientific verification protocols, and strict missing-data policies.
        </p>
      </div>

      {loading ? (
        <div style={{ padding: '60px 0', textAlign: 'center', color: 'var(--color-text-muted)' }}>
          Loading dataset governance metrics...
        </div>
      ) : (
        <div>
          <div className="card" style={{ marginBottom: 24 }}>
            <h3 style={{ fontSize: '1.25rem', color: 'var(--color-primary)', marginBottom: 16 }}>
              Data Quality Governance & Verification Protocols
            </h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.88rem' }}>
              <thead>
                <tr style={{ background: 'var(--color-surface-alt)', borderBottom: '2px solid var(--color-border)' }}>
                  <th style={{ padding: '12px 16px', fontWeight: 800 }}>Audit Characteristic</th>
                  <th style={{ padding: '12px 16px', fontWeight: 800 }}>Scientific Verification Standard</th>
                  <th style={{ padding: '12px 16px', fontWeight: 800 }}>EATGOOD Governance Protocol</th>
                </tr>
              </thead>
              <tbody>
                {[
                  {
                    characteristic: 'Thermodynamic Macro Consistency',
                    standard: 'Energy, Carbohydrates, Protein, and Fat alignment',
                    protocol: 'Original manufacturer declarations verified and preserved without silent distortion.'
                  },
                  {
                    characteristic: 'Macronutrient Mass Conservation',
                    standard: 'Carbohydrates + Protein + Fat ≤ Stated Serving Size',
                    protocol: 'Physical consistency verified; converted to standard per 100g basis where verified.'
                  },
                  {
                    characteristic: 'Strict Null Protocol (No Silent Zeroes)',
                    standard: 'Missing nutrients must remain explicitly null',
                    protocol: 'Zeroes are never substituted for missing declarations; missing data refusal active.'
                  },
                  {
                    characteristic: 'Primary Indian Catalogue Source Priority',
                    standard: 'Local Indian packaged foods prioritised over third-party feeds',
                    protocol: 'Protected local baseline; Open Food Facts queried for image enrichment and barcode discovery.'
                  },
                  {
                    characteristic: 'Statutory Nutrition Standards Alignment',
                    standard: 'WHO SEARO Regional Model & FSSAI Indian Nutrition Rating (Draft 2022)',
                    protocol: 'Dual-layered scoring separates objective FoPL grade from user health goals.'
                  }
                ].map((row, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <td style={{ padding: '14px 16px', fontWeight: 600 }}>{row.characteristic}</td>
                    <td style={{ padding: '14px 16px', color: 'var(--color-text-muted)' }}>{row.standard}</td>
                    <td style={{ padding: '14px 16px' }}>
                      <span className="badge badge-verified" style={{ fontSize: '0.75rem' }}>
                        {row.protocol}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ background: '#fff', border: '1px solid var(--color-border)', borderRadius: 12, padding: 20 }}>
            <h4 style={{ fontSize: '1rem', color: 'var(--color-primary)', marginBottom: 8 }}>
              Standardization & Missing-Data Protocols:
            </h4>
            <ul style={{ margin: 0, paddingLeft: 20, fontSize: '0.85rem', color: 'var(--color-text-muted)', lineHeight: 1.6 }}>
              <li><strong>No Automatic Zero-Filling:</strong> Missing sugars, sodium, trans fat, or fibre values are stored as null (blank), never substituted with 0.0g.</li>
              <li><strong>Refusal of Unverifiable Basis:</strong> Records with ambiguous serving units or unconfirmed measurement basis have standardization halted until manufacturer audit.</li>
              <li><strong>Image Enrichment Priority:</strong> Front-of-pack and label photos matched exclusively via exact GS1 barcode or brand-product alignment.</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
