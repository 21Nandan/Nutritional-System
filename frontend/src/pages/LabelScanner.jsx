import React, { useState, useEffect, useRef } from 'react';
import { 
  Upload, Camera, FileText, CheckCircle2, AlertTriangle, 
  HelpCircle, Sparkles, ArrowRight, RefreshCw, Barcode, Search,
  ChevronDown, ChevronUp, Info, Smartphone, ExternalLink,
  PlusCircle, Globe, ShieldCheck, Zap, Package, AlertCircle
} from 'lucide-react';
import BarcodeCameraScanner from '../components/BarcodeCameraScanner';
import ProductContributionModal from '../components/ProductContributionModal';

export default function LabelScanner({ 
  onAssessmentGenerated, 
  onSelectProduct,
  formData: propFormData,
  setFormData: propSetFormData,
  mode: propMode,
  setMode: propSetMode
}) {
  const [internalMode, setInternalMode] = useState('upload'); // 'upload', 'manual', 'barcode'
  const mode = propMode !== undefined ? propMode : internalMode;
  const setMode = propSetMode || setInternalMode;

  const [file, setFile] = useState(null);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrResult, setOcrResult] = useState(null);
  const [showRawText, setShowRawText] = useState(false);
  const [barcodeInput, setBarcodeInput] = useState('');
  const [barcodeError, setBarcodeError] = useState('');

  // Barcode Scanner & Layered Discovery State
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [barcodeSearching, setBarcodeSearching] = useState(false);
  const [barcodeLookupStep, setBarcodeLookupStep] = useState('');
  const [barcodeFoundResult, setBarcodeFoundResult] = useState(null);
  const [barcodeNotFoundInfo, setBarcodeNotFoundInfo] = useState(null);
  const [isContributionModalOpen, setIsContributionModalOpen] = useState(false);
  const [contributionBarcode, setContributionBarcode] = useState('');

  // Product Search by Name / Brand Fallback & Live Autocomplete State
  const [nameSearchQuery, setNameSearchQuery] = useState('');
  const [nameSearchResults, setNameSearchResults] = useState([]);
  const [nameSearchLoading, setNameSearchLoading] = useState(false);
  const [nameSearchError, setNameSearchError] = useState(null);
  const [showNameSearch, setShowNameSearch] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [activeSuggestionIdx, setActiveSuggestionIdx] = useState(-1);
  const searchContainerRef = useRef(null);
  const notFoundSearchContainerRef = useRef(null);
  const searchAbortControllerRef = useRef(null);

  // Editable confirmation form state (preserves inputs across views)
  const [internalFormData, setInternalFormData] = useState({
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
  const formData = propFormData !== undefined ? propFormData : internalFormData;
  const setFormData = propSetFormData || setInternalFormData;

  const [fieldStatuses, setFieldStatuses] = useState({});
  const [fieldNotes, setFieldNotes] = useState({});
  const [confidenceScores, setConfidenceScores] = useState({});
  const [suspiciousFlags, setSuspiciousFlags] = useState([]);
  const [evaluating, setEvaluating] = useState(false);

  const processUploadedFile = async (uploadedFile) => {
    if (!uploadedFile) return;
    setFile(uploadedFile);
    setOcrLoading(true);
    setOcrResult(null);

    const body = new FormData();
    body.append('file', uploadedFile);

    try {
      const res = await fetch('/api/analyze/ocr', {
        method: 'POST',
        body
      });
      const data = await res.json();
      setOcrResult(data);
      setOcrLoading(false);

      if (data.status === 'error') {
        alert(data.detail || data.message || 'OCR processing failed. You can enter details manually.');
        return;
      }

      // Prepopulate confirmation form with OCR results
      const vals = data.extracted_values || {};
      setFormData(prev => ({
        ...prev,
        product_name: prev.product_name || uploadedFile.name.replace(/\.[^/.]+$/, ''),
        serving_size: vals.serving_size != null ? String(vals.serving_size) : prev.serving_size || '100',
        serving_size_unit: vals.serving_size_unit || prev.serving_size_unit || 'g',
        measurement_basis: vals.measurement_basis || prev.measurement_basis || 'per 100g',
        energy_kcal: vals.energy_kcal != null ? String(vals.energy_kcal) : '',
        carbohydrates_g: vals.carbohydrates_g != null ? String(vals.carbohydrates_g) : '',
        sugars_g: vals.sugars_g != null ? String(vals.sugars_g) : '',
        added_sugars_g: vals.added_sugars_g != null ? String(vals.added_sugars_g) : '',
        protein_g: vals.protein_g != null ? String(vals.protein_g) : '',
        total_fat_g: vals.total_fat_g != null ? String(vals.total_fat_g) : '',
        saturated_fat_g: vals.saturated_fat_g != null ? String(vals.saturated_fat_g) : '',
        trans_fat_g: vals.trans_fat_g != null ? String(vals.trans_fat_g) : '',
        sodium_mg: vals.sodium_mg != null ? String(vals.sodium_mg) : '',
        dietary_fibre_g: vals.dietary_fibre_g != null ? String(vals.dietary_fibre_g) : '',
        ingredients: vals.ingredients || prev.ingredients
      }));

      setFieldStatuses(data.field_statuses || {});
      setFieldNotes(data.field_notes || {});
      setConfidenceScores(data.confidence_scores || {});
      setSuspiciousFlags(data.suspicious_flags || []);
    } catch (err) {
      console.error(err);
      setOcrLoading(false);
      alert('OCR network request failed. You can proceed with manual entry below.');
    }
  };

  const handleFileUpload = (e) => {
    processUploadedFile(e.target.files[0]);
  };

  const handleBarcodeLookup = async (codeToLookup) => {
    const code = String(codeToLookup !== undefined ? codeToLookup : barcodeInput).trim();
    if (!code) {
      setBarcodeError('Please enter a barcode number.');
      return;
    }
    setBarcodeError('');
    setBarcodeSearching(true);
    setBarcodeLookupStep('Querying local catalogue & Open Food Facts...');
    setBarcodeFoundResult(null);
    setBarcodeNotFoundInfo(null);
    setIsCameraActive(false);

    try {
      const res = await fetch(`/api/products/barcode/${encodeURIComponent(code)}`);
      const data = await res.json();
      setBarcodeSearching(false);

      if (res.ok && data.status === 'found') {
        setBarcodeFoundResult(data);
      } else if (res.status === 404) {
        setBarcodeNotFoundInfo({
          barcode: code,
          format: data.detail?.barcode_format || 'EAN / UPC',
          message: data.detail?.message || `Barcode ${code} was not found in the local catalogue or Open Food Facts.`
        });
      } else {
        const errorMsg = data?.detail?.message || (typeof data?.detail === 'string' ? data.detail : null) || 'Unable to complete barcode lookup. Please check connection or enter nutrition details manually.';
        setBarcodeError(errorMsg);
      }
    } catch (err) {
      console.error(err);
      setBarcodeSearching(false);
      setBarcodeError('Network error connecting to barcode service. Please check your connection.');
    }
  };

  const handleBarcodeSearch = (e) => {
    if (e && e.preventDefault) e.preventDefault();
    handleBarcodeLookup(barcodeInput);
  };

  // Live autocomplete search effect with debouncing (280ms)
  useEffect(() => {
    const query = nameSearchQuery.trim();
    if (query.length < 2) {
      setNameSearchResults([]);
      setShowSuggestions(false);
      setNameSearchLoading(false);
      setNameSearchError(null);
      return;
    }

    setNameSearchLoading(true);
    setNameSearchError(null);

    const timer = setTimeout(async () => {
      if (searchAbortControllerRef.current) {
        searchAbortControllerRef.current.abort();
      }
      const controller = new AbortController();
      searchAbortControllerRef.current = controller;

      try {
        const res = await fetch(
          `/api/products/search?q=${encodeURIComponent(query)}&limit=8&include_external=true`,
          { signal: controller.signal }
        );
        if (!res.ok) throw new Error('Search failed');
        const data = await res.json();
        setNameSearchResults(data.products || []);
        setShowSuggestions(true);
        setActiveSuggestionIdx(-1);
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.error('Live search error:', err);
          setNameSearchError('Could not fetch suggestions. Please check connection.');
        }
      } finally {
        setNameSearchLoading(false);
      }
    }, 280);

    return () => {
      clearTimeout(timer);
    };
  }, [nameSearchQuery]);

  // Click outside to close suggestions dropdown
  useEffect(() => {
    const handleClickOutside = (e) => {
      const inMain = searchContainerRef.current && searchContainerRef.current.contains(e.target);
      const inNotFound = notFoundSearchContainerRef.current && notFoundSearchContainerRef.current.contains(e.target);
      if (!inMain && !inNotFound) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleNameSearch = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    const query = nameSearchQuery.trim();
    if (!query) return;

    setNameSearchLoading(true);
    setNameSearchError(null);
    try {
      const res = await fetch(`/api/products/search?q=${encodeURIComponent(query)}&limit=12&include_external=true`);
      const data = await res.json();
      setNameSearchResults(data.products || []);
      setShowSuggestions(true);
      setActiveSuggestionIdx(-1);
    } catch (err) {
      console.error('Name search failed:', err);
      setNameSearchError('Search failed. Please try again.');
    } finally {
      setNameSearchLoading(false);
    }
  };

  const handleSearchKeyDown = (e) => {
    if (!showSuggestions || nameSearchResults.length === 0) {
      if (e.key === 'Enter') {
        handleNameSearch(e);
      }
      return;
    }

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveSuggestionIdx(prev => (prev < nameSearchResults.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveSuggestionIdx(prev => (prev > 0 ? prev - 1 : nameSearchResults.length - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (activeSuggestionIdx >= 0 && activeSuggestionIdx < nameSearchResults.length) {
        handleSelectSearchResult(nameSearchResults[activeSuggestionIdx]);
      } else {
        handleNameSearch(e);
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      setShowSuggestions(false);
      setActiveSuggestionIdx(-1);
    }
  };

  const handleSelectSearchResult = (prod) => {
    if (!prod) return;
    setShowSuggestions(false);
    setActiveSuggestionIdx(-1);

    // Prepopulate confirmation form data with verified fields
    setFormData(prev => ({
      ...prev,
      product_name: prod.product_name || prev.product_name || '',
      brand: prod.brand || prev.brand || '',
      category: prod.category || prev.category || 'Other',
      serving_size: prod.serving_size != null ? String(prod.serving_size) : (prev.serving_size || '100'),
      serving_size_unit: prod.serving_size_unit || prev.serving_size_unit || 'g',
      measurement_basis: 'per 100g',
      energy_kcal: prod.energy_kcal != null ? String(prod.energy_kcal) : (prev.energy_kcal || ''),
      carbohydrates_g: prod.carbohydrates_g != null ? String(prod.carbohydrates_g) : (prev.carbohydrates_g || ''),
      sugars_g: prod.sugars_g != null ? String(prod.sugars_g) : (prev.sugars_g || ''),
      added_sugars_g: prod.added_sugars_g != null ? String(prod.added_sugars_g) : (prev.added_sugars_g || ''),
      protein_g: prod.protein_g != null ? String(prod.protein_g) : (prev.protein_g || ''),
      total_fat_g: prod.total_fat_g != null ? String(prod.total_fat_g) : (prev.total_fat_g || ''),
      saturated_fat_g: prod.saturated_fat_g != null ? String(prod.saturated_fat_g) : (prev.saturated_fat_g || ''),
      trans_fat_g: prod.trans_fat_g != null ? String(prod.trans_fat_g) : (prev.trans_fat_g || ''),
      sodium_mg: prod.sodium_mg != null ? String(prod.sodium_mg) : (prev.sodium_mg || ''),
      dietary_fibre_g: prod.dietary_fibre_g != null ? String(prod.dietary_fibre_g) : (prev.dietary_fibre_g || ''),
      ingredients: prod.ingredients || prev.ingredients || ''
    }));

    if (prod.is_local && prod.product_id) {
      // Local catalogue item: view full assessment directly
      onSelectProduct(prod.product_id);
    } else if (prod.barcode) {
      // Open Food Facts product with barcode: trigger barcode lookup to fetch assessment & display result
      setBarcodeInput(prod.barcode);
      handleBarcodeLookup(prod.barcode);
    } else {
      // No barcode: open confirmation form in manual mode for user review
      setMode('manual');
    }
  };

  const renderNameSearchBox = (containerRef) => (
    <div ref={containerRef} style={{ position: 'relative', width: '100%', maxWidth: 500, margin: '12px auto 0' }}>
      <form onSubmit={handleNameSearch} style={{ display: 'flex', gap: 8 }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <input
            type="text"
            placeholder="Search by product name or brand (e.g. Lay's, Maggi, Amul)..."
            value={nameSearchQuery}
            onChange={(e) => {
              setNameSearchQuery(e.target.value);
              if (!showSuggestions && e.target.value.trim().length >= 2) {
                setShowSuggestions(true);
              }
            }}
            onFocus={() => {
              if (nameSearchResults.length > 0 || nameSearchQuery.trim().length >= 2) {
                setShowSuggestions(true);
              }
            }}
            onKeyDown={handleSearchKeyDown}
            style={{
              width: '100%',
              padding: '10px 36px 10px 34px',
              borderRadius: 8,
              border: '1px solid var(--color-border)',
              fontSize: '0.88rem',
              boxSizing: 'border-box'
            }}
          />
          <Search
            size={15}
            color="var(--color-text-muted)"
            style={{ position: 'absolute', left: 11, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }}
          />
          {nameSearchLoading && (
            <div style={{ position: 'absolute', right: 11, top: '50%', transform: 'translateY(-50%)', display: 'flex', alignItems: 'center' }}>
              <RefreshCw size={14} className="spin" color="var(--color-primary)" style={{ animation: 'spin 1s linear infinite' }} />
            </div>
          )}
        </div>
        <button
          type="submit"
          className="btn-primary"
          disabled={nameSearchLoading}
          style={{ padding: '9px 18px', fontSize: '0.85rem', flexShrink: 0 }}
        >
          {nameSearchLoading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {/* Live Suggestions Dropdown */}
      {showSuggestions && nameSearchQuery.trim().length >= 2 && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + 6px)',
            left: 0,
            right: 0,
            background: '#ffffff',
            borderRadius: 8,
            border: '1px solid var(--color-border)',
            boxShadow: '0 8px 24px rgba(0,0,0,0.12)',
            maxHeight: 320,
            overflowY: 'auto',
            zIndex: 1000,
            textAlign: 'left'
          }}
        >
          {nameSearchLoading && nameSearchResults.length === 0 && (
            <div style={{ padding: '14px', textAlign: 'center', fontSize: '0.82rem', color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
              <RefreshCw size={14} className="spin" color="var(--color-primary)" style={{ animation: 'spin 1s linear infinite' }} />
              <span>Searching local catalogue & Open Food Facts...</span>
            </div>
          )}

          {nameSearchError && (
            <div style={{ padding: '10px 12px', fontSize: '0.8rem', color: '#c62828', background: '#ffebee', display: 'flex', alignItems: 'center', gap: 6 }}>
              <AlertCircle size={14} />
              <span>{nameSearchError}</span>
            </div>
          )}

          {nameSearchResults.length > 0 && (
            <>
              <div style={{ padding: '6px 12px', background: '#f8f9fa', borderBottom: '1px solid #eee', fontSize: '0.72rem', color: 'var(--color-text-muted)', fontWeight: 600, display: 'flex', justifyContent: 'space-between' }}>
                <span>SUGGESTIONS</span>
                <span>↑ ↓ to navigate • Enter to select</span>
              </div>
              {nameSearchResults.map((prod, idx) => {
                const isSelected = idx === activeSuggestionIdx;
                const hasImg = prod.image_url && typeof prod.image_url === 'string' && prod.image_url.trim() !== '' && prod.image_url !== 'None';
                return (
                  <div
                    key={prod.product_id || prod.barcode || idx}
                    onClick={() => handleSelectSearchResult(prod)}
                    onMouseEnter={() => setActiveSuggestionIdx(idx)}
                    style={{
                      padding: '8px 12px',
                      borderBottom: idx === nameSearchResults.length - 1 ? 'none' : '1px solid #f2f2f2',
                      cursor: 'pointer',
                      background: isSelected ? '#f4f6fd' : '#ffffff',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      transition: 'background 0.1s ease'
                    }}
                  >
                    <div style={{ width: 38, height: 38, borderRadius: 6, background: '#fafafa', border: '1px solid var(--color-border)', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
                      {hasImg ? (
                        <img
                          src={prod.image_url}
                          alt=""
                          style={{ width: '100%', height: '100%', objectFit: 'contain' }}
                          onError={e => { e.target.style.display = 'none'; }}
                        />
                      ) : (
                        <Package size={18} color="var(--color-text-muted)" />
                      )}
                    </div>

                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                        <strong style={{ fontSize: '0.85rem', color: isSelected ? 'var(--color-primary)' : 'var(--color-text-main, #222)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '75%' }}>
                          {prod.product_name}
                        </strong>
                        {prod.is_local ? (
                          <span style={{ fontSize: '0.66rem', padding: '1px 5px', borderRadius: 4, background: '#e8f5e9', color: '#2e7d32', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 3 }}>
                            <CheckCircle2 size={10} /> Local
                          </span>
                        ) : (
                          <span style={{ fontSize: '0.66rem', padding: '1px 5px', borderRadius: 4, background: '#e3f2fd', color: '#1565c0', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 3 }}>
                            <Globe size={10} /> Open Food Facts
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: '0.74rem', color: 'var(--color-text-subtle, #666)', marginTop: 2, display: 'flex', alignItems: 'center', gap: 5 }}>
                        <span>{prod.brand || 'Brand'}</span>
                        <span>•</span>
                        <span>{prod.category || 'Food'}</span>
                        {prod.barcode && <span>• Barcode: {prod.barcode}</span>}
                      </div>

                      {prod.nutrition_summary && (prod.nutrition_summary.energy_kcal != null || prod.nutrition_summary.sugars_g != null) && (
                        <div style={{ display: 'flex', gap: 6, marginTop: 3 }}>
                          {prod.nutrition_summary.energy_kcal != null && (
                            <span style={{ fontSize: '0.66rem', padding: '1px 5px', borderRadius: 3, background: '#f5f5f5', color: '#555' }}>
                              {Math.round(Number(prod.nutrition_summary.energy_kcal))} kcal
                            </span>
                          )}
                          {prod.nutrition_summary.sugars_g != null && (
                            <span style={{ fontSize: '0.66rem', padding: '1px 5px', borderRadius: 3, background: '#f5f5f5', color: '#555' }}>
                              Sugar: {Number(prod.nutrition_summary.sugars_g).toFixed(1)}g
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                    <ArrowRight size={14} color={isSelected ? 'var(--color-primary)' : 'var(--color-text-muted)'} style={{ flexShrink: 0 }} />
                  </div>
                );
              })}
            </>
          )}

          {!nameSearchLoading && nameSearchResults.length === 0 && (
            <div style={{ padding: '14px', textAlign: 'center', fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
              No matching products found in local catalogue or Open Food Facts for "{nameSearchQuery}".
            </div>
          )}
        </div>
      )}
    </div>
  );

  const handleViewBarcodeAssessment = (foundResult) => {
    if (!foundResult) return;
    if (foundResult.source === 'local_database' && foundResult.product?.product_id) {
      onSelectProduct(foundResult.product.product_id);
    } else if (foundResult.assessment) {
      onAssessmentGenerated(foundResult.assessment, foundResult.product);
    }
  };

  const handleOpenContribution = (code) => {
    setContributionBarcode(code || barcodeInput || '');
    setIsContributionModalOpen(true);
  };

  const handleContributionSuccess = (productObj) => {
    handleBarcodeLookup(productObj.barcode);
  };

  const handleGenerateAssessment = async (e) => {
    e.preventDefault();
    if (!formData.product_name.trim()) {
      alert('Please enter a product name.');
      return;
    }

    setEvaluating(true);

    const parseNum = (v) => (v === '' || v === null || isNaN(Number(v))) ? null : Number(v);

    const payload = {
      product_name: formData.product_name,
      brand: formData.brand || 'Custom',
      category: formData.category,
      serving_size: parseNum(formData.serving_size) || 100,
      serving_size_unit: formData.serving_size_unit,
      measurement_basis: formData.measurement_basis,
      energy_kcal: parseNum(formData.energy_kcal),
      carbohydrates_g: parseNum(formData.carbohydrates_g),
      sugars_g: parseNum(formData.sugars_g),
      added_sugars_g: parseNum(formData.added_sugars_g),
      protein_g: parseNum(formData.protein_g),
      total_fat_g: parseNum(formData.total_fat_g),
      saturated_fat_g: parseNum(formData.saturated_fat_g),
      trans_fat_g: parseNum(formData.trans_fat_g),
      sodium_mg: parseNum(formData.sodium_mg),
      dietary_fibre_g: parseNum(formData.dietary_fibre_g),
      ingredients: formData.ingredients,
      allergens_declared: formData.allergens_declared,
      marketing_claims: formData.marketing_claims
    };

    try {
      const cid = localStorage.getItem('eatgood_client_id') || 'USR_DEFAULT';
      const res = await fetch(`/api/products/assess?user_id=${encodeURIComponent(cid)}`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-User-Id': cid
        },
        body: JSON.stringify(payload)
      });
      const assessmentData = await res.json();
      setEvaluating(false);
      onAssessmentGenerated(assessmentData, formData);
    } catch (err) {
      console.error(err);
      setEvaluating(false);
      alert('Failed to generate food assessment.');
    }
  };

  const renderFieldBadge = (fieldKey) => {
    const status = fieldStatuses[fieldKey];
    const note = fieldNotes[fieldKey];
    const conf = confidenceScores[fieldKey];

    if (status === 'extracted') {
      return (
        <span 
          style={{
            fontSize: '0.7rem',
            fontWeight: 700,
            color: '#2e7d32',
            background: '#e8f5e9',
            padding: '2px 6px',
            borderRadius: 4,
            marginLeft: 6
          }}
          title="Extracted from OCR packaging scan"
        >
          ✓ Extracted
        </span>
      );
    }
    if (status === 'needs_review') {
      return (
        <span 
          style={{
            fontSize: '0.7rem',
            fontWeight: 700,
            color: '#b73800',
            background: '#fff3e0',
            padding: '2px 6px',
            borderRadius: 4,
            marginLeft: 6
          }}
          title={note || 'Anomaly or repair flagged — verify against packaging'}
        >
          ⚠️ Review
        </span>
      );
    }
    if (ocrResult && status === 'not_found') {
      return (
        <span 
          style={{
            fontSize: '0.68rem',
            fontWeight: 500,
            color: '#84988d',
            background: '#f1f5ef',
            padding: '2px 6px',
            borderRadius: 4,
            marginLeft: 6
          }}
        >
          Manual
        </span>
      );
    }
    return null;
  };

  return (
    <div className="label-scanner">
      <div style={{ marginBottom: 28, textAlign: 'center', maxWidth: 700, margin: '0 auto 28px' }}>
        <h1 style={{ fontSize: 'clamp(1.6rem, 4vw, 2.2rem)', color: 'var(--color-primary)', marginBottom: 8 }}>
          Food Label Scanner & Analysis
        </h1>
        <p style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem' }}>
          Upload a food label photo for automated OCR extraction, snap a picture on mobile, look up a barcode, or manually enter nutrition facts.
        </p>
      </div>

      {/* Mode Switcher */}
      <div style={{ display: 'flex', justifyContent: 'center', flexWrap: 'wrap', gap: 10, marginBottom: 24 }}>
        <button
          className={`btn-secondary ${mode === 'upload' ? 'active' : ''}`}
          onClick={() => setMode('upload')}
          style={{ 
            background: mode === 'upload' ? 'var(--color-primary)' : '#fff', 
            color: mode === 'upload' ? '#fff' : 'inherit',
            minHeight: 44
          }}
        >
          <Camera size={16} />
          <span>Upload Label (OCR)</span>
        </button>
        <button
          className={`btn-secondary ${mode === 'barcode' ? 'active' : ''}`}
          onClick={() => setMode('barcode')}
          style={{ 
            background: mode === 'barcode' ? 'var(--color-primary)' : '#fff', 
            color: mode === 'barcode' ? '#fff' : 'inherit',
            minHeight: 44
          }}
        >
          <Barcode size={16} />
          <span>Barcode Lookup</span>
        </button>
        <button
          className={`btn-secondary ${mode === 'manual' ? 'active' : ''}`}
          onClick={() => setMode('manual')}
          style={{ 
            background: mode === 'manual' ? 'var(--color-primary)' : '#fff', 
            color: mode === 'manual' ? '#fff' : 'inherit',
            minHeight: 44
          }}
        >
          <FileText size={16} />
          <span>Manual Entry</span>
        </button>
      </div>

      {/* Mode 1: Barcode Lookup & Camera Scanner */}
      {mode === 'barcode' && (
        <div style={{ maxWidth: 680, margin: '0 auto 30px' }}>
          {/* Active Camera Viewfinder */}
          {isCameraActive && (
            <div style={{ marginBottom: 20 }}>
              <BarcodeCameraScanner
                isScanningActive={isCameraActive}
                onScan={(detectedCode) => handleBarcodeLookup(detectedCode)}
                onClose={() => setIsCameraActive(false)}
                onManualEntry={() => {
                  setIsCameraActive(false);
                  setTimeout(() => {
                    const el = document.getElementById('manual-barcode-input');
                    if (el) {
                      el.focus();
                      el.scrollIntoView({ behavior: 'smooth' });
                    }
                  }, 100);
                }}
              />
            </div>
          )}

          {/* Lookup In Progress State */}
          {barcodeSearching && (
            <div className="card" style={{ textAlign: 'center', padding: '36px 20px', marginBottom: 20 }}>
              <RefreshCw size={32} className="spin" color="var(--color-primary)" style={{ margin: '0 auto 12px', animation: 'spin 1s linear infinite' }} />
              <h3 style={{ fontSize: '1.15rem', color: 'var(--color-primary)', marginBottom: 6 }}>
                Searching Product Barcode...
              </h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
                {barcodeLookupStep || 'Checking local database and Open Food Facts...'}
              </p>
            </div>
          )}

          {/* State 1: Barcode Found Result Card */}
          {barcodeFoundResult && !barcodeSearching && (
            <div className="card" style={{ border: '2px solid #2e7d32', padding: 24, marginBottom: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12, marginBottom: 16 }}>
                <div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginBottom: 6 }}>
                    <span 
                      style={{
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        padding: '3px 8px',
                        borderRadius: 6,
                        background: barcodeFoundResult.source === 'local_database' ? '#e8f5e9' : 
                                    (barcodeFoundResult.source === 'user_contributed' ? '#fff3e0' : '#e1f5fe'),
                        color: barcodeFoundResult.source === 'local_database' ? '#2e7d32' : 
                               (barcodeFoundResult.source === 'user_contributed' ? '#e65100' : '#0288d1'),
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 4
                      }}
                    >
                      <ShieldCheck size={13} />
                      {barcodeFoundResult.source === 'local_database' ? 'Local EATGOOD Catalogue' :
                       barcodeFoundResult.source === 'user_contributed' ? 'User Contributed (Pending Review)' :
                       'Open Food Facts (v3 API)'}
                    </span>

                    <span style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)', background: '#f5f5f5', padding: '3px 8px', borderRadius: 4 }}>
                      {barcodeFoundResult.barcode_format || 'EAN-13'}: <strong>{barcodeFoundResult.barcode}</strong>
                    </span>
                  </div>

                  <h2 style={{ fontSize: '1.4rem', color: 'var(--color-primary)', marginBottom: 4 }}>
                    {barcodeFoundResult.product?.product_name || 'Packaged Food Product'}
                  </h2>

                  <div style={{ fontSize: '0.85rem', color: 'var(--color-text-subtle)' }}>
                    {barcodeFoundResult.product?.brand || 'Brand'} • {barcodeFoundResult.product?.category || 'Category'}
                  </div>
                </div>

                {/* Score Preview Pill */}
                <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                  <div style={{ textAlign: 'center', padding: '8px 14px', background: 'var(--color-surface-alt)', borderRadius: 10, border: '1px solid var(--color-border)' }}>
                    <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--color-text-subtle)', display: 'block', textTransform: 'uppercase' }}>
                      General Grade
                    </span>
                    <span className={`grade-badge grade-${barcodeFoundResult.assessment?.layer1_general?.grade || 'NA'}`} style={{ width: 32, height: 32, fontSize: '1.1rem', marginTop: 2 }}>
                      {barcodeFoundResult.assessment?.layer1_general?.grade || 'N/A'}
                    </span>
                  </div>

                  {barcodeFoundResult.assessment?.layer2_personalized?.personalized_score != null && (
                    <div style={{ textAlign: 'center', padding: '8px 14px', background: 'var(--color-surface-alt)', borderRadius: 10, border: '1px solid var(--color-border)' }}>
                      <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--color-text-subtle)', display: 'block', textTransform: 'uppercase' }}>
                        Goal Match
                      </span>
                      <span style={{ fontSize: '1.1rem', fontWeight: 800, color: '#2e7d32', marginTop: 2, display: 'block' }}>
                        {barcodeFoundResult.assessment.layer2_personalized.personalized_score}/100
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Product Thumbnail if available from OFF */}
              {barcodeFoundResult.product?.image_url && (
                <div style={{ marginBottom: 14, textAlign: 'center' }}>
                  <img 
                    src={barcodeFoundResult.product.image_url} 
                    alt={barcodeFoundResult.product.product_name} 
                    style={{ maxHeight: 140, objectFit: 'contain', borderRadius: 8, border: '1px solid var(--color-border)' }} 
                  />
                </div>
              )}

              {/* Open Food Facts Attribution Notice */}
              {barcodeFoundResult.openfoodfacts_attribution && (
                <div style={{
                  background: '#f8f9fa',
                  border: '1px solid #e9ecef',
                  borderRadius: 6,
                  padding: '8px 12px',
                  fontSize: '0.75rem',
                  color: 'var(--color-text-muted)',
                  marginBottom: 16
                }}>
                  {barcodeFoundResult.openfoodfacts_attribution}
                </div>
              )}

              {/* Primary Actions */}
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => handleViewBarcodeAssessment(barcodeFoundResult)}
                  style={{ flex: 1, minWidth: 200, padding: '12px 20px', minHeight: 46, fontSize: '0.95rem' }}
                >
                  <Sparkles size={16} />
                  <span>View Full Assessment & Alternatives</span>
                  <ArrowRight size={16} />
                </button>

                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setBarcodeFoundResult(null);
                    setBarcodeNotFoundInfo(null);
                    setBarcodeInput('');
                    setIsCameraActive(true);
                  }}
                  style={{ padding: '12px 18px', minHeight: 46, fontSize: '0.9rem' }}
                >
                  <RefreshCw size={15} />
                  <span>Scan Another Barcode</span>
                </button>
              </div>
            </div>
          )}

          {/* State 2: Barcode Not Found Card */}
          {barcodeNotFoundInfo && !barcodeSearching && (
            <div className="card" style={{ border: '2px solid #ff9800', padding: 24, marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                <div style={{
                  width: 44,
                  height: 44,
                  borderRadius: '50%',
                  background: '#fff3e0',
                  color: '#e65100',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0
                }}>
                  <AlertTriangle size={24} />
                </div>
                <div>
                  <h3 style={{ fontSize: '1.2rem', color: '#b73800', margin: 0 }}>
                    Product Not Found
                  </h3>
                  <div style={{ fontSize: '0.8rem', color: 'var(--color-text-subtle)', marginTop: 2 }}>
                    Barcode: <strong>{barcodeNotFoundInfo.barcode}</strong> ({barcodeNotFoundInfo.format})
                  </div>
                </div>
              </div>

              <p style={{ fontSize: '0.88rem', color: 'var(--color-text-muted)', lineHeight: 1.5, marginBottom: 18 }}>
                {barcodeNotFoundInfo.message} You can add it directly to your local database, scan its nutrition table photo via OCR, or search by product name.
              </p>

              {/* Action Buttons for Not Found State */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10 }}>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => handleOpenContribution(barcodeNotFoundInfo.barcode)}
                  style={{
                    padding: '10px 14px',
                    fontSize: '0.85rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 6
                  }}
                >
                  <PlusCircle size={15} />
                  <span>Contribute This Product</span>
                </button>

                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setFormData(prev => ({
                      ...prev,
                      product_name: prev.product_name || `Product ${barcodeNotFoundInfo.barcode}`
                    }));
                    setMode('upload');
                  }}
                  style={{
                    padding: '10px 14px',
                    fontSize: '0.85rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 6
                  }}
                >
                  <Camera size={15} />
                  <span>Scan Label via OCR</span>
                </button>

                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setBarcodeNotFoundInfo(null);
                    setBarcodeFoundResult(null);
                    setIsCameraActive(true);
                  }}
                  style={{
                    padding: '10px 14px',
                    fontSize: '0.85rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 6
                  }}
                >
                  <RefreshCw size={15} />
                  <span>Rescan / Try Another</span>
                </button>

                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setShowNameSearch(prev => !prev);
                  }}
                  style={{
                    padding: '10px 14px',
                    fontSize: '0.85rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 6
                  }}
                >
                  <Search size={15} />
                  <span>Search by Name</span>
                </button>
              </div>

              {/* Product Name Search Section in Not Found Card */}
              {showNameSearch && (
                <div style={{ marginTop: 18, paddingTop: 16, borderTop: '1px solid #ffe0b2' }}>
                  <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#b73800', display: 'block', marginBottom: 4 }}>
                    Search Local Indian Food Catalogue & Open Food Facts by Name:
                  </span>
                  {renderNameSearchBox(notFoundSearchContainerRef)}
                </div>
              )}
            </div>
          )}

          {/* Default State: Barcode Hub Controls */}
          {!barcodeFoundResult && !barcodeNotFoundInfo && !barcodeSearching && (
            <div className="card" style={{ textAlign: 'center', padding: '30px 20px' }}>
              <Barcode size={44} color="var(--color-primary)" style={{ margin: '0 auto 12px' }} />
              <h2 style={{ fontSize: '1.25rem', color: 'var(--color-primary)', marginBottom: 6 }}>
                Barcode Scanner & Product Discovery
              </h2>
              <p style={{ fontSize: '0.88rem', color: 'var(--color-text-muted)', maxWidth: 500, margin: '0 auto 20px', lineHeight: 1.4 }}>
                Scan retail food barcodes with your camera or enter the digits. Matches against our local Indian catalogue, then Open Food Facts.
              </p>

              {/* Main Camera Scan Button */}
              {!isCameraActive && (
                <div style={{ marginBottom: 24 }}>
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={() => {
                      setBarcodeError('');
                      setIsCameraActive(true);
                    }}
                    style={{
                      padding: '12px 28px',
                      fontSize: '1rem',
                      fontWeight: 700,
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 10,
                      minHeight: 48,
                      boxShadow: '0 4px 14px rgba(20, 56, 40, 0.25)'
                    }}
                  >
                    <Camera size={18} />
                    <span>Open Camera Barcode Scanner</span>
                  </button>
                </div>
              )}

              {/* Divider */}
              <div style={{ display: 'flex', alignItems: 'center', margin: '20px 0', color: 'var(--color-border)' }}>
                <div style={{ flex: 1, height: 1, background: 'var(--color-border)' }} />
                <span style={{ padding: '0 12px', fontSize: '0.78rem', color: 'var(--color-text-subtle)', textTransform: 'uppercase', fontWeight: 600 }}>
                  Or Enter Digits Manually
                </span>
                <div style={{ flex: 1, height: 1, background: 'var(--color-border)' }} />
              </div>

              {/* Manual Input Form */}
              <form onSubmit={handleBarcodeSearch} style={{ display: 'flex', flexWrap: 'wrap', gap: 8, maxWidth: 440, margin: '0 auto 16px' }}>
                <input
                  id="manual-barcode-input"
                  type="text"
                  placeholder="Enter 8-13 digit barcode..."
                  value={barcodeInput}
                  onChange={e => setBarcodeInput(e.target.value)}
                  style={{
                    flex: 1,
                    minWidth: 200,
                    padding: '10px 14px',
                    borderRadius: 8,
                    border: '1px solid var(--color-border)',
                    fontSize: '0.95rem',
                    minHeight: 44
                  }}
                />
                <button type="submit" className="btn-primary" style={{ padding: '10px 20px', minHeight: 44 }}>
                  Lookup
                </button>
              </form>

              {/* Search by Product Name Fallback Toggle */}
              <div style={{ marginTop: 16 }}>
                <button
                  type="button"
                  onClick={() => setShowNameSearch(prev => !prev)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--color-primary)',
                    fontSize: '0.82rem',
                    cursor: 'pointer',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 6,
                    fontWeight: 600
                  }}
                >
                  <Search size={14} />
                  <span>{showNameSearch ? 'Hide Name Search' : "Can't find barcode? Search by Product Name or Brand"}</span>
                </button>
              </div>

              {showNameSearch && (
                <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid var(--color-border)', maxWidth: 520, margin: '14px auto 0' }}>
                  {renderNameSearchBox(searchContainerRef)}
                </div>
              )}

              {barcodeError && (
                <div style={{ color: '#c62828', fontSize: '0.85rem', marginTop: 14, background: '#ffebee', padding: 10, borderRadius: 8 }}>
                  {barcodeError}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Product Contribution Modal */}
      <ProductContributionModal
        isOpen={isContributionModalOpen}
        onClose={() => setIsContributionModalOpen(false)}
        initialBarcode={contributionBarcode}
        onSuccessAssessment={handleContributionSuccess}
      />

      {/* Mode 2: Label Image Upload */}
      {mode === 'upload' && (
        <div className="card" style={{ maxWidth: 740, margin: '0 auto 30px' }}>
          <div style={{
            border: '2px dashed var(--color-border)',
            borderRadius: 12,
            padding: '30px 16px',
            textAlign: 'center',
            background: 'var(--color-surface-alt)',
            position: 'relative'
          }}>
            <Upload size={36} color="var(--color-accent)" style={{ margin: '0 auto 12px' }} />
            <h3 style={{ fontSize: '1.15rem', color: 'var(--color-primary)', marginBottom: 6 }}>
              Select or Photograph Food Label
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginBottom: 18 }}>
              Supports PNG, JPEG, WebP photos of nutrition tables or ingredient panels.
            </p>

            {/* Action Buttons for Mobile & Desktop */}
            <div style={{ display: 'flex', justifyContent: 'center', flexWrap: 'wrap', gap: 12 }}>
              <label 
                className="btn-primary" 
                style={{ 
                  cursor: 'pointer', 
                  display: 'inline-flex', 
                  alignItems: 'center', 
                  gap: 8, 
                  minHeight: 44,
                  padding: '10px 20px',
                  borderRadius: 8
                }}
              >
                <Upload size={16} />
                <span>Choose Image</span>
                <input
                  type="file"
                  accept="image/png, image/jpeg, image/webp"
                  onChange={handleFileUpload}
                  style={{ display: 'none' }}
                />
              </label>

              <label 
                className="btn-secondary" 
                style={{ 
                  cursor: 'pointer', 
                  display: 'inline-flex', 
                  alignItems: 'center', 
                  gap: 8, 
                  minHeight: 44,
                  padding: '10px 20px',
                  borderRadius: 8,
                  background: '#fff',
                  border: '1px solid var(--color-border)'
                }}
              >
                <Smartphone size={16} />
                <span>Take Photo (Camera)</span>
                <input
                  type="file"
                  accept="image/*"
                  capture="environment"
                  onChange={handleFileUpload}
                  style={{ display: 'none' }}
                />
              </label>
            </div>
          </div>

          {ocrLoading && (
            <div style={{ marginTop: 20, textAlign: 'center', padding: 20, background: '#eaf6e5', borderRadius: 8, color: 'var(--color-primary)' }}>
              <RefreshCw size={24} className="spin" style={{ margin: '0 auto 8px', animation: 'spin 1s linear infinite' }} />
              <div style={{ fontWeight: 700 }}>Extracting nutrition facts...</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Analyzing packaging image and validating nutritional figures</div>
            </div>
          )}

          {ocrResult && (
            <div style={{ marginTop: 20, background: '#f8faf7', border: '1px solid var(--color-border)', borderRadius: 8, padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8, marginBottom: 8 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ 
                    fontSize: '0.78rem', 
                    fontWeight: 700, 
                    color: ocrResult.status === 'success' ? '#2e7d32' : (ocrResult.status === 'partial' ? '#b73800' : '#c62828'),
                    display: 'flex',
                    alignItems: 'center',
                    gap: 4
                  }}>
                    {ocrResult.status === 'success' && <CheckCircle2 size={14} />}
                    {ocrResult.status === 'partial' && <AlertTriangle size={14} />}
                    {ocrResult.status.toUpperCase()}
                  </span>
                  {ocrResult.ocr_confidence > 0 && (
                    <span style={{ fontSize: '0.72rem', background: '#eaf6e5', color: 'var(--color-accent)', padding: '2px 8px', borderRadius: 4, fontWeight: 700 }}>
                      Text Extracted
                    </span>
                  )}
                </div>
                <span style={{ fontSize: '0.72rem', color: 'var(--color-text-subtle)' }}>
                  Local Text Extraction
                </span>
              </div>

              {ocrResult.message && (
                <div style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', marginBottom: 10 }}>
                  {ocrResult.message}
                </div>
              )}

              {/* Raw OCR Text Accordion */}
              {ocrResult.raw_text && (
                <div style={{ marginTop: 10 }}>
                  <button
                    type="button"
                    onClick={() => setShowRawText(prev => !prev)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      fontSize: '0.78rem',
                      fontWeight: 600,
                      color: 'var(--color-primary)',
                      padding: '6px 0',
                      cursor: 'pointer'
                    }}
                  >
                    <span>{showRawText ? 'Hide Raw OCR Text' : 'View Raw Extracted Text'}</span>
                    {showRawText ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>

                  {showRawText && (
                    <div style={{ 
                      maxHeight: 180, 
                      overflowY: 'auto', 
                      background: '#fff', 
                      border: '1px solid #e2e8e0', 
                      borderRadius: 6, 
                      padding: 10, 
                      fontSize: '0.75rem', 
                      fontFamily: 'monospace', 
                      whiteSpace: 'pre-wrap',
                      marginTop: 6
                    }}>
                      {ocrResult.raw_text}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Editable Confirmation Form */}
      <form onSubmit={handleGenerateAssessment} className="card" style={{ maxWidth: 840, margin: '0 auto' }}>
        <div style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: 16, marginBottom: 20 }}>
          <h2 style={{ fontSize: 'clamp(1.2rem, 3vw, 1.4rem)', color: 'var(--color-primary)' }}>
            Editable Nutrition & Ingredient Confirmation
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
            Review every field. EATGOOD refuses to silently turn uncertain OCR text into unverified nutrition scores.
          </p>
        </div>

        {/* Suspicious Anomaly Flags Notice */}
        {suspiciousFlags.length > 0 && (
          <div style={{ background: '#fff3e0', border: '1px solid #ffe0b2', borderRadius: 8, padding: 14, marginBottom: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#b73800', fontWeight: 700, fontSize: '0.85rem', marginBottom: 4 }}>
              <AlertTriangle size={16} />
              <span>Label Inconsistency Flags (Please Confirm):</span>
            </div>
            <ul style={{ margin: 0, paddingLeft: 20, fontSize: '0.8rem', color: '#8c2d00' }}>
              {suspiciousFlags.map((flag, i) => (
                <li key={i}>{flag}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Basic Product Info */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14, marginBottom: 18 }}>
          <div>
            <label style={{ display: 'flex', alignItems: 'center', fontSize: '0.82rem', fontWeight: 700, marginBottom: 4 }}>
              <span>Product Name *</span>
            </label>
            <input
              type="text"
              required
              placeholder="e.g. Marie Gold Biscuits"
              value={formData.product_name}
              onChange={e => setFormData({ ...formData, product_name: e.target.value })}
              style={inputStyle}
            />
          </div>

          <div>
            <label style={{ display: 'flex', alignItems: 'center', fontSize: '0.82rem', fontWeight: 700, marginBottom: 4 }}>
              <span>Brand</span>
            </label>
            <input
              type="text"
              placeholder="e.g. Britannia"
              value={formData.brand}
              onChange={e => setFormData({ ...formData, brand: e.target.value })}
              style={inputStyle}
            />
          </div>

          <div>
            <label style={{ display: 'flex', alignItems: 'center', fontSize: '0.82rem', fontWeight: 700, marginBottom: 4 }}>
              <span>Category *</span>
            </label>
            <select
              value={formData.category}
              onChange={e => setFormData({ ...formData, category: e.target.value })}
              style={inputStyle}
            >
              <option value="Snacks">Snacks</option>
              <option value="Breakfast Cereals">Breakfast Cereals</option>
              <option value="Packaged Beverages">Packaged Beverages</option>
              <option value="Biscuits & Bakery">Biscuits & Bakery</option>
              <option value="Chocolates & Sweets">Chocolates & Sweets</option>
              <option value="Instant Foods">Instant Foods</option>
              <option value="Dairy">Dairy</option>
              <option value="Condiments & Spreads">Condiments & Spreads</option>
            </select>
          </div>
        </div>

        {/* Serving Size and Measurement Basis */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 14, marginBottom: 18 }}>
          <div>
            <label style={{ display: 'flex', alignItems: 'center', fontSize: '0.82rem', fontWeight: 700, marginBottom: 4 }}>
              <span>Serving Size</span>
              {renderFieldBadge('serving_size')}
            </label>
            <input
              type="number"
              step="any"
              placeholder="100"
              value={formData.serving_size}
              onChange={e => setFormData({ ...formData, serving_size: e.target.value })}
              style={inputStyle}
            />
          </div>

          <div>
            <label style={{ display: 'flex', alignItems: 'center', fontSize: '0.82rem', fontWeight: 700, marginBottom: 4 }}>
              <span>Unit</span>
            </label>
            <select
              value={formData.serving_size_unit}
              onChange={e => setFormData({ ...formData, serving_size_unit: e.target.value })}
              style={inputStyle}
            >
              <option value="g">grams (g)</option>
              <option value="ml">milliliters (ml)</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'flex', alignItems: 'center', fontSize: '0.82rem', fontWeight: 700, marginBottom: 4 }}>
              <span>Measurement Basis</span>
            </label>
            <select
              value={formData.measurement_basis}
              onChange={e => setFormData({ ...formData, measurement_basis: e.target.value })}
              style={inputStyle}
            >
              <option value="per 100g">Per 100g (Standard)</option>
              <option value="per 100ml">Per 100ml (Beverages)</option>
              <option value="per serving">Per Serving</option>
            </select>
          </div>
        </div>

        {/* Nutrition Values Grid */}
        <div style={{
          background: 'var(--color-surface-alt)',
          padding: 16,
          borderRadius: 10,
          marginBottom: 18
        }}>
          <h4 style={{ fontSize: '0.9rem', marginBottom: 12, color: 'var(--color-primary)' }}>
            Nutritional Facts ({formData.measurement_basis})
          </h4>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 12 }}>
            <div>
              <label style={labelStyle}>
                <span>Calories (kcal)</span>
                {renderFieldBadge('energy_kcal')}
              </label>
              <input
                type="number"
                step="any"
                placeholder="e.g. 520"
                value={formData.energy_kcal}
                onChange={e => setFormData({ ...formData, energy_kcal: e.target.value })}
                style={inputStyle}
              />
              {fieldNotes['energy_kcal'] && (
                <div style={{ fontSize: '0.68rem', color: '#b73800', marginTop: 2 }}>{fieldNotes['energy_kcal']}</div>
              )}
            </div>

            <div>
              <label style={labelStyle}>
                <span>Carbs (g)</span>
                {renderFieldBadge('carbohydrates_g')}
              </label>
              <input
                type="number"
                step="any"
                placeholder="e.g. 64.0"
                value={formData.carbohydrates_g}
                onChange={e => setFormData({ ...formData, carbohydrates_g: e.target.value })}
                style={inputStyle}
              />
              {fieldNotes['carbohydrates_g'] && (
                <div style={{ fontSize: '0.68rem', color: '#b73800', marginTop: 2 }}>{fieldNotes['carbohydrates_g']}</div>
              )}
            </div>

            <div>
              <label style={labelStyle}>
                <span>Total Sugars (g)</span>
                {renderFieldBadge('sugars_g')}
              </label>
              <input
                type="number"
                step="any"
                placeholder="e.g. 4.5"
                value={formData.sugars_g}
                onChange={e => setFormData({ ...formData, sugars_g: e.target.value })}
                style={inputStyle}
              />
            </div>

            <div>
              <label style={labelStyle}>
                <span>Added Sugars (g)</span>
                {renderFieldBadge('added_sugars_g')}
              </label>
              <input
                type="number"
                step="any"
                placeholder="Optional"
                value={formData.added_sugars_g}
                onChange={e => setFormData({ ...formData, added_sugars_g: e.target.value })}
                style={inputStyle}
              />
            </div>

            <div>
              <label style={labelStyle}>
                <span>Sodium (mg)</span>
                {renderFieldBadge('sodium_mg')}
              </label>
              <input
                type="number"
                step="any"
                placeholder="e.g. 650"
                value={formData.sodium_mg}
                onChange={e => setFormData({ ...formData, sodium_mg: e.target.value })}
                style={inputStyle}
              />
              {fieldNotes['sodium_mg'] && (
                <div style={{ fontSize: '0.68rem', color: '#56695e', marginTop: 2 }}>{fieldNotes['sodium_mg']}</div>
              )}
            </div>

            <div>
              <label style={labelStyle}>
                <span>Protein (g)</span>
                {renderFieldBadge('protein_g')}
              </label>
              <input
                type="number"
                step="any"
                placeholder="e.g. 8.2"
                value={formData.protein_g}
                onChange={e => setFormData({ ...formData, protein_g: e.target.value })}
                style={inputStyle}
              />
            </div>

            <div>
              <label style={labelStyle}>
                <span>Total Fat (g)</span>
                {renderFieldBadge('total_fat_g')}
              </label>
              <input
                type="number"
                step="any"
                placeholder="e.g. 24.0"
                value={formData.total_fat_g}
                onChange={e => setFormData({ ...formData, total_fat_g: e.target.value })}
                style={inputStyle}
              />
            </div>

            <div>
              <label style={labelStyle}>
                <span>Saturated Fat (g)</span>
                {renderFieldBadge('saturated_fat_g')}
              </label>
              <input
                type="number"
                step="any"
                placeholder="e.g. 10.5"
                value={formData.saturated_fat_g}
                onChange={e => setFormData({ ...formData, saturated_fat_g: e.target.value })}
                style={inputStyle}
              />
            </div>

            <div>
              <label style={labelStyle}>
                <span>Dietary Fibre (g)</span>
                {renderFieldBadge('dietary_fibre_g')}
              </label>
              <input
                type="number"
                step="any"
                placeholder="e.g. 3.5"
                value={formData.dietary_fibre_g}
                onChange={e => setFormData({ ...formData, dietary_fibre_g: e.target.value })}
                style={inputStyle}
              />
              {fieldNotes['dietary_fibre_g'] && (
                <div style={{ fontSize: '0.68rem', color: '#b73800', marginTop: 2 }}>{fieldNotes['dietary_fibre_g']}</div>
              )}
            </div>
          </div>
        </div>

        {/* Ingredients & Allergens */}
        <div style={{ marginBottom: 18 }}>
          <label style={{ display: 'flex', alignItems: 'center', fontSize: '0.82rem', fontWeight: 700, marginBottom: 4 }}>
            <span>Ingredients List</span>
            {renderFieldBadge('ingredients')}
          </label>
          <textarea
            rows={3}
            placeholder="e.g. Potatoes, Edible Vegetable Oil (Palmolein), Salt, Red Chilli Powder, Amchur, INS 330..."
            value={formData.ingredients}
            onChange={e => setFormData({ ...formData, ingredients: e.target.value })}
            style={{ ...inputStyle, width: '100%', resize: 'vertical' }}
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14, marginBottom: 24 }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, marginBottom: 4 }}>
              Declared Allergens (Box Notice)
            </label>
            <input
              type="text"
              placeholder="e.g. Contains Milk, Soy"
              value={formData.allergens_declared}
              onChange={e => setFormData({ ...formData, allergens_declared: e.target.value })}
              style={inputStyle}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, marginBottom: 4 }}>
              Marketing Claims on Pack
            </label>
            <input
              type="text"
              placeholder="e.g. High Protein, Zero Sugar, Low Fat"
              value={formData.marketing_claims}
              onChange={e => setFormData({ ...formData, marketing_claims: e.target.value })}
              style={inputStyle}
            />
          </div>
        </div>

        {/* Submit Action */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
          <button
            type="submit"
            className="btn-accent"
            disabled={evaluating}
            style={{ padding: '12px 28px', fontSize: '1rem', minHeight: 48, width: '100%', maxWidth: 320 }}
          >
            {evaluating ? 'Analyzing...' : 'Generate Assessment'}
            <ArrowRight size={18} />
          </button>
        </div>
      </form>
    </div>
  );
}

const inputStyle = {
  width: '100%',
  padding: '10px 12px',
  borderRadius: 8,
  border: '1px solid var(--color-border)',
  fontSize: '0.9rem',
  background: '#fff',
  minHeight: 42,
  boxSizing: 'border-box'
};

const labelStyle = {
  display: 'flex',
  alignItems: 'center',
  fontSize: '0.75rem',
  fontWeight: 600,
  color: 'var(--color-text-muted)',
  marginBottom: 4
};
