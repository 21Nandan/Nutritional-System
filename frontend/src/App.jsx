import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import ProfileModal from './components/ProfileModal';
import LandingPage from './pages/LandingPage';
import ProductCatalogue from './pages/ProductCatalogue';
import LabelScanner from './pages/LabelScanner';
import ProductAssessment from './pages/ProductAssessment';
import ProductComparison from './pages/ProductComparison';
import Dashboard from './pages/Dashboard';
import MethodologyPage from './pages/MethodologyPage';
import DataAuditPage from './pages/DataAuditPage';

export default function App() {
  const [activePage, setActivePage] = useState('landing');
  const [selectedProductId, setSelectedProductId] = useState(null);
  const [customAssessment, setCustomAssessment] = useState(null);
  const [compareIds, setCompareIds] = useState(['IND_PKG_001', 'IND_PKG_002']);
  const [activeProfile, setActiveProfile] = useState(null);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);

  useEffect(() => {
    // Load active profile from backend SQLite database
    fetch('/api/profile')
      .then(res => res.json())
      .then(data => setActiveProfile(data))
      .catch(err => {
        console.error('Error fetching profile:', err);
        setActiveProfile({
          user_id: 'USR_DEFAULT',
          name: 'Evaluator',
          goal: 'Balanced Choices',
          dietary_preference: 'No preference',
          allergens_to_avoid: ''
        });
      });
  }, []);

  const handleSelectProduct = (productId) => {
    setSelectedProductId(productId);
    setCustomAssessment(null);
    setActivePage('assessment');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleAssessmentGenerated = (assessmentData) => {
    setCustomAssessment(assessmentData);
    setSelectedProductId(assessmentData.product_id);
    setActivePage('assessment');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleCompareProduct = (productId) => {
    if (!compareIds.includes(productId)) {
      setCompareIds(prev => [productId, ...prev.slice(0, 3)]);
    }
    setActivePage('compare');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSaveProfile = (newProfile) => {
    fetch('/api/profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newProfile)
    })
      .then(res => res.json())
      .then(saved => setActiveProfile(saved))
      .catch(err => console.error(err));
  };

  return (
    <div className="app-container">
      <Navbar
        activePage={activePage}
        setActivePage={setActivePage}
        activeProfile={activeProfile}
        onOpenProfile={() => setIsProfileModalOpen(true)}
      />

      <main className="main-content">
        {activePage === 'landing' && (
          <LandingPage
            setActivePage={setActivePage}
            onSelectProduct={handleSelectProduct}
            activeProfile={activeProfile}
            onOpenProfile={() => setIsProfileModalOpen(true)}
          />
        )}

        {activePage === 'catalogue' && (
          <ProductCatalogue
            onSelectProduct={handleSelectProduct}
            onCompareProduct={handleCompareProduct}
            activeProfile={activeProfile}
          />
        )}

        {activePage === 'scanner' && (
          <LabelScanner
            onAssessmentGenerated={handleAssessmentGenerated}
            onSelectProduct={handleSelectProduct}
          />
        )}

        {activePage === 'assessment' && (
          <ProductAssessment
            productId={selectedProductId}
            assessmentData={customAssessment}
            onBack={() => setActivePage('catalogue')}
            onSelectProduct={handleSelectProduct}
            activeProfile={activeProfile}
          />
        )}

        {activePage === 'compare' && (
          <ProductComparison
            initialProductIds={compareIds}
            onSelectProduct={handleSelectProduct}
            activeProfile={activeProfile}
          />
        )}

        {activePage === 'dashboard' && (
          <Dashboard
            setActivePage={setActivePage}
            onSelectProduct={handleSelectProduct}
            activeProfile={activeProfile}
            onOpenProfile={() => setIsProfileModalOpen(true)}
          />
        )}

        {activePage === 'methodology' && (
          <MethodologyPage />
        )}

        {activePage === 'audit' && (
          <DataAuditPage
            onSelectProduct={handleSelectProduct}
          />
        )}
      </main>

      <Footer setActivePage={setActivePage} />

      <ProfileModal
        isOpen={isProfileModalOpen}
        onClose={() => setIsProfileModalOpen(false)}
        activeProfile={activeProfile}
        onSaveProfile={handleSaveProfile}
      />
    </div>
  );
}
