import React, { useState } from 'react';
import { HeartHandshake } from 'lucide-react';
import logoImg from '../assets/logo.png';
import LegalModal from './LegalModal';

export default function Footer({ setActivePage }) {
  const [legalModalOpen, setLegalModalOpen] = useState(false);
  const [legalModalTab, setLegalModalTab] = useState('privacy');
  const [heartGlow, setHeartGlow] = useState(false);

  const openLegal = (tab) => {
    setLegalModalTab(tab);
    setLegalModalOpen(true);
  };

  const handleHeartClick = () => {
    setHeartGlow(prev => !prev);
  };

  return (
    <footer className="footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <img 
              src={logoImg} 
              alt="EATGOOD Logo" 
              style={{
                width: 34,
                height: 34,
                borderRadius: 8,
                background: '#fff',
                padding: 2,
                objectFit: 'contain'
              }} 
            />
            <h3 style={{ color: '#fff', fontSize: '1.2rem', margin: 0 }}>EATGOOD</h3>
          </div>
          <p style={{ color: '#b0c9bb', lineHeight: 1.6, fontSize: '0.85rem', marginBottom: 16 }}>
            Helps you read Indian packaged food labels: a nutrition grade, a personal fit score, allergen checks and plain explanations.
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#82c733', fontSize: '0.78rem', fontWeight: 600 }}>
            <HeartHandshake size={15} />
            <span>Open-source student project</span>
          </div>
        </div>

        {/* Explore & Standards & Data: displayed side-by-side on mobile */}
        <div className="footer-nav-group">
          <div className="footer-col">
            <h4>Explore</h4>
            <ul>
              <li><a href="#scanner" onClick={(e) => { e.preventDefault(); setActivePage('scanner'); }}>Label Scanner</a></li>
              <li><a href="#catalogue" onClick={(e) => { e.preventDefault(); setActivePage('catalogue'); }}>Product Catalogue</a></li>
              <li><a href="#compare" onClick={(e) => { e.preventDefault(); setActivePage('compare'); }}>Product Comparison</a></li>
              <li><a href="#profile" onClick={(e) => { e.preventDefault(); setActivePage('profile'); }}>User Profile</a></li>
            </ul>
          </div>

          <div className="footer-col">
            <h4>Standards & Data</h4>
            <ul>
              <li><a href="#audit" onClick={(e) => { e.preventDefault(); setActivePage('audit'); }}>About the data</a></li>
              <li>
                <a href="https://world.openfoodfacts.org" target="_blank" rel="noopener noreferrer">
                  Open Food Facts (ODbL) ↗
                </a>
              </li>
              <li>
                <a 
                  href="https://www.who.int/news-room/fact-sheets/detail/healthy-diet" 
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  WHO Food Guidelines ↗
                </a>
              </li>
              <li>
                <a 
                  href="https://www.fssai.gov.in/" 
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  FSSAI Food Standards ↗
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="footer-disclaimer">
          <h4>Important Disclaimer</h4>
          <p style={{ color: '#8da698', fontSize: '0.8rem', lineHeight: 1.5, background: 'rgba(255,255,255,0.05)', padding: 12, borderRadius: 8 }}>
            Informational only, not medical advice. EATGOOD is not affiliated with or endorsed by WHO or FSSAI and does not
            certify regulatory compliance. The catalogue uses demo nutrition data; always read the actual pack. Consult a
            registered dietitian or doctor for medical needs. Product data from Open Food Facts is available under the
            Open Database License (ODbL).
          </p>
        </div>
      </div>

      <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.1)', paddingTop: 20, maxWidth: 1240, margin: '0 auto' }}>
        <div className="footer-subbar" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16, paddingBottom: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <img 
              src={logoImg} 
              alt="EATGOOD Logo" 
              style={{
                width: 26,
                height: 26,
                borderRadius: '50%',
                background: '#fff',
                padding: 2,
                objectFit: 'contain'
              }} 
            />
            <span style={{ color: '#fff', fontWeight: 600, fontSize: '0.92rem' }}>EATGOOD</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 14, color: '#8da698', fontSize: '0.82rem' }}>
            <a 
              href="#privacy" 
              onClick={(e) => { e.preventDefault(); openLegal('privacy'); }}
              style={{ color: '#8da698', textDecoration: 'none', cursor: 'pointer' }}
            >
              Privacy Policy
            </a>
            <span style={{ color: 'rgba(255,255,255,0.2)' }}>|</span>
            <a 
              href="#terms" 
              onClick={(e) => { e.preventDefault(); openLegal('terms'); }}
              style={{ color: '#8da698', textDecoration: 'none', cursor: 'pointer' }}
            >
              Terms & Conditions
            </a>
          </div>
        </div>

        <div style={{ borderTop: '1px solid rgba(255, 255, 255, 0.08)', paddingTop: 14, display: 'flex', justifyContent: 'center', textAlign: 'center' }}>
          <div style={{ color: '#8da698', fontSize: '0.78rem', lineHeight: 1.6 }}>
            <div>
              Made with{' '}
              <span
                className={`rvce-heart ${heartGlow ? 'is-glowing' : ''}`}
                onClick={handleHeartClick}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleHeartClick(); } }}
                role="button"
                tabIndex={0}
                aria-label="Made with love in Bengaluru — click to toggle glow"
                title="Made with ❤️ in Bengaluru — Click or hover to glow!"
              >
                ❤️
              </span>{' '}
              in Bengaluru &nbsp;•&nbsp; v1.0.0
            </div>
            <div>&copy; 2026 EATGOOD &nbsp;•&nbsp; All rights reserved</div>
          </div>
        </div>
      </div>

      <LegalModal
        isOpen={legalModalOpen}
        onClose={() => setLegalModalOpen(false)}
        initialTab={legalModalTab}
      />
    </footer>
  );
}
