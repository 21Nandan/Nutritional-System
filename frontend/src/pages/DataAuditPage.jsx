import React, { useState, useEffect } from 'react';
import { ShieldAlert, AlertTriangle, CheckCircle2, Search, Table, FileSpreadsheet, Scale, Info } from 'lucide-react';

export default function DataAuditPage({ onSelectProduct }) {
  const [auditData, setAuditData] = useState(null);
  const [activeTab, setActiveTab] = useState('summary'); // 'summary', 'atwater78', 'serving13'
  const [loading, setLoading] = useState(true);
  const [atwaterSearch, setAtwaterSearch] = useState('');

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

  const atwaterList = auditData?.atwater_discrepancies_sample || [];
  const servingList = auditData?.macro_serving_discrepancies || [];

  const filteredAtwater = atwaterList.filter(item => 
    !atwaterSearch || 
    item.product_name.toLowerCase().includes(atwaterSearch.toLowerCase()) ||
    item.brand.toLowerCase().includes(atwaterSearch.toLowerCase()) ||
    item.category.toLowerCase().includes(atwaterSearch.toLowerCase())
  );

  return (
    <div className="data-audit-page">
      <div style={{ marginBottom: 28 }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          background: '#fff3e0',
          color: '#e65100',
          padding: '4px 12px',
          borderRadius: 20,
          fontSize: '0.8rem',
          fontWeight: 700,
          marginBottom: 10
        }}>
          <ShieldAlert size={14} color="#e65100" />
          <span>Scientific Data Quality & Verification Audit</span>
        </div>
        <h1 style={{ fontSize: '2.2rem', color: 'var(--color-primary)', marginBottom: 8 }}>
          Dataset Quality & Discrepancy Inspection
        </h1>
        <p style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem' }}>
          Real-time audit of the 852 Indian packaged products dataset, documenting Atwater calorie anomalies, serving size contradictions, and standardization rules.
        </p>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 24, borderBottom: '1px solid var(--color-border)', paddingBottom: 12 }}>
        <button
          className={`btn-secondary ${activeTab === 'summary' ? 'active' : ''}`}
          onClick={() => setActiveTab('summary')}
          style={{ background: activeTab === 'summary' ? 'var(--color-primary)' : '#fff', color: activeTab === 'summary' ? '#fff' : 'inherit' }}
        >
          <FileSpreadsheet size={16} />
          <span>Audit Summary & Completeness</span>
        </button>
        <button
          className={`btn-secondary ${activeTab === 'atwater78' ? 'active' : ''}`}
          onClick={() => setActiveTab('atwater78')}
          style={{ background: activeTab === 'atwater78' ? 'var(--color-primary)' : '#fff', color: activeTab === 'atwater78' ? '#fff' : 'inherit' }}
        >
          <AlertTriangle size={16} color={activeTab === 'atwater78' ? '#fff' : '#e65100'} />
          <span>78 Atwater Calorie Anomalies</span>
        </button>
        <button
          className={`btn-secondary ${activeTab === 'serving13' ? 'active' : ''}`}
          onClick={() => setActiveTab('serving13')}
          style={{ background: activeTab === 'serving13' ? 'var(--color-primary)' : '#fff', color: activeTab === 'serving13' ? '#fff' : 'inherit' }}
        >
          <Scale size={16} color={activeTab === 'serving13' ? '#fff' : '#c62828'} />
          <span>13 Macro &gt; Serving Discrepancies</span>
        </button>
      </div>

      {loading ? (
        <div style={{ padding: '60px 0', textAlign: 'center', color: 'var(--color-text-muted)' }}>
          Loading dataset audit metrics...
        </div>
      ) : activeTab === 'summary' ? (
        /* Tab 1: Summary Table */
        <div>
          <div className="card" style={{ marginBottom: 24 }}>
            <h3 style={{ fontSize: '1.25rem', color: 'var(--color-primary)', marginBottom: 16 }}>
              Dataset Metrics & Quality Assessment
            </h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.88rem' }}>
              <thead>
                <tr style={{ background: 'var(--color-surface-alt)', borderBottom: '2px solid var(--color-border)' }}>
                  <th style={{ padding: '12px 16px', fontWeight: 800 }}>Audit Metric / Characteristic</th>
                  <th style={{ padding: '12px 16px', fontWeight: 800 }}>Record Count</th>
                  <th style={{ padding: '12px 16px', fontWeight: 800 }}>Percentage</th>
                  <th style={{ padding: '12px 16px', fontWeight: 800 }}>EATGOOD Data Governance Policy</th>
                </tr>
              </thead>
              <tbody>
                {auditData?.quality_summary?.map((row, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <td style={{ padding: '12px 16px', fontWeight: 600 }}>{row.Metric}</td>
                    <td style={{ padding: '12px 16px', fontFamily: 'monospace', fontWeight: 700 }}>{row.Count}</td>
                    <td style={{ padding: '12px 16px' }}>{row.Percentage}</td>
                    <td style={{ padding: '12px 16px' }}>
                      <span className="badge badge-neutral" style={{ fontSize: '0.75rem' }}>
                        {row['Evaluation Status']}
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
              <li><strong>Preservation of Original Values:</strong> Raw source declarations in <code>packaged_foods_india.csv</code> are never destructively overwritten.</li>
              <li><strong>No Automatic Zero-Filling:</strong> Missing sugars, sodium, trans fat, or fibre values are stored as null (blank), never substituted with 0.0g.</li>
              <li><strong>Refusal of Unverifiable Basis:</strong> Records with ambiguous serving units or unconfirmed measurement basis have standardization halted until manufacturer audit.</li>
            </ul>
          </div>
        </div>
      ) : activeTab === 'atwater78' ? (
        /* Tab 2: 78 Atwater Discrepancies */
        <div>
          <div className="card" style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div>
                <h3 style={{ fontSize: '1.25rem', color: 'var(--color-primary)' }}>
                  The 78 Calorie Discrepancy Records (Atwater Inconsistency)
                </h3>
                <p style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', marginTop: 2 }}>
                  Products where <code>|Reported Energy - Calculated (4C + 4P + 9F)| &gt; 50 kcal</code> or exceeds 25% delta.
                </p>
              </div>
              <input
                type="text"
                placeholder="Filter by product or brand..."
                value={atwaterSearch}
                onChange={e => setAtwaterSearch(e.target.value)}
                style={{
                  padding: '8px 14px',
                  borderRadius: 6,
                  border: '1px solid var(--color-border)',
                  fontSize: '0.85rem',
                  width: 240
                }}
              />
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.82rem' }}>
                <thead>
                  <tr style={{ background: 'var(--color-surface-alt)', borderBottom: '2px solid var(--color-border)' }}>
                    <th style={{ padding: '10px 14px' }}>Product</th>
                    <th style={{ padding: '10px 14px' }}>Category</th>
                    <th style={{ padding: '10px 14px' }}>Reported (kcal)</th>
                    <th style={{ padding: '10px 14px' }}>Atwater (kcal)</th>
                    <th style={{ padding: '10px 14px' }}>Delta</th>
                    <th style={{ padding: '10px 14px' }}>Audit Diagnosis</th>
                    <th style={{ padding: '10px 14px' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAtwater.map(item => (
                    <tr key={item.product_id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                      <td style={{ padding: '10px 14px' }}>
                        <strong>{item.product_name}</strong>
                        <div style={{ fontSize: '0.72rem', color: 'var(--color-text-subtle)' }}>{item.brand}</div>
                      </td>
                      <td style={{ padding: '10px 14px' }}>{item.category}</td>
                      <td style={{ padding: '10px 14px', fontFamily: 'monospace', fontWeight: 700 }}>{item.energy_kcal}</td>
                      <td style={{ padding: '10px 14px', fontFamily: 'monospace' }}>{item.calculated_atwater_kcal}</td>
                      <td style={{ padding: '10px 14px', color: '#c62828', fontWeight: 700 }}>
                        {item.absolute_difference} kcal ({item.percentage_difference}%)
                      </td>
                      <td style={{ padding: '10px 14px', color: 'var(--color-text-muted)' }}>
                        {item.potential_cause}
                      </td>
                      <td style={{ padding: '10px 14px' }}>
                        <button
                          className="btn-secondary"
                          style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                          onClick={() => onSelectProduct(item.product_id)}
                        >
                          Inspect
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        /* Tab 3: 13 Macro > Serving Discrepancies */
        <div>
          <div className="card">
            <h3 style={{ fontSize: '1.25rem', color: '#c62828', marginBottom: 6 }}>
              The 13 Critical Inconsistencies (Macronutrients &gt; Stated Serving Size)
            </h3>
            <p style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', marginBottom: 20 }}>
              Physical contradiction where <code>Carbohydrates + Protein + Fat &gt; Stated Serving Size</code>. Typically caused by declaring per-100g nutrition while stating a 15g-25g package serving.
            </p>

            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ background: '#ffebee', borderBottom: '2px solid #ffcdd2' }}>
                  <th style={{ padding: '10px 14px', color: '#c62828' }}>Product</th>
                  <th style={{ padding: '10px 14px', color: '#c62828' }}>Category</th>
                  <th style={{ padding: '10px 14px', color: '#c62828' }}>Stated Serving Size</th>
                  <th style={{ padding: '10px 14px', color: '#c62828' }}>Macro Sum (C+P+F)</th>
                  <th style={{ padding: '10px 14px', color: '#c62828' }}>Excess Weight</th>
                  <th style={{ padding: '10px 14px', color: '#c62828' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {servingList.map(item => (
                  <tr key={item.product_id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <td style={{ padding: '10px 14px' }}>
                      <strong>{item.product_name}</strong>
                      <div style={{ fontSize: '0.72rem', color: 'var(--color-text-subtle)' }}>{item.brand}</div>
                    </td>
                    <td style={{ padding: '10px 14px' }}>{item.category}</td>
                    <td style={{ padding: '10px 14px', fontFamily: 'monospace', fontWeight: 700, color: '#c62828' }}>
                      {item.serving_size} {item.serving_size_unit}
                    </td>
                    <td style={{ padding: '10px 14px', fontFamily: 'monospace', fontWeight: 700 }}>
                      {item.macro_sum_g}g
                    </td>
                    <td style={{ padding: '10px 14px', color: '#c62828', fontWeight: 700 }}>
                      +{item.macro_excess_g}g excess
                    </td>
                    <td style={{ padding: '10px 14px' }}>
                      <button
                        className="btn-secondary"
                        style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                        onClick={() => onSelectProduct(item.product_id)}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
