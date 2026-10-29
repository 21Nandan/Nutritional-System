import React, { useState } from 'react';
import { apiFetch } from '../api';
import {
  Camera, FileText, AlertTriangle,
  Sparkles, ArrowRight, RefreshCw, Barcode, Search,
  PlusCircle, ShieldCheck
} from 'lucide-react';
import BarcodeCameraScanner from '../components/BarcodeCameraScanner';
import OpenFoodFactsSearch from '../components/OpenFoodFactsSearch';
import ProductContributionModal from '../components/ProductContributionModal';

export default function LabelScanner({ 
  onAssessmentGenerated, 
  onSelectProduct,
  formData: propFormData,
  setFormData: propSetFormData,
  mode: propMode,
  setMode: propSetMode
}) {
  const [internalMode, setInternalMode] = useState('search'); // 'search', 'barcode', 'manual'
  const mode = propMode !== undefined ? propMode : internalMode;
  const setMode = propSetMode || setInternalMode;

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

  const [evaluating, setEvaluating] = useState(false);

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
      const data = await apiFetch(`/api/products/barcode/${encodeURIComponent(code)}`);
      setBarcodeFoundResult(data);
    } catch (err) {
      if (err.status === 404 && err.code === 'OFF_PRODUCT_NOT_FOUND') {
        setBarcodeNotFoundInfo({
          barcode: code,
          format: err.detail?.barcode_format || 'EAN / UPC',
          message: err.message
        });
      } else {
        setBarcodeError(err.message);
      }
    } finally {
      setBarcodeSearching(false);
    }
  };

  const handleBarcodeSearch = (e) => {
    if (e && e.preventDefault) e.preventDefault();
    handleBarcodeLookup(barcodeInput);
  };

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
      window.alert('Please enter a product name.');
      return;
    }

    setEvaluating(true);

    const parseNum = (v) => (v === '' || v === null || isNaN(Number(v))) ? null : Number(v);

    const payload = {
      product_name: formData.product_name,
      brand: formData.brand,
      category: formData.category,
      serving_size: parseNum(formData.serving_size),
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
      const assessmentData = await apiFetch('/api/products/assess', { method: 'POST', body: payload });
      onAssessmentGenerated(assessmentData, formData);
    } catch (err) {
      window.alert(err.message);
    } finally {
      setEvaluating(false);
    }
  };

  return (
    <div className="label-scanner">
      <div style={{ marginBottom: 28, textAlign: 'center', maxWidth: 700, margin: '0 auto 28px' }}>
        <h1 style={{ fontSize: 'clamp(1.6rem, 4vw, 2.2rem)', color: 'var(--color-primary)', marginBottom: 8 }}>
          Find a Product
        </h1>
        <p style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem' }}>
          Search a world database of packaged foods, scan or type a barcode, or enter the nutrition facts yourself.
        </p>
      </div>

      {/* Mode Switcher */}
      <div className="scanner-modes" style={{ display: 'flex', justifyContent: 'center', flexWrap: 'wrap', gap: 10, marginBottom: 24 }}>
        <button
          className={`btn-secondary ${mode === 'search' ? 'active' : ''}`}
          onClick={() => setMode('search')}
          aria-pressed={mode === 'search'}
          style={{
            background: mode === 'search' ? 'var(--color-primary)' : '#fff',
            color: mode === 'search' ? '#fff' : 'inherit',
            minHeight: 44
          }}
        >
          <Search size={16} />
          <span>Search Products</span>
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

      {mode === 'search' && <OpenFoodFactsSearch onSelectProduct={onSelectProduct} />}

      {/* Barcode Lookup & Camera Scanner */}
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
                {barcodeNotFoundInfo.message} You can contribute it, enter the values from the pack yourself, or search by product name.
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
                    setMode('manual');
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
                  <FileText size={15} />
                  <span>Enter Values Manually</span>
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
                  onClick={() => setMode('search')}
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
                  onClick={() => setMode('search')}
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
                  <span>Can&apos;t find the barcode? Search by product name or brand</span>
                </button>
              </div>

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

      {/* Editable Confirmation Form */}
      {mode === 'manual' && (
      <form onSubmit={handleGenerateAssessment} className="card" style={{ maxWidth: 840, margin: '0 auto' }}>
        <div style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: 16, marginBottom: 20 }}>
          <h2 style={{ fontSize: 'clamp(1.2rem, 3vw, 1.4rem)', color: 'var(--color-primary)' }}>
            Editable Nutrition & Ingredient Confirmation
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
            Check every value against the pack before continuing. Nothing is scored until you submit this form.
          </p>
        </div>

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
              </label>
              <input
                type="number"
                step="any"
                placeholder="e.g. 520"
                value={formData.energy_kcal}
                onChange={e => setFormData({ ...formData, energy_kcal: e.target.value })}
                style={inputStyle}
              />
            </div>

            <div>
              <label style={labelStyle}>
                <span>Carbs (g)</span>
              </label>
              <input
                type="number"
                step="any"
                placeholder="e.g. 64.0"
                value={formData.carbohydrates_g}
                onChange={e => setFormData({ ...formData, carbohydrates_g: e.target.value })}
                style={inputStyle}
              />
            </div>

            <div>
              <label style={labelStyle}>
                <span>Total Sugars (g)</span>
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
              </label>
              <input
                type="number"
                step="any"
                placeholder="e.g. 650"
                value={formData.sodium_mg}
                onChange={e => setFormData({ ...formData, sodium_mg: e.target.value })}
                style={inputStyle}
              />
            </div>

            <div>
              <label style={labelStyle}>
                <span>Protein (g)</span>
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
              </label>
              <input
                type="number"
                step="any"
                placeholder="e.g. 3.5"
                value={formData.dietary_fibre_g}
                onChange={e => setFormData({ ...formData, dietary_fibre_g: e.target.value })}
                style={inputStyle}
              />
            </div>
          </div>
        </div>

        {/* Ingredients & Allergens */}
        <div style={{ marginBottom: 18 }}>
          <label style={{ display: 'flex', alignItems: 'center', fontSize: '0.82rem', fontWeight: 700, marginBottom: 4 }}>
            <span>Ingredients List</span>
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
      )}
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
