import React, { useState } from 'react';
import { 
  Home, Search, ScanLine, ArrowLeftRight, 
  User, ShieldCheck, Menu, X 
} from 'lucide-react';
import logoImg from '../assets/logo.png';

export default function Navbar({ activePage, setActivePage }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { id: 'landing', label: 'Home', icon: Home },
    { id: 'scanner', label: 'Label Scanner', icon: ScanLine },
    { id: 'catalogue', label: 'Catalogue', labelSub: 'Products', icon: Search },
    { id: 'compare', label: 'Compare', icon: ArrowLeftRight },
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'audit', label: 'Data Quality Audit', icon: ShieldCheck }
  ];

  const handleNavClick = (id) => {
    setActivePage(id);
    setMobileMenuOpen(false);
  };

  return (
    <header className="navbar">
      <div className="nav-inner">
        <div 
          className="brand-logo" 
          onClick={() => handleNavClick('landing')} 
          style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10 }}
        >
          <img 
            src={logoImg} 
            alt="EATGOOD Logo" 
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              objectFit: 'contain'
            }}
          />
          <span>EATGOOD</span>
        </div>

        {/* Desktop Navigation Links */}
        <nav className="nav-links desktop-nav">
          {navItems.map(item => {
            const Icon = item.icon;
            const isActive = activePage === item.id;
            return (
              <button
                key={item.id}
                className={`nav-btn ${isActive ? 'active' : ''}`}
                onClick={() => handleNavClick(item.id)}
              >
                <Icon size={16} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Mobile Hamburger Toggle Button */}
        <button 
          className="mobile-menu-toggle"
          onClick={() => setMobileMenuOpen(prev => !prev)}
          aria-label={mobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
          style={{
            display: 'none',
            alignItems: 'center',
            justifyContent: 'center',
            width: 44,
            height: 44,
            borderRadius: 8,
            color: 'var(--color-primary)',
            background: 'var(--color-surface-alt)',
            border: '1px solid var(--color-border)',
            cursor: 'pointer'
          }}
        >
          {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {/* Mobile Menu Dropdown / Drawer */}
      {mobileMenuOpen && (
        <div 
          className="mobile-nav-drawer"
          style={{
            borderTop: '1px solid var(--color-border)',
            background: 'var(--color-surface)',
            padding: '12px 16px 20px',
            boxShadow: 'var(--shadow-md)'
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {navItems.map(item => {
              const Icon = item.icon;
              const isActive = activePage === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => handleNavClick(item.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    padding: '12px 16px',
                    borderRadius: 'var(--radius-md)',
                    fontSize: '0.95rem',
                    fontWeight: 600,
                    textAlign: 'left',
                    color: isActive ? 'var(--color-primary)' : 'var(--color-text-main)',
                    background: isActive ? 'var(--color-accent-subtle)' : 'transparent',
                    border: 'none',
                    width: '100%',
                    cursor: 'pointer',
                    minHeight: 44
                  }}
                >
                  <Icon size={18} color={isActive ? 'var(--color-accent)' : 'var(--color-text-muted)'} />
                  <span>{item.label}</span>
                  {isActive && (
                    <span style={{ marginLeft: 'auto', width: 6, height: 6, borderRadius: '50%', background: 'var(--color-accent)' }} />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </header>
  );
}
