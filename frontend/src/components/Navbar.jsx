import React from 'react';
import { 
  Sparkles, Search, ScanLine, ArrowLeftRight, 
  BarChart3, ShieldCheck, UserCheck 
} from 'lucide-react';

export default function Navbar({ activePage, setActivePage, activeProfile, onOpenProfile }) {
  const navItems = [
    { id: 'landing', label: 'Home', icon: Sparkles },
    { id: 'scanner', label: 'Label Scanner', icon: ScanLine },
    { id: 'catalogue', label: 'Catalogue (852)', labelSub: 'Products', icon: Search },
    { id: 'compare', label: 'Compare', icon: ArrowLeftRight },
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
    { id: 'audit', label: 'Data Quality Audit', icon: ShieldCheck }
  ];

  return (
    <header className="navbar">
      <div className="nav-inner">
        <div 
          className="brand-logo" 
          onClick={() => setActivePage('landing')} 
          style={{ cursor: 'pointer' }}
        >
          <div style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: 'linear-gradient(135deg, #143828 0%, #58a834 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontWeight: 800,
            fontSize: '1.1rem'
          }}>
            E
          </div>
          <span>EATGOOD</span>
          <span className="brand-pill">AI Platform</span>
        </div>

        <nav className="nav-links">
          {navItems.map(item => {
            const Icon = item.icon;
            const isActive = activePage === item.id;
            return (
              <button
                key={item.id}
                className={`nav-btn ${isActive ? 'active' : ''}`}
                onClick={() => setActivePage(item.id)}
              >
                <Icon size={16} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="user-profile-pill" onClick={onOpenProfile} title="Configure Profile">
          <UserCheck size={16} color="#58a834" />
          <div>
            <span style={{ color: 'var(--color-text-main)' }}>{activeProfile?.goal || 'Balanced Choices'}</span>
            <span style={{ color: 'var(--color-text-subtle)', marginLeft: 6, fontSize: '0.75rem' }}>
              ({activeProfile?.dietary_preference || 'No pref'})
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
