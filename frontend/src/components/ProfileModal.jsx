import React, { useState } from 'react';
import { X, Check, AlertCircle, Info, ShieldAlert } from 'lucide-react';

const GOALS = [
  { id: 'Reduce Sugar', title: 'Reduce Sugar', desc: 'Prioritizes foods with lower verified sugar and penalizes high sugar content.' },
  { id: 'Reduce Sodium', title: 'Reduce Sodium', desc: 'Focuses on low-sodium alternatives for cardiovascular and blood pressure management.' },
  { id: 'Increase Fibre', title: 'Increase Fibre', desc: 'Rewards verified dietary fibre content (>= 6g/100g) for metabolic and gut health.' },
  { id: 'Increase Protein', title: 'Increase Protein', desc: 'Favours higher protein foods (>= 10g/100g) to support muscle maintenance and satiety.' },
  { id: 'Balanced Choices', title: 'Balanced Choices', desc: 'Evaluates macronutrient and micronutrient balance holistically without single-nutrient obsession.' }
];

const PREFERENCES = [
  'No preference',
  'Vegetarian',
  'Vegan',
  'Lactose avoidance'
];

const COMMON_ALLERGENS = [
  'Milk',
  'Soy',
  'Gluten',
  'Peanuts',
  'Tree Nuts',
  'Eggs',
  'Fish',
  'Crustaceans',
  'Sesame',
  'Sulphites'
];

