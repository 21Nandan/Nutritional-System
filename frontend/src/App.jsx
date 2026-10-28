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

const PAGE_TITLES = {
  landing: 'EATGOOD — AI-Powered Personalized Food Safety & Nutrition Assessment',
  catalogue: 'EATGOOD — Indian Packaged Food Catalogue',
  scanner: 'EATGOOD — Food Label Scanner & OCR Extraction',
  assessment: 'EATGOOD — Product Nutritional Assessment',
  compare: 'EATGOOD — Product Comparison Matrix',
  profile: 'EATGOOD — User Profile & History',
  dashboard: 'EATGOOD — User Dashboard',
  audit: 'EATGOOD — Data Quality & Integrity Audit'
};

// URL Route Parser (supports real URL paths, search params, and hash fallback)
const getRouteFromLocation = () => {
  const path = window.location.pathname.toLowerCase().replace(/^\/+|\/+$/g, '');
  const searchParams = new URLSearchParams(window.location.search);
  const hash = window.location.hash.toLowerCase().replace(/^#\/?/, '');

  // 1. Direct product path: /product/IND_PKG_001 or /assessment/IND_PKG_001
  const productMatch = path.match(/^(?:product|assessment)\/(.+)$/);
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
    const hashProductMatch = cleanHash.match(/^(?:product|assessment)\/(.+)$/);
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
  const [customAssessment, setCustomAssessment] = useState(() => {
    try {
      const saved = sessionStorage.getItem('eatgood_custom_assessment');
      return saved ? JSON.parse(saved) : null;
    } catch (e) {
      return null;
    }
  });

  const [compareIds, setCompareIds] = useState(() => {
    if (initialRoute.compareIds && initialRoute.compareIds.length >= 2) {
      return initialRoute.compareIds;
    }
    try {
      const saved = sessionStorage.getItem('eatgood_compare_ids');
      return saved ? JSON.parse(saved) : ['IND_PKG_001', 'IND_PKG_002'];
    } catch (e) {
      return ['IND_PKG_001', 'IND_PKG_002'];
    }
  });

  const getClientId = () => {
    try {
      let cid = localStorage.getItem('eatgood_client_id');
      if (!cid) {
        cid = 'usr_' + Math.random().toString(36).substring(2, 9) + '_' + Date.now().toString(36);
        localStorage.setItem('eatgood_client_id', cid);
      }
      return cid;
    } catch (e) {
      return 'USR_DEFAULT';
    }
  };

  const [activeProfile, setActiveProfile] = useState(() => {
    try {
      const saved = localStorage.getItem('eatgood_user_profile');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed && typeof parsed === 'object') {
          return {
            user_id: parsed.user_id || 'USR_DEFAULT',
            name: parsed.name || 'Guest User',
            goal: parsed.goal || 'Balanced Choices',
            dietary_preference: parsed.dietary_preference || 'No preference',
            allergens_to_avoid: parsed.allergens_to_avoid || '',
            age_group: parsed.age_group || '18-24',
            activity_level: parsed.activity_level || 'Moderately active'
          };
        }
      }
    } catch (e) {}
    return {
      user_id: 'USR_DEFAULT',
      name: 'Guest User',
      goal: 'Balanced Choices',
      dietary_preference: 'No preference',
      allergens_to_avoid: '',
      age_group: '18-24',
      activity_level: 'Moderately active'
    };
  });
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);

  // Initialize persistent device client ID eagerly
  useEffect(() => {
    getClientId();
  }, []);

  // First-time visit onboarding & terms acceptance state
  const [isOnboardingOpen, setIsOnboardingOpen] = useState(() => {
    try {
      const completed = localStorage.getItem('eatgood_onboarding_completed');
      return completed !== 'true';
    } catch (e) {
      return true;
    }
  });

  // Persistent scanner form data (preserved across refreshes)
  const [scannerFormData, setScannerFormData] = useState(() => {
    try {
      const saved = sessionStorage.getItem('eatgood_scanner_form');
      if (saved) return JSON.parse(saved);
    } catch (e) {}
    return {
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
    };
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
      try {
        sessionStorage.setItem('eatgood_compare_ids', JSON.stringify(params.compareIds));
      } catch (e) {}
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [compareIds, selectedProductId]);

  // Initial load and popstate event listener for browser Back/Forward
  useEffect(() => {
    const route = getRouteFromLocation();
    navigateTo(route.page, { productId: route.productId, compareIds: route.compareIds }, true);

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

  // Fetch active profile on load with client identity
  useEffect(() => {
    const cid = getClientId();
    fetch(`/api/profile?user_id=${encodeURIComponent(cid)}`, {
      headers: { 'X-User-Id': cid }
    })
      .then(res => res.json())
      .then(data => {
        if (data && data.user_id) {
          const localSaved = localStorage.getItem('eatgood_user_profile');
          if (localSaved) {
            try {
              const parsed = JSON.parse(localSaved);
              if (parsed && (parsed.goal || parsed.dietary_preference || parsed.allergens_to_avoid)) {
                // If local storage has user preferences, keep them as primary and sync to backend
                setActiveProfile(parsed);
                if (data.user_id === 'USR_DEFAULT' && parsed.user_id !== 'USR_DEFAULT') {
                  handleSaveProfile(parsed);
                }
                return;
              }
            } catch (e) {}
          }
          setActiveProfile(data);
          try {
            localStorage.setItem('eatgood_user_profile', JSON.stringify(data));
          } catch (e) {}
        }
      })
      .catch(err => {
        console.error('Error fetching profile:', err);
      });
  }, []);

  const handleSelectProduct = (productId) => {
    setCustomAssessment(null);
    try {
      sessionStorage.removeItem('eatgood_custom_assessment');
    } catch (e) {}
    navigateTo('assessment', { productId });
  };

  const handleAssessmentGenerated = (assessmentData, enteredData = null) => {
    setCustomAssessment(assessmentData);
    try {
      sessionStorage.setItem('eatgood_custom_assessment', JSON.stringify(assessmentData));
    } catch (e) {}

    if (enteredData) {
      setScannerFormData(enteredData);
      try {
        sessionStorage.setItem('eatgood_scanner_form', JSON.stringify(enteredData));
      } catch (e) {}
    }
    navigateTo('assessment', { productId: assessmentData.product_id });
  };

  const handleEditCustomData = () => {
    setScannerMode('manual');
    navigateTo('scanner');
  };

  const handleUpdateCustomAssessment = (updatedAssessment, updatedForm = null) => {
    setCustomAssessment(updatedAssessment);
    try {
      sessionStorage.setItem('eatgood_custom_assessment', JSON.stringify(updatedAssessment));
    } catch (e) {}

    if (updatedForm) {
      setScannerFormData(prev => {
        const next = { ...prev, ...updatedForm };
        try {
          sessionStorage.setItem('eatgood_scanner_form', JSON.stringify(next));
        } catch (e) {}
        return next;
      });
    }
  };

  const handleCompareProduct = (productId) => {
    let newIds = compareIds;
    if (!compareIds.includes(productId)) {
      newIds = [productId, ...compareIds.slice(0, 3)];
      setCompareIds(newIds);
      try {
        sessionStorage.setItem('eatgood_compare_ids', JSON.stringify(newIds));
      } catch (e) {}
    }
    navigateTo('compare', { ids: newIds });
  };

  const handleSaveProfile = (newProfile) => {
    const cid = getClientId();
    const profileToSave = { ...newProfile, user_id: cid };

    try {
      localStorage.setItem('eatgood_user_profile', JSON.stringify(profileToSave));
    } catch (e) {}
    setActiveProfile(profileToSave);

    fetch('/api/profile', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'X-User-Id': cid
      },
      body: JSON.stringify(profileToSave)
    })
      .then(res => res.json())
      .then(saved => {
        if (saved && saved.user_id) {
          setActiveProfile(saved);
          try {
            localStorage.setItem('eatgood_user_profile', JSON.stringify(saved));
          } catch (e) {}
        }
      })
      .catch(err => console.error(err));
  };

  const handleCompleteOnboarding = (newProfile) => {
    handleSaveProfile(newProfile);
    try {
      localStorage.setItem('eatgood_onboarding_completed', 'true');
      localStorage.setItem('eatgood_terms_accepted_at', new Date().toISOString());
    } catch (e) {}
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
                try {
                  sessionStorage.setItem('eatgood_scanner_form', JSON.stringify(next));
                } catch (e) {}
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
            activeProfile={activeProfile}
            onOpenProfile={() => setIsProfileModalOpen(true)}
            onRetakeOnboarding={() => setIsOnboardingOpen(true)}
          />
        )}

        {activePage === 'audit' && (
          <DataAuditPage
            onSelectProduct={handleSelectProduct}
          />
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
