import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import ProfileModal from './components/ProfileModal';
import OnboardingModal from './components/OnboardingModal';
import LandingPage from './pages/LandingPage';
import ProductCatalogue from './pages/ProductCatalogue';
import LabelScanner from './pages/LabelScanner';
import ProductAssessment from './pages/ProductAssessment';
import ProductComparison from './pages/ProductComparison';
import Dashboard from './pages/Dashboard';
import DataAuditPage from './pages/DataAuditPage';
import DemoDataBanner from './components/DemoDataBanner';
import { DEFAULT_PROFILE, completeOnboarding, isOnboardingComplete, loadProfile, readSession, saveProfile, writeSession } from './storage';

const PAGE_TITLES = {
  landing: 'EATGOOD — Understand Indian packaged food labels',
  catalogue: 'Catalogue — EATGOOD',
  scanner: 'Scan a label — EATGOOD',
  assessment: 'Product assessment — EATGOOD',
  compare: 'Compare products — EATGOOD',
  profile: 'Your profile — EATGOOD',
  dashboard: 'Your profile — EATGOOD',
  audit: 'Data quality — EATGOOD'
};

// URL Route Parser (supports real URL paths, search params, and hash fallback)
const getRouteFromLocation = () => {
  // Product IDs are case-sensitive, so only the route name is compared case-insensitively.
  const rawPath = window.location.pathname.replace(/^\/+|\/+$/g, '');
  const path = rawPath.toLowerCase();
  const searchParams = new URLSearchParams(window.location.search);
  const rawHash = window.location.hash.replace(/^#\/?/, '');
  const hash = rawHash.toLowerCase();

  // 1. Direct product path: /product/IND_PKG_001 or /assessment/IND_PKG_001
  const productMatch = rawPath.match(/^(?:product|assessment)\/(.+)$/i);
  if (productMatch) {
    return {
      page: 'assessment',
      productId: decodeURIComponent(productMatch[1])
    };
  }

  // 2. Query param: /assessment?id=IND_PKG_001 or ?product=IND_PKG_001
  if (path === 'assessment' || path === 'product') {
    const id = searchParams.get('id') || searchParams.get('product_id') || searchParams.get('productId');
    return {
      page: 'assessment',
      productId: id || null
    };
  }

  // 3. Compare with ids: /compare?ids=IND_PKG_001,IND_PKG_002
  if (path === 'compare') {
    const ids = searchParams.get('ids');
    return {
      page: 'compare',
      compareIds: ids ? ids.split(',').filter(Boolean) : null
    };
  }

  // 4. Standard valid paths
  const validPages = ['catalogue', 'scanner', 'compare', 'profile', 'dashboard', 'audit'];
  if (validPages.includes(path)) {
    return { page: path === 'dashboard' ? 'profile' : path };
  }

  // 5. Fallback to hash if present (e.g. #/catalogue or #scanner)
  if (hash) {
    const cleanHash = hash.replace(/^\/+/, '');
    const hashProductMatch = rawHash.replace(/^\/+/, '').match(/^(?:product|assessment)\/(.+)$/i);
    if (hashProductMatch) {
      return { page: 'assessment', productId: decodeURIComponent(hashProductMatch[1]) };
    }
    if (validPages.includes(cleanHash)) {
      return { page: cleanHash === 'dashboard' ? 'profile' : cleanHash };
    }
  }

  // 6. Default to landing / home
  return { page: 'landing' };
};

export default function App() {
  const initialRoute = getRouteFromLocation();
  const [activePage, setActivePage] = useState(initialRoute.page);
  const [selectedProductId, setSelectedProductId] = useState(initialRoute.productId || null);

  // Restore custom assessment from session storage if present across refreshes
  const [customAssessment, setCustomAssessment] = useState(() => readSession('eatgood_custom_assessment', null));

  const [compareIds, setCompareIds] = useState(() => {
    if (initialRoute.compareIds && initialRoute.compareIds.length >= 2) {
      return initialRoute.compareIds;
    }
    return readSession('eatgood_compare_ids', ['IND_PKG_001', 'IND_PKG_002']);
  });

  const [activeProfile, setActiveProfile] = useState(() => loadProfile() || DEFAULT_PROFILE);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);

  // First-time visit onboarding & terms acceptance state
  const [isOnboardingOpen, setIsOnboardingOpen] = useState(() => !isOnboardingComplete());

  // Persistent scanner form data (preserved across refreshes)
  const [scannerFormData, setScannerFormData] = useState(() => readSession('eatgood_scanner_form', null) || {
      product_name: '',
      brand: '',
      category: 'Snacks',
      serving_size: '100',
      serving_size_unit: 'g',
      measurement_basis: 'per 100g',
      energy_kcal: '',
      carbohydrates_g: '',
      sugars_g: '',
      added_sugars_g: '',
      protein_g: '',
      total_fat_g: '',
      saturated_fat_g: '',
      trans_fat_g: '',
      sodium_mg: '',
      dietary_fibre_g: '',
      ingredients: '',
      allergens_declared: '',
      marketing_claims: ''
  });

  const [scannerMode, setScannerMode] = useState('upload');

  // Navigate function that synchronizes URL, document title, and browser history
  const navigateTo = useCallback((page, params = {}, replace = false) => {
    let url = '/';
    if (page === 'landing' || page === 'home') {
      url = '/';
    } else if (page === 'catalogue') {
      url = '/catalogue';
    } else if (page === 'scanner') {
      url = '/scanner';
    } else if (page === 'compare') {
      const ids = params.ids || params.compareIds || compareIds;
      url = (ids && ids.length) ? `/compare?ids=${ids.join(',')}` : '/compare';
    } else if (page === 'profile' || page === 'dashboard') {
      url = '/profile';
    } else if (page === 'audit') {
      url = '/audit';
    } else if (page === 'assessment') {
      const pid = params.productId !== undefined ? params.productId : selectedProductId;
      url = pid ? `/product/${pid}` : '/assessment';
    }

    const title = PAGE_TITLES[page] || PAGE_TITLES.landing;
    document.title = title;

    if (replace) {
      window.history.replaceState({ page, params }, title, url);
    } else {
      const currentUrl = window.location.pathname + window.location.search;
      if (currentUrl !== url) {
        window.history.pushState({ page, params }, title, url);
      }
    }

    setActivePage(page);
    if (params.productId !== undefined) {
      setSelectedProductId(params.productId);
    }
    if (params.compareIds) {
      setCompareIds(params.compareIds);
      writeSession('eatgood_compare_ids', params.compareIds);
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [compareIds, selectedProductId]);

  // Initial load and popstate event listener for browser Back/Forward
  useEffect(() => {
    document.title = PAGE_TITLES[getRouteFromLocation().page] || PAGE_TITLES.landing;

    const handlePopState = () => {
      const currentRoute = getRouteFromLocation();
      setActivePage(currentRoute.page);
      if (currentRoute.productId) setSelectedProductId(currentRoute.productId);
      if (currentRoute.compareIds) setCompareIds(currentRoute.compareIds);
      document.title = PAGE_TITLES[currentRoute.page] || PAGE_TITLES.landing;
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const handleSelectProduct = (productId) => {
    setCustomAssessment(null);
    writeSession('eatgood_custom_assessment', null);
    navigateTo('assessment', { productId });
  };

  const handleAssessmentGenerated = (assessmentData, enteredData = null) => {
    setCustomAssessment(assessmentData);
    writeSession('eatgood_custom_assessment', assessmentData);

    if (enteredData) {
      setScannerFormData(enteredData);
      writeSession('eatgood_scanner_form', enteredData);
    }
    navigateTo('assessment', { productId: assessmentData.product_id });
  };

  const handleEditCustomData = () => {
    setScannerMode('manual');
    navigateTo('scanner');
  };

  const handleUpdateCustomAssessment = (updatedAssessment, updatedForm = null) => {
    setCustomAssessment(updatedAssessment);
    writeSession('eatgood_custom_assessment', updatedAssessment);

    if (updatedForm) {
      setScannerFormData(prev => {
        const next = { ...prev, ...updatedForm };
        writeSession('eatgood_scanner_form', next);
        return next;
      });
    }
  };

  const handleCompareProduct = (productId) => {
    let newIds = compareIds;
    if (!compareIds.includes(productId)) {
      newIds = [productId, ...compareIds.slice(0, 3)];
      setCompareIds(newIds);
      writeSession('eatgood_compare_ids', newIds);
    }
    navigateTo('compare', { ids: newIds });
  };

  const handleSaveProfile = (newProfile) => {
    const profile = { ...DEFAULT_PROFILE, ...newProfile };
    setActiveProfile(profile);
    if (!saveProfile(profile)) {
      window.alert('Your browser blocked saving your profile, so it will be forgotten when you close this tab. Allow site data for this site to keep it.');
    }
  };

  const handleCompleteOnboarding = (newProfile) => {
    handleSaveProfile(newProfile);
    completeOnboarding();
    setIsOnboardingOpen(false);
  };

  return (
    <div className="app-container">
      <Navbar
        activePage={activePage}
        setActivePage={(page) => navigateTo(page)}
        activeProfile={activeProfile}
        onOpenProfile={() => setIsProfileModalOpen(true)}
      />

      <DemoDataBanner onOpenAudit={() => navigateTo('audit')} />

      <main className="main-content">
        {activePage === 'landing' && (
          <LandingPage
            setActivePage={(page) => navigateTo(page)}
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
            formData={scannerFormData}
            setFormData={(updater) => {
              setScannerFormData(prev => {
                const next = typeof updater === 'function' ? updater(prev) : updater;
                writeSession('eatgood_scanner_form', next);
                return next;
              });
            }}
            mode={scannerMode}
            setMode={setScannerMode}
          />
        )}

        {activePage === 'assessment' && (
          <ProductAssessment
            productId={selectedProductId}
            assessmentData={customAssessment}
            onBack={() => navigateTo('catalogue')}
            onSelectProduct={handleSelectProduct}
            activeProfile={activeProfile}
            onEditCustomData={handleEditCustomData}
            onUpdateAssessment={handleUpdateCustomAssessment}
          />
        )}

        {activePage === 'compare' && (
          <ProductComparison
            initialProductIds={compareIds}
            onSelectProduct={handleSelectProduct}
            activeProfile={activeProfile}
          />
        )}

        {(activePage === 'profile' || activePage === 'dashboard') && (
          <Dashboard
            setActivePage={(page) => navigateTo(page)}
            onSelectProduct={handleSelectProduct}
            onOpenCustomAssessment={(assessment) => handleAssessmentGenerated(assessment)}
            activeProfile={activeProfile}
            onOpenProfile={() => setIsProfileModalOpen(true)}
            onRetakeOnboarding={() => setIsOnboardingOpen(true)}
          />
        )}

        {activePage === 'audit' && (
          <DataAuditPage />
        )}
      </main>

      <Footer setActivePage={(page) => navigateTo(page)} />

      <ProfileModal
        isOpen={isProfileModalOpen}
        onClose={() => setIsProfileModalOpen(false)}
        activeProfile={activeProfile}
        onSaveProfile={handleSaveProfile}
      />

      <OnboardingModal
        isOpen={isOnboardingOpen}
        activeProfile={activeProfile}
        onComplete={handleCompleteOnboarding}
      />
    </div>
  );
}