export default function ProfileModal({ isOpen, onClose, activeProfile, onSaveProfile }) {
  if (!isOpen) return null;

  const [formData, setFormData] = useState({
    name: activeProfile?.name || 'Health Conscious User',
    goal: activeProfile?.goal || 'Balanced Choices',
    dietary_preference: activeProfile?.dietary_preference || 'No preference',
    allergens: activeProfile?.allergens_to_avoid ? activeProfile.allergens_to_avoid.split(',').map(s => s.trim()).filter(Boolean) : [],
    customAllergen: '',
    age_group: activeProfile?.age_group || '18-24',
    activity_level: activeProfile?.activity_level || 'Moderately active'
  });

  const toggleAllergen = (allg) => {
    setFormData(prev => {
      const exists = prev.allergens.includes(allg);
      return {
        ...prev,
        allergens: exists ? prev.allergens.filter(a => a !== allg) : [...prev.allergens, allg]
      };
    });
  };

  const addCustomAllergen = (e) => {
    e.preventDefault();
    if (formData.customAllergen.trim() && !formData.allergens.includes(formData.customAllergen.trim())) {
      setFormData(prev => ({
        ...prev,
        allergens: [...prev.allergens, prev.customAllergen.trim()],
        customAllergen: ''
      }));
    }
  };

  const handleSave = () => {
    const payload = {
      ...activeProfile,
      name: formData.name,
      goal: formData.goal,
      dietary_preference: formData.dietary_preference,
      allergens_to_avoid: formData.allergens.join(', '),
      age_group: formData.age_group,
      activity_level: formData.activity_level
    };
    onSaveProfile(payload);
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={e => e.stopPropagation()} style={{ maxWidth: 640 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div>
            <h3 style={{ fontSize: '1.3rem', margin: 0, color: 'var(--color-primary)' }}>Personalized Nutrition Profile</h3>
            <p style={{ fontSize: '0.82rem', color: 'var(--color-text-muted)', marginTop: 4 }}>
              Configures transparent rules for Layer 2 personalized suitability scoring and Layer 3 allergen safety exclusions.
            </p>
          </div>
          <button onClick={onClose} style={{ padding: 6, borderRadius: 6, color: 'var(--color-text-subtle)' }}>
            <X size={20} />
          </button>
        </div>

        {/* 1. Primary Nutrition Goal */}
        <div style={{ marginBottom: 24 }}>
          <label style={{ display: 'block', fontWeight: 700, fontSize: '0.9rem', marginBottom: 8, color: 'var(--color-primary)' }}>
            1. Primary Nutrition Goal *
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 8 }}>
            {GOALS.map(g => {
              const isSelected = formData.goal === g.id;
              return (
                <div
                  key={g.id}
                  onClick={() => setFormData({ ...formData, goal: g.id })}
                  style={{
                    padding: '10px 14px',
                    borderRadius: 8,
                    border: isSelected ? '2px solid var(--color-accent)' : '1px solid var(--color-border)',
                    background: isSelected ? 'var(--color-accent-subtle)' : '#fff',
                    cursor: 'pointer',
                    transition: 'all 0.15s'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.9rem', color: isSelected ? 'var(--color-primary)' : 'var(--color-text-main)' }}>
                      {g.title}
                    </span>
                    {isSelected && <Check size={16} color="var(--color-accent)" />}
                  </div>
                  <p style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', marginTop: 4, margin: 0 }}>
                    {g.desc}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* 2. Dietary Preference */}
        <div style={{ marginBottom: 24 }}>
          <label style={{ display: 'block', fontWeight: 700, fontSize: '0.9rem', marginBottom: 8, color: 'var(--color-primary)' }}>
            2. Dietary Preference
          </label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {PREFERENCES.map(pref => {
              const isSelected = formData.dietary_preference === pref;
              return (
                <button
                  type="button"
                  key={pref}
                  onClick={() => setFormData({ ...formData, dietary_preference: pref })}
                  style={{
                    padding: '8px 14px',
                    borderRadius: 20,
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    border: isSelected ? '2px solid var(--color-accent)' : '1px solid var(--color-border)',
                    background: isSelected ? 'var(--color-accent-subtle)' : '#fff',
                    color: isSelected ? 'var(--color-primary)' : 'var(--color-text-main)'
                  }}
                >
                  {pref}
                </button>
              );
            })}
          </div>
        </div>

        {/* 3. Allergens to Avoid */}
        <div style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
            <label style={{ fontWeight: 700, fontSize: '0.9rem', color: 'var(--color-primary)', margin: 0 }}>
              3. Allergens to Avoid (Strict Safety Exclusions)
            </label>
            <ShieldAlert size={16} color="#c62828" />
          </div>
          <p style={{ fontSize: '0.78rem', color: 'var(--color-text-muted)', marginBottom: 10 }}>
            Selected allergens will trigger prominent red warnings and strictly exclude conflicting products from recommendations.
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
            {COMMON_ALLERGENS.map(allg => {
              const isChecked = formData.allergens.includes(allg);
              return (
                <button
                  type="button"
                  key={allg}
                  onClick={() => toggleAllergen(allg)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: 6,
                    fontSize: '0.82rem',
                    fontWeight: 600,
                    border: isChecked ? '1px solid #c62828' : '1px solid var(--color-border)',
                    background: isChecked ? '#ffebee' : '#fff',
                    color: isChecked ? '#c62828' : 'var(--color-text-main)'
                  }}
                >
                  {isChecked ? `✕ ${allg}` : `+ ${allg}`}
                </button>
              );
            })}
          </div>

          <form onSubmit={addCustomAllergen} style={{ display: 'flex', gap: 8 }}>
            <input
              type="text"
              placeholder="Add other allergen (e.g. Mustard, Pine nuts)..."
              value={formData.customAllergen}
              onChange={e => setFormData({ ...formData, customAllergen: e.target.value })}
              style={{
                flex: 1,
                padding: '8px 12px',
                borderRadius: 6,
                border: '1px solid var(--color-border)',
                fontSize: '0.85rem'
              }}
            />
            <button type="submit" className="btn-secondary" style={{ padding: '8px 14px', fontSize: '0.85rem' }}>
              Add
            </button>
          </form>
        </div>

        {/* 4. Optional Context */}
        <div style={{ padding: 14, background: 'var(--color-surface-alt)', borderRadius: 8, marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6, color: 'var(--color-text-muted)' }}>
            <Info size={15} />
            <span style={{ fontSize: '0.8rem', fontWeight: 700 }}>Optional Context (Stored Locally Only)</span>
          </div>
          <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', lineHeight: 1.4, margin: 0 }}>
            Demographic fields alone do not calculate medical requirements. EATGOOD does not prescribe clinical diets. Data is held in your local browser and SQLite instance.
          </p>
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          <button className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn-primary" onClick={handleSave}>
            Save Profile & Update Scoring
          </button>
        </div>
      </div>
    </div>
  );
}
