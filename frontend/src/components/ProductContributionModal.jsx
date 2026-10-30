import React, { useState } from 'react';
import { 
  X, CheckCircle2, PlusCircle, 
  Sparkles, RefreshCw
} from 'lucide-react';
import { useLockBodyScroll } from './useLockBodyScroll';
import { apiFetch } from '../api';

/**
 * ProductContributionModal
 * Allows users to submit unlisted products to the local SQLite database.
 * Every submitted product is stored with 'user_submitted' status and
 * marked as "User Submitted (Unverified)" — never falsely verified.
 */
export default function ProductContributionModal({ 
  isOpen, 
  onClose, 
  initialBarcode = '', 
  onSuccessAssessment 
}) {
  useLockBodyScroll(isOpen);

  const [formData, setFormData] = useState({
    barcode: initialBarcode || '',
    product_name: '',
    brand: '',
    category: 'Snacks',
    sub_category: 'Packaged Snacks',
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
    submission_notes: ''
  });

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const [successData, setSuccessData] = useState(null);

  if (!isOpen) return null;

  const parseNum = (v) => (v === '' || v === null || isNaN(Number(v))) ? null : Number(v);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.barcode.trim()) {
      setSubmitError('Please provide a valid barcode number.');
      return;
    }
    if (!formData.product_name.trim()) {
      setSubmitError('Product name is required.');
      return;
    }

    setSubmitting(true);
    setSubmitError('');

    const payload = {
      barcode: formData.barcode.trim(),
      product_name: formData.product_name.trim(),
      brand: formData.brand.trim(),
      category: formData.category,
      sub_category: formData.sub_category,
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
      ingredients: formData.ingredients.trim(),
      allergens_declared: formData.allergens_declared.trim(),
      submission_notes: formData.submission_notes.trim()
    };

    try {
      const data = await apiFetch('/api/products/contribute', { method: 'POST', body: payload });
      setSuccessData(data);
    } catch (err) {
      setSubmitError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleImmediateAssess = () => {
    if (onSuccessAssessment && successData) {
      // Immediately assess the newly contributed product
      const productObj = {
        product_id: `USER_SUB_${formData.barcode.trim()}`,
        barcode: formData.barcode.trim(),
        product_name: formData.product_name.trim(),
        brand: formData.brand.trim() || 'Contributed',
        category: formData.category,
        sub_category: formData.sub_category,
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
        data_source: 'Local User Contribution (Pending Review)',
        data_confidence_status: 'User Submitted (Unverified)'
      };

      onClose();
      onSuccessAssessment(productObj);
    }
  };

  const inputStyle = {
    width: '100%',
    padding: '8px 12px',
    borderRadius: 6,
    border: '1px solid var(--color-border)',
    fontSize: '0.88rem',
    background: '#fff'
  };

  return (
    <div 
      className="modal-overlay" 
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        padding: 16,
        backdropFilter: 'blur(3px)'
      }}
    >
      <div 
        className="modal-content"
        onClick={e => e.stopPropagation()}
        style={{
          background: '#fff',
          borderRadius: 14,
          maxWidth: 680,
          width: '100%',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 20px 40px rgba(0,0,0,0.25)',
          overflow: 'hidden'
        }}
      >
        {/* Modal Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '16px 22px',
          borderBottom: '1px solid var(--color-border)',
          background: '#f8faf7'
        }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', color: 'var(--color-primary)', margin: 0 }}>
              Contribute Product to EATGOOD
            </h2>
            <p style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', margin: '2px 0 0' }}>
              Add unlisted packaged foods to your local database for instant assessment.
            </p>
          </div>
          <button 
            type="button" 
            onClick={onClose}
            aria-label="Close modal"
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}
          >
            <X size={20} color="var(--color-text-muted)" />
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: '20px 22px', overflowY: 'auto', flex: 1 }}>
          {successData ? (
            <div style={{ textAlign: 'center', padding: '24px 10px' }}>
              <div style={{
                width: 60,
                height: 60,
                borderRadius: '50%',
                background: '#e8f5e9',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px',
                color: '#2e7d32'
              }}>
                <CheckCircle2 size={36} />
              </div>
              <h3 style={{ fontSize: '1.3rem', color: 'var(--color-primary)', marginBottom: 8 }}>
                Product Added Successfully!
              </h3>
              <p style={{ fontSize: '0.88rem', color: 'var(--color-text-muted)', maxWidth: 460, margin: '0 auto 20px' }}>
                {successData.message}
              </p>

              <div style={{ display: 'flex', justifyContent: 'center', gap: 12, flexWrap: 'wrap' }}>
                <button
                  type="button"
                  onClick={handleImmediateAssess}
                  className="btn-primary"
                  style={{ padding: '10px 20px', fontSize: '0.9rem' }}
                >
                  <Sparkles size={16} />
                  <span>Run Food Assessment Now</span>
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="btn-secondary"
                  style={{ padding: '10px 18px', fontSize: '0.9rem' }}
                >
                  Done
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              {submitError && (
                <div style={{
                  background: '#ffebee',
                  border: '1px solid #ef9a9a',
                  color: '#c62828',
                  padding: '10px 14px',
                  borderRadius: 8,
                  fontSize: '0.85rem',
                  marginBottom: 16
                }}>
                  {submitError}
                </div>
              )}

              {/* Barcode & Basic Identifiers */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 14 }}>
                <div>
                  <label style={{ fontSize: '0.8rem', fontWeight: 700, display: 'block', marginBottom: 4 }}>
                    Barcode (GTIN / EAN-13) *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.barcode}
                    onChange={e => setFormData({ ...formData, barcode: e.target.value })}
                    placeholder="e.g. 8901030123456"
                    style={inputStyle}
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.8rem', fontWeight: 700, display: 'block', marginBottom: 4 }}>
                    Product Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.product_name}
                    onChange={e => setFormData({ ...formData, product_name: e.target.value })}
                    placeholder="e.g. Roasted Multigrain Crisps"
                    style={inputStyle}
                  />
                </div>

                <div>
                  <label style={{ fontSize: '0.8rem', fontWeight: 700, display: 'block', marginBottom: 4 }}>
                    Brand Name
                  </label>
                  <input
                    type="text"
                    value={formData.brand}
                    onChange={e => setFormData({ ...formData, brand: e.target.value })}
                    placeholder="e.g. NutriSnacks"
                    style={inputStyle}
                  />
                </div>
              </div>

              {/* Category & Measurement Basis */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: 12, marginBottom: 16 }}>
                <div>
                  <label style={{ fontSize: '0.8rem', fontWeight: 700, display: 'block', marginBottom: 4 }}>
                    Category *
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

                <div>
                  <label style={{ fontSize: '0.8rem', fontWeight: 700, display: 'block', marginBottom: 4 }}>
                    Serving Size
                  </label>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <input
                      type="number"
                      step="any"
                      value={formData.serving_size}
                      onChange={e => setFormData({ ...formData, serving_size: e.target.value })}
                      placeholder="100"
                      style={{ ...inputStyle, flex: 2 }}
                    />
                    <select
                      value={formData.serving_size_unit}
                      onChange={e => setFormData({ ...formData, serving_size_unit: e.target.value })}
                      style={{ ...inputStyle, flex: 1 }}
                    >
                      <option value="g">g</option>
                      <option value="ml">ml</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: '0.8rem', fontWeight: 700, display: 'block', marginBottom: 4 }}>
                    Measurement Basis
                  </label>
                  <select
                    value={formData.measurement_basis}
                    onChange={e => setFormData({ ...formData, measurement_basis: e.target.value })}
                    style={inputStyle}
                  >
                    <option value="per 100g">per 100g</option>
                    <option value="per 100ml">per 100ml</option>
                    <option value="per serving">per serving</option>
                  </select>
                </div>
              </div>

              {/* Nutrition Facts Section */}
              <div style={{
                background: '#f8faf7',
                border: '1px solid var(--color-border)',
                borderRadius: 8,
                padding: 14,
                marginBottom: 16
              }}>
                <span style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--color-primary)', textTransform: 'uppercase', display: 'block', marginBottom: 8 }}>
                  Nutrition Facts ({formData.measurement_basis})
                </span>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 10 }}>
                  <div>
                    <label style={{ fontSize: '0.72rem', color: 'var(--color-text-subtle)', display: 'block', marginBottom: 2 }}>
                      Energy (kcal)
                    </label>
                    <input
                      type="number"
                      step="any"
                      value={formData.energy_kcal}
                      onChange={e => setFormData({ ...formData, energy_kcal: e.target.value })}
                      placeholder="0"
                      style={inputStyle}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: '0.72rem', color: 'var(--color-text-subtle)', display: 'block', marginBottom: 2 }}>
                      Carbohydrates (g)
                    </label>
                    <input
                      type="number"
                      step="any"
                      value={formData.carbohydrates_g}
                      onChange={e => setFormData({ ...formData, carbohydrates_g: e.target.value })}
                      placeholder="0"
                      style={inputStyle}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: '0.72rem', color: 'var(--color-text-subtle)', display: 'block', marginBottom: 2 }}>
                      Total Sugars (g)
                    </label>
                    <input
                      type="number"
                      step="any"
                      value={formData.sugars_g}
                      onChange={e => setFormData({ ...formData, sugars_g: e.target.value })}
                      placeholder="0"
                      style={inputStyle}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: '0.72rem', color: 'var(--color-text-subtle)', display: 'block', marginBottom: 2 }}>
                      Added Sugars (g)
                    </label>
                    <input
                      type="number"
                      step="any"
                      value={formData.added_sugars_g}
                      onChange={e => setFormData({ ...formData, added_sugars_g: e.target.value })}
                      placeholder="0"
                      style={inputStyle}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: '0.72rem', color: 'var(--color-text-subtle)', display: 'block', marginBottom: 2 }}>
                      Protein (g)
                    </label>
                    <input
                      type="number"
                      step="any"
                      value={formData.protein_g}
                      onChange={e => setFormData({ ...formData, protein_g: e.target.value })}
                      placeholder="0"
                      style={inputStyle}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: '0.72rem', color: 'var(--color-text-subtle)', display: 'block', marginBottom: 2 }}>
                      Total Fat (g)
                    </label>
                    <input
                      type="number"
                      step="any"
                      value={formData.total_fat_g}
                      onChange={e => setFormData({ ...formData, total_fat_g: e.target.value })}
                      placeholder="0"
                      style={inputStyle}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: '0.72rem', color: 'var(--color-text-subtle)', display: 'block', marginBottom: 2 }}>
                      Saturated Fat (g)
                    </label>
                    <input
                      type="number"
                      step="any"
                      value={formData.saturated_fat_g}
                      onChange={e => setFormData({ ...formData, saturated_fat_g: e.target.value })}
                      placeholder="0"
                      style={inputStyle}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: '0.72rem', color: 'var(--color-text-subtle)', display: 'block', marginBottom: 2 }}>
                      Sodium (mg)
                    </label>
                    <input
                      type="number"
                      step="any"
                      value={formData.sodium_mg}
                      onChange={e => setFormData({ ...formData, sodium_mg: e.target.value })}
                      placeholder="0"
                      style={inputStyle}
                    />
                  </div>

                  <div>
                    <label style={{ fontSize: '0.72rem', color: 'var(--color-text-subtle)', display: 'block', marginBottom: 2 }}>
                      Dietary Fibre (g)
                    </label>
                    <input
                      type="number"
                      step="any"
                      value={formData.dietary_fibre_g}
                      onChange={e => setFormData({ ...formData, dietary_fibre_g: e.target.value })}
                      placeholder="0"
                      style={inputStyle}
                    />
                  </div>
                </div>
              </div>

              {/* Ingredients & Allergens */}
              <div style={{ marginBottom: 12 }}>
                <label style={{ fontSize: '0.8rem', fontWeight: 700, display: 'block', marginBottom: 4 }}>
                  Ingredients List (from packaging)
                </label>
                <textarea
                  rows={2}
                  value={formData.ingredients}
                  onChange={e => setFormData({ ...formData, ingredients: e.target.value })}
                  placeholder="e.g. Whole wheat, edible vegetable oil, iodised salt, spices and condiments..."
                  style={inputStyle}
                />
              </div>

              <div style={{ marginBottom: 18 }}>
                <label style={{ fontSize: '0.8rem', fontWeight: 700, display: 'block', marginBottom: 4 }}>
                  Declared Allergens (or "May contain...")
                </label>
                <input
                  type="text"
                  value={formData.allergens_declared}
                  onChange={e => setFormData({ ...formData, allergens_declared: e.target.value })}
                  placeholder="e.g. Contains Wheat, Milk. May contain Soy, Peanuts."
                  style={inputStyle}
                />
              </div>

              {/* Form Action Buttons */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, borderTop: '1px solid var(--color-border)', paddingTop: 14 }}>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={onClose}
                  style={{ padding: '8px 16px', fontSize: '0.88rem' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={submitting}
                  style={{ padding: '8px 22px', fontSize: '0.88rem', display: 'flex', alignItems: 'center', gap: 6 }}
                >
                  {submitting ? (
                    <>
                      <RefreshCw size={14} className="spin" style={{ animation: 'spin 1s linear infinite' }} />
                      <span>Saving to Local Database...</span>
                    </>
                  ) : (
                    <>
                      <PlusCircle size={15} />
                      <span>Contribute Product</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
