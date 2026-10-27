import React, { useState } from 'react';
import { X, ShieldCheck, FileText, CheckCircle2, AlertTriangle, Lock, Eye, Database } from 'lucide-react';
import { useLockBodyScroll } from './useLockBodyScroll';

export default function LegalModal({ isOpen, onClose, initialTab = 'privacy' }) {
  useLockBodyScroll(isOpen);
  const [activeTab, setActiveTab] = useState(initialTab); // 'privacy' or 'terms'

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose} style={{ zIndex: 1100 }}>
      <div 
        className="modal-card" 
        onClick={e => e.stopPropagation()} 
        style={{ 
          maxWidth: 720, 
          maxHeight: '85vh', 
          display: 'flex', 
          flexDirection: 'column',
          padding: 0,
          overflow: 'hidden'
        }}
      >
        {/* Modal Header */}
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid var(--color-border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'var(--color-surface)'
        }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <div style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: 'var(--color-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff'
            }}>
              {activeTab === 'privacy' ? <ShieldCheck size={18} /> : <FileText size={18} />}
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '1.2rem', color: 'var(--color-primary)' }}>
                {activeTab === 'privacy' ? 'Privacy Policy & Data Ethics' : 'Terms & Conditions of Service'}
              </h3>
              <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--color-text-subtle)' }}>
                EATGOOD Platform Governance • Last Updated: October 2026
              </p>
            </div>
          </div>

          <button 
            onClick={onClose} 
            style={{ 
              background: 'none', 
              border: 'none', 
              cursor: 'pointer', 
              color: 'var(--color-text-subtle)',
              padding: 4
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Tab Switcher */}
        <div style={{
          display: 'flex',
          borderBottom: '1px solid var(--color-border)',
          background: 'var(--color-surface-alt)'
        }}>
          <button
            onClick={() => setActiveTab('privacy')}
            style={{
              flex: 1,
              padding: '12px 16px',
              border: 'none',
              background: activeTab === 'privacy' ? '#fff' : 'transparent',
              color: activeTab === 'privacy' ? 'var(--color-primary)' : 'var(--color-text-muted)',
              fontWeight: 700,
              fontSize: '0.85rem',
              cursor: 'pointer',
              borderBottom: activeTab === 'privacy' ? '2px solid var(--color-accent)' : 'none',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8
            }}
          >
            <Lock size={15} />
            <span>Privacy Policy</span>
          </button>

          <button
            onClick={() => setActiveTab('terms')}
            style={{
              flex: 1,
              padding: '12px 16px',
              border: 'none',
              background: activeTab === 'terms' ? '#fff' : 'transparent',
              color: activeTab === 'terms' ? 'var(--color-primary)' : 'var(--color-text-muted)',
              fontWeight: 700,
              fontSize: '0.85rem',
              cursor: 'pointer',
              borderBottom: activeTab === 'terms' ? '2px solid var(--color-accent)' : 'none',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8
            }}
          >
            <FileText size={15} />
            <span>Terms & Conditions</span>
          </button>
        </div>

        {/* Modal Body / Scrollable Content */}
        <div style={{ padding: '24px', overflowY: 'auto', overscrollBehavior: 'contain', flex: 1, fontSize: '0.85rem', color: 'var(--color-text-main)', lineHeight: 1.6 }}>
          {activeTab === 'privacy' ? (
            /* PRIVACY POLICY */
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div style={{ background: '#f1f8e9', padding: 14, borderRadius: 8, border: '1px solid #c8e6c9', display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <CheckCircle2 size={18} color="#2e7d32" style={{ flexShrink: 0, marginTop: 2 }} />
                <p style={{ margin: 0, fontSize: '0.8rem', color: '#1b5e20' }}>
                  <strong>Local-First Guarantee:</strong> EATGOOD operates 100% on your host computer. Your health goals, dietary preferences, scanned food labels, and bookmark records are processed locally and never transmitted to external cloud servers.
                </p>
              </div>

              <div>
                <h4 style={{ color: 'var(--color-primary)', fontSize: '0.98rem', marginBottom: 6 }}>
                  1. Data Collection & Local Storage Architecture
                </h4>
                <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>
                  We practice strict data minimization. The application collects only the parameters explicitly required to calibrate Layer 2 personalized scoring and Layer 3 allergen safety exclusions. All user profiles, dietary restriction lists, and product search histories reside exclusively in your local SQLite database (<code>eatgood_app.db</code>) and browser local storage.
                </p>
              </div>

              <div>
                <h4 style={{ color: 'var(--color-primary)', fontSize: '0.98rem', marginBottom: 6 }}>
                  2. Offline OCR & Image Processing Privacy
                </h4>
                <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>
                  When you upload photograph files (JPEG, PNG) for label analysis, text recognition is handled offline through native computer vision libraries running directly in your execution environment. Images are never transmitted across the public internet, sold, or shared with commercial AI vision APIs.
                </p>
              </div>

              <div>
                <h4 style={{ color: 'var(--color-primary)', fontSize: '0.98rem', marginBottom: 6 }}>
                  3. Zero Third-Party Telemetry & No Behavioral Tracking
                </h4>
                <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>
                  EATGOOD employs no marketing pixels, analytics beacons, behavioral fingerprinting scripts, or third-party cookies. The platform does not profile consumer purchasing habits, monitor user location, or sell data to packaged food manufacturers or insurers.
                </p>
              </div>

              <div>
                <h4 style={{ color: 'var(--color-primary)', fontSize: '0.98rem', marginBottom: 6 }}>
                  4. User Autonomy, Data Portability & Complete Erasure
                </h4>
                <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>
                  You maintain unconditional control over your dietary data. At any moment, you can modify your stated nutrition goals, remove individual food items from your saved favorites, or reset the local database without external approval.
                </p>
              </div>

              <div>
                <h4 style={{ color: 'var(--color-primary)', fontSize: '0.98rem', marginBottom: 6 }}>
                  5. Ethical Machine Learning Transparency
                </h4>
                <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>
                  The integrated machine learning suitability model serves as an experimental secondary perspective trained on synthetic, rule-based data points. Deterministic, evidence-based nutrition standards (WHO & FSSAI benchmarks) remain the primary ground truth.
                </p>
              </div>
            </div>
          ) : (
            /* TERMS & CONDITIONS */
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div style={{ background: '#fff3e0', padding: 14, borderRadius: 8, border: '1px solid #ffe0b2', display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <AlertTriangle size={18} color="#e65100" style={{ flexShrink: 0, marginTop: 2 }} />
                <p style={{ margin: 0, fontSize: '0.8rem', color: '#e65100' }}>
                  <strong>Important Medical Notice:</strong> EATGOOD is an evidence-based educational and nutritional assessment tool. It does not provide medical diagnosis, prescribe therapeutic diets, or substitute for personalized medical consultation.
                </p>
              </div>

              <div>
                <h4 style={{ color: 'var(--color-primary)', fontSize: '0.98rem', marginBottom: 6 }}>
                  1. Purpose & Scope of Application
                </h4>
                <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>
                  EATGOOD evaluates packaged food labels against international and national nutritional reference models (WHO SEARO Nutrient Profile Model 2017 and FSSAI Indian Nutrition Rating criteria). The platform is intended to assist consumers in demystifying front-of-pack and back-of-pack nutrition claims, hidden sugars, sodium density, and food additives.
                </p>
              </div>

              <div>
                <h4 style={{ color: 'var(--color-primary)', fontSize: '0.98rem', marginBottom: 6 }}>
                  2. Severe Allergens & Anaphylaxis Disclaimer
                </h4>
                <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>
                  While the platform includes rigorous Layer 3 allergen alerts that automatically override scores to zero for declared conflicting allergens, manufacturing formulations and factory cross-contact conditions may change without notice. Individuals with life-threatening food allergies or severe anaphylactic conditions <strong>must always physically verify the physical packaging</strong> and contact the manufacturer before consumption.
                </p>
              </div>

              <div>
                <h4 style={{ color: 'var(--color-primary)', fontSize: '0.98rem', marginBottom: 6 }}>
                  3. User Responsibility for OCR Verification
                </h4>
                <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>
                  Optical Character Recognition extractions from smartphone photos are sensitive to lighting, glare, and curved surfaces. Users are required to inspect and confirm extracted nutritional values, serving sizes, and ingredients before relying on the assessment output. EATGOOD provides an editable verification step specifically for this purpose.
                </p>
              </div>

              <div>
                <h4 style={{ color: 'var(--color-primary)', fontSize: '0.98rem', marginBottom: 6 }}>
                  4. Non-Affiliation & Regulatory Independence
                </h4>
                <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>
                  EATGOOD operates independently and is not legally affiliated with, certified by, or officially representing the Food Safety and Standards Authority of India (FSSAI), the World Health Organization (WHO), or the Codex Alimentarius Commission. Product ratings represent computational benchmarks against published reference standards and do not constitute statutory compliance certification.
                </p>
              </div>

              <div>
                <h4 style={{ color: 'var(--color-primary)', fontSize: '0.98rem', marginBottom: 6 }}>
                  5. Calibrated vs. Uncalibrated Categories
                </h4>
                <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>
                  Automated letter grades are strictly calibrated for Snacks, Breakfast Cereals, and Packaged Beverages where reliable comparative benchmarks exist. Other categories (Chocolates, Instant Foods, Condiments, Dairy) display raw nutritional disclosures with explicit disclaimers regarding calibration scope.
                </p>
              </div>

              <div>
                <h4 style={{ color: 'var(--color-primary)', fontSize: '0.98rem', marginBottom: 6 }}>
                  6. Limitation of Liability
                </h4>
                <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>
                  The software is provided on an &quot;as is&quot; basis without warranty of any kind. The developers, contributors, and affiliated academic institutions disclaim all liability for any direct, indirect, incidental, or consequential health issues or consumer purchasing decisions resulting from the use of this software.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div style={{
          padding: '14px 24px',
          borderTop: '1px solid var(--color-border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          background: 'var(--color-surface)'
        }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)' }}>
            EATGOOD Intelligence Platform &bull; Offline Architecture
          </span>
          <button 
            className="btn-primary" 
            onClick={onClose}
            style={{ padding: '8px 20px', fontSize: '0.85rem' }}
          >
            I Understand &amp; Agree
          </button>
        </div>
      </div>
    </div>
  );
}
