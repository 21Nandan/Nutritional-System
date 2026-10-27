import React from 'react';
import { Shield, BookOpen, Database, HeartHandshake } from 'lucide-react';

export default function Footer({ setActivePage }) {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
            <div style={{
              width: 28,
              height: 28,
              borderRadius: 6,
              background: '#58a834',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontWeight: 800
            }}>
              E
            </div>
            <h3 style={{ color: '#fff', fontSize: '1.2rem', margin: 0 }}>EATGOOD</h3>
          </div>
          <p style={{ color: '#b0c9bb', lineHeight: 1.6, fontSize: '0.85rem', marginBottom: 16 }}>
            AI-Powered Personalized Food Safety and Nutrition Assessment.
            Transforming complicated front-of-pack and back-of-pack food labels into simple, transparent, evidence-based recommendations.
          </p>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#82c733', fontSize: '0.78rem', fontWeight: 600 }}>
            <HeartHandshake size={15} />
            <span>Academic Experiential Learning (EL Phase-I) Project — AI for Social Good</span>
          </div>
        </div>

        <div>
          <h4>Explore</h4>
          <ul>
            <li><a href="#scanner" onClick={(e) => { e.preventDefault(); setActivePage('scanner'); }}>Label Scanner</a></li>
            <li><a href="#catalogue" onClick={(e) => { e.preventDefault(); setActivePage('catalogue'); }}>Product Catalogue</a></li>
            <li><a href="#compare" onClick={(e) => { e.preventDefault(); setActivePage('compare'); }}>Product Comparison</a></li>
            <li><a href="#dashboard" onClick={(e) => { e.preventDefault(); setActivePage('dashboard'); }}>User Dashboard</a></li>
          </ul>
        </div>

        <div>
          <h4>Research & Ethics</h4>
          <ul>
            <li><a href="#methodology" onClick={(e) => { e.preventDefault(); setActivePage('methodology'); }}>Methodology & Citations</a></li>
            <li><a href="#audit" onClick={(e) => { e.preventDefault(); setActivePage('audit'); }}>Data Quality Audit</a></li>
            <li><a href="#standards" onClick={(e) => { e.preventDefault(); setActivePage('audit'); }}>WHO & FSSAI Standards</a></li>
            <li><span style={{ color: '#7e9e8c' }}>Simulated ML Training Ethics</span></li>
          </ul>
        </div>

        <div>
          <h4>Important Disclaimer</h4>
          <p style={{ color: '#8da698', fontSize: '0.8rem', lineHeight: 1.5, background: 'rgba(255,255,255,0.05)', padding: 12, borderRadius: 8 }}>
            EATGOOD is an educational, research-oriented food assessment platform. It does not provide clinical diagnoses, 
            prescribe medical diets, or guarantee regulatory certification. Consult a registered dietitian or physician for individual medical requirements.
          </p>
        </div>
      </div>

      <div className="footer-bottom">
        <div>&copy; 2026 EATGOOD Academic Research Team. All rights reserved. Locally executed research prototype.</div>
        <div style={{ display: 'flex', gap: 16 }}>
          <span>FastAPI Microservice</span>
          <span>•</span>
          <span>Scikit-Learn Architecture</span>
        </div>
      </div>
    </footer>
  );
}
