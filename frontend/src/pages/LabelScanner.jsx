import React, { useState } from 'react';
import { 
  Upload, Camera, FileText, CheckCircle2, AlertTriangle, 
  HelpCircle, Sparkles, ArrowRight, RefreshCw, Barcode, Search 
} from 'lucide-react';

export default function LabelScanner({ onAssessmentGenerated, onSelectProduct }) {
  const [mode, setMode] = useState('upload'); // 'upload', 'manual', 'barcode'
  const [file, setFile] = useState(null);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrResult, setOcrResult] = useState(null);
  const [barcodeInput, setBarcodeInput] = useState('');
  const [barcodeError, setBarcodeError] = useState('');

  // Editable confirmation form state
  const [formData, setFormData] = useState({
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

  const [suspiciousFlags, setSuspiciousFlags] = useState([]);
  const [evaluating, setEvaluating] = useState(false);

  const handleFileUpload = async (e) => {
    const uploadedFile = e.target.files[0];
    if (!uploadedFile) return;
    setFile(uploadedFile);
    setOcrLoading(true);

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

      // Prepopulate confirmation form with OCR results
      const vals = data.extracted_values || {};
      setFormData(prev => ({
        ...prev,
        product_name: prev.product_name || uploadedFile.name.replace(/\.[^/.]+$/, ''),
        serving_size: vals.serving_size != null ? String(vals.serving_size) : '100',
        serving_size_unit: vals.serving_size_unit || 'g',
        measurement_basis: vals.measurement_basis || 'per 100g',
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

      setSuspiciousFlags(data.suspicious_flags || []);
    } catch (err) {
      console.error(err);
      setOcrLoading(false);
      alert('OCR extraction failed. You can proceed with manual entry below.');
    }
  };

  const handleBarcodeSearch = async (e) => {
    e.preventDefault();
    if (!barcodeInput.trim()) return;
    setBarcodeError('');
    try {
      const res = await fetch(`/api/products?query=${encodeURIComponent(barcodeInput.trim())}&limit=1`);
      const data = await res.json();
      if (data.products && data.products.length > 0) {
        onSelectProduct(data.products[0].product_id);
      } else {
        setBarcodeError(`No product found with barcode "${barcodeInput}". Try manual entry or label photo upload.`);
      }
    } catch (err) {
      setBarcodeError('Failed to search barcode database.');
    }
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
      const res = await fetch('/api/products/assess', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const assessmentData = await res.json();
      setEvaluating(false);
      onAssessmentGenerated(assessmentData);
    } catch (err) {
      console.error(err);
      setEvaluating(false);
      alert('Failed to generate food assessment.');
    }
  };

  return (
    <div className="label-scanner">
      <div style={{ marginBottom: 28, textAlign: 'center', maxWidth: 700, margin: '0 auto 28px' }}>
        <h1 style={{ fontSize: '2.2rem', color: 'var(--color-primary)', marginBottom: 8 }}>
          Food Label Scanner & Analysis
        </h1>
        <p style={{ color: 'var(--color-text-muted)', fontSize: '0.95rem' }}>
          Upload a food label photo for Apple Vision OCR extraction, look up a barcode, or manually enter nutrition facts.
        </p>
      </div>

      {/* Mode Switcher */}
      <div style={{ display: 'flex', justifyContent: 'center', gap: 10, marginBottom: 24 }}>
        <button
          className={`btn-secondary ${mode === 'upload' ? 'active' : ''}`}
          onClick={() => setMode('upload')}
          style={{ background: mode === 'upload' ? 'var(--color-primary)' : '#fff', color: mode === 'upload' ? '#fff' : 'inherit' }}
        >
          <Camera size={16} />
          <span>Upload Label Image (OCR)</span>
        </button>
        <button
          className={`btn-secondary ${mode === 'barcode' ? 'active' : ''}`}
          onClick={() => setMode('barcode')}
          style={{ background: mode === 'barcode' ? 'var(--color-primary)' : '#fff', color: mode === 'barcode' ? '#fff' : 'inherit' }}
        >
          <Barcode size={16} />
          <span>Barcode Lookup</span>
        </button>
        <button
          className={`btn-secondary ${mode === 'manual' ? 'active' : ''}`}
          onClick={() => setMode('manual')}
          style={{ background: mode === 'manual' ? 'var(--color-primary)' : '#fff', color: mode === 'manual' ? '#fff' : 'inherit' }}
        >
          <FileText size={16} />
          <span>Manual Entry</span>
        </button>
      </div>

      {/* Mode 1: Barcode Lookup */}
      {mode === 'barcode' && (
        <div className="card" style={{ maxWidth: 600, margin: '0 auto 30px', textAlign: 'center' }}>
          <Barcode size={40} color="var(--color-primary)" style={{ margin: '0 auto 12px' }} />
          <h3 style={{ fontSize: '1.2rem', marginBottom: 6 }}>Barcode Number Lookup</h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginBottom: 16 }}>
            Search the 852 Indian packaged products catalogue using an EAN-13 barcode (e.g. <code>8901030123456</code>).
          </p>
          <form onSubmit={handleBarcodeSearch} style={{ display: 'flex', gap: 8, maxWidth: 420, margin: '0 auto' }}>
            <input
              type="text"
              placeholder="Enter barcode digits..."
              value={barcodeInput}
              onChange={e => setBarcodeInput(e.target.value)}
              style={{
                flex: 1,
                padding: '10px 14px',
                borderRadius: 8,
                border: '1px solid var(--color-border)',
                fontSize: '0.95rem'
              }}
            />
            <button type="submit" className="btn-primary" style={{ padding: '10px 18px' }}>
              Lookup
            </button>
          </form>
          {barcodeError && (
            <div style={{ color: '#c62828', fontSize: '0.85rem', marginTop: 12, background: '#ffebee', padding: 8, borderRadius: 6 }}>
              {barcodeError}
            </div>
          )}
        </div>
      )}

      {/* Mode 2: Label Image Upload */}
      {mode === 'upload' && (
        <div className="card" style={{ maxWidth: 720, margin: '0 auto 30px' }}>
          <div style={{
            border: '2px dashed var(--color-border)',
            borderRadius: 12,
            padding: '36px 20px',
            textAlign: 'center',
            background: 'var(--color-surface-alt)',
            cursor: 'pointer',
            position: 'relative'
          }}>
            <input
              type="file"
              accept="image/png, image/jpeg, image/webp"
              onChange={handleFileUpload}
              style={{
                position: 'absolute',
                inset: 0,
                opacity: 0,
                cursor: 'pointer',
                width: '100%',
                height: '100%'
              }}
            />
            <Upload size={36} color="var(--color-accent)" style={{ margin: '0 auto 12px' }} />
            <h3 style={{ fontSize: '1.15rem', color: 'var(--color-primary)', marginBottom: 6 }}>
              Drop Food Label Photo or Click to Browse
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginBottom: 12 }}>
              Supports PNG, JPEG images of nutrition facts tables or ingredient lists.
            </p>
            <div style={{ display: 'inline-block', fontSize: '0.75rem', color: 'var(--color-text-subtle)', background: '#fff', padding: '4px 10px', borderRadius: 4, border: '1px solid var(--color-border)' }}>
              Engine: Apple Vision Text Recognition Framework (100% Offline Local Inference)
            </div>
          </div>

          {ocrLoading && (
            <div style={{ marginTop: 20, textAlign: 'center', padding: 20, background: '#eaf6e5', borderRadius: 8, color: 'var(--color-primary)' }}>
              <RefreshCw size={24} className="spin" style={{ margin: '0 auto 8px', animation: 'spin 1s linear infinite' }} />
              <div style={{ fontWeight: 700 }}>Extracting label text using Apple Vision OCR...</div>
              <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>Parsing serving sizes, macro values, and ingredients</div>
            </div>
          )}

          {ocrResult && (
            <div style={{ marginTop: 20, background: '#f8faf7', border: '1px solid var(--color-border)', borderRadius: 8, padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--color-accent)' }}>
                  ✓ OCR EXTRACTED TEXT
                </span>
                <span style={{ fontSize: '0.72rem', color: 'var(--color-text-subtle)' }}>
                  {ocrResult.ocr_engine}
                </span>
              </div>
              <div style={{ maxHeight: 120, overflowY: 'auto', background: '#fff', border: '1px solid #e2e8e0', borderRadius: 6, padding: 10, fontSize: '0.75rem', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                {ocrResult.raw_text}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', marginTop: 8 }}>
                ⚠️ <strong>Transparency Check:</strong> Verify or adjust the extracted values in the confirmation form below before generating the final assessment.
              </div>
            </div>
          )}
        </div>
      )}

      {/* Editable Confirmation Form */}
      <form onSubmit={handleGenerateAssessment} className="card" style={{ maxWidth: 840, margin: '0 auto' }}>
        <div style={{ borderBottom: '1px solid var(--color-border)', paddingBottom: 16, marginBottom: 20 }}>
          <h2 style={{ fontSize: '1.4rem', color: 'var(--color-primary)' }}>
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
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: 14, marginBottom: 18 }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, marginBottom: 4 }}>
              Product Name *
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
            <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, marginBottom: 4 }}>
              Brand
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
            <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, marginBottom: 4 }}>
              Category *
            </label>
            <select
              value={formData.category}
              onChange={e => setFormData({ ...formData, category: e.target.value })}
              style={inputStyle}
            >
              <option value="Snacks">Snacks (Calibrated)</option>
              <option value="Breakfast Cereals">Breakfast Cereals (Calibrated)</option>
              <option value="Packaged Beverages">Packaged Beverages (Calibrated)</option>
              <option value="Biscuits & Bakery">Biscuits & Bakery</option>
              <option value="Chocolates & Sweets">Chocolates & Sweets</option>
              <option value="Instant Foods">Instant Foods</option>
              <option value="Dairy">Dairy</option>
              <option value="Condiments & Spreads">Condiments & Spreads</option>
            </select>
          </div>
        </div>

        {/* Serving Size and Measurement Basis */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1.5fr', gap: 14, marginBottom: 18 }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, marginBottom: 4 }}>
              Serving Size
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
            <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, marginBottom: 4 }}>
              Unit
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
            <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, marginBottom: 4 }}>
              Measurement Basis
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
              <label style={labelStyle}>Calories (kcal)</label>
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
              <label style={labelStyle}>Total Sugars (g)</label>
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
              <label style={labelStyle}>Added Sugars (g)</label>
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
              <label style={labelStyle}>Sodium (mg)</label>
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
              <label style={labelStyle}>Protein (g)</label>
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
              <label style={labelStyle}>Total Fat (g)</label>
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
              <label style={labelStyle}>Saturated Fat (g)</label>
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
              <label style={labelStyle}>Dietary Fibre (g)</label>
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
          <label style={{ display: 'block', fontSize: '0.82rem', fontWeight: 700, marginBottom: 4 }}>
            Ingredients List
          </label>
          <textarea
            rows={3}
            placeholder="e.g. Potatoes, Edible Vegetable Oil (Palmolein), Salt, Red Chilli Powder, Amchur, INS 330..."
            value={formData.ingredients}
            onChange={e => setFormData({ ...formData, ingredients: e.target.value })}
            style={{ ...inputStyle, width: '100%', resize: 'vertical' }}
          />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 24 }}>
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
            style={{ padding: '12px 28px', fontSize: '1rem' }}
          >
            {evaluating ? 'Analyzing...' : 'Generate 3-Layer Assessment'}
            <ArrowRight size={18} />
          </button>
        </div>
      </form>
    </div>
  );
}

const inputStyle = {
  width: '100%',
  padding: '8px 12px',
  borderRadius: 6,
  border: '1px solid var(--color-border)',
  fontSize: '0.88rem',
  background: '#fff'
};

const labelStyle = {
  display: 'block',
  fontSize: '0.75rem',
  fontWeight: 600,
  color: 'var(--color-text-muted)',
  marginBottom: 4
};
