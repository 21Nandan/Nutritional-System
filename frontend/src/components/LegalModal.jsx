import React, { useState } from 'react';
import { X, ShieldCheck, FileText, CheckCircle2, AlertTriangle, Lock } from 'lucide-react';
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
                  <strong>In short:</strong> your profile, saved products and history are stored only in this browser. Label photos are read on your device and never uploaded. EATGOOD has no accounts and stores nothing that identifies you.
                </p>
              </div>

              <div>
                <h4 style={{ color: 'var(--color-primary)', fontSize: '0.98rem', marginBottom: 6 }}>
                  1. What stays on your device
                </h4>
                <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>
                  Your profile (name, goals, diet, allergens, age group, activity level), saved products and assessment history are kept in this browser&apos;s local storage. Clearing site data or using another browser removes them. Label photos are processed by a text reader that runs inside your browser.
                </p>
              </div>
              <div>
                <h4 style={{ color: 'var(--color-primary)', fontSize: '0.98rem', marginBottom: 6 }}>
                  2. What is sent to the EATGOOD server
                </h4>
                <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>
                  To compute results, your browser sends: your goal, dietary preference and allergens (with each request, not stored); product IDs, barcodes and search terms; the text recognised from a label photo; and any values you type in. The server runs on Vercel. It keeps short-lived technical logs (time, page path, status) without search terms or profile data, and a cache of Open Food Facts lookups.
                </p>
              </div>
              <div>
                <h4 style={{ color: 'var(--color-primary)', fontSize: '0.98rem', marginBottom: 6 }}>
                  3. What is shared with others
                </h4>
                <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>
                  If you choose to contribute a missing product, what you submit is stored without your identity and can be shown, marked as unreviewed, to anyone who scans the same barcode. When a barcode is not in our catalogue, the server asks Open Food Facts about that barcode or search term (never your profile). Product photos are loaded by your browser directly from Open Food Facts&apos; image servers.
                </p>
              </div>
              <div>
                <h4 style={{ color: 'var(--color-primary)', fontSize: '0.98rem', marginBottom: 6 }}>
                  4. Analytics
                </h4>
                <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>
                  Vercel Web Analytics counts anonymous page views (no cookies, no cross-site tracking). There are no advertising pixels and no data is sold.
                </p>
              </div>
              <div>
                <h4 style={{ color: 'var(--color-primary)', fontSize: '0.98rem', marginBottom: 6 }}>
                  5. Your control
                </h4>
                <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>
                  You can change or clear your profile at any time, remove saved products, and clear your history from the profile page. Clearing this site&apos;s data in your browser deletes everything EATGOOD stored on your device.
                </p>
              </div>
            </div>
          ) : (
            /* TERMS & CONDITIONS */
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div style={{ background: '#fff3e0', padding: 14, borderRadius: 8, border: '1px solid #ffe0b2', display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <AlertTriangle size={18} color="#e65100" style={{ flexShrink: 0, marginTop: 2 }} />
                <p style={{ margin: 0, fontSize: '0.8rem', color: '#e65100' }}>
                  <strong>Important medical notice:</strong> EATGOOD is an informational tool. It does not provide medical diagnosis, prescribe therapeutic diets, or substitute for personalized medical consultation.
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
                  5. Category-Specific Benchmarks
                </h4>
                <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>
                  Letter grades are given for Snacks, Breakfast Cereals, Packaged Beverages, Biscuits &amp; Bakery, Instant Foods and Dairy, using category thresholds informed by WHO SEARO and FSSAI documents. Chocolates &amp; Sweets and Condiments &amp; Spreads show their nutrition values without a grade, because no suitable threshold model is used for them.
                </p>
              </div>

              <div>
                <h4 style={{ color: 'var(--color-primary)', fontSize: '0.98rem', marginBottom: 6 }}>
                  6. Limitation of Liability
                </h4>
                <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>
                  The software is provided on an &quot;as is&quot; basis without warranty of any kind. The developers and contributors disclaim all liability for any direct, indirect, incidental, or consequential health issues or consumer purchasing decisions resulting from the use of this software.
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
            EATGOOD &bull; Informational only, not medical advice
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
