import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, FileText, Check, ArrowRight, ArrowLeft, 
  AlertTriangle, Lock, Sparkles, Heart, ShieldAlert, User, 
  CheckCircle2, Info, Activity, AlertCircle
} from 'lucide-react';
import { useLockBodyScroll } from './useLockBodyScroll';
import logoImg from '../assets/logo.png';

const GOALS = [
  { id: 'Reduce Sugar', title: 'Reduce Sugar', desc: 'Prioritizes lower sugar foods and penalizes high sugar content per WHO benchmarks.' },
  { id: 'Reduce Sodium', title: 'Reduce Sodium', desc: 'Focuses on low-sodium alternatives for cardiovascular health and blood pressure.' },
  { id: 'Increase Fibre', title: 'Increase Fibre', desc: 'Rewards foods rich in dietary fibre (>= 6g/100g) for digestive and metabolic health.' },
  { id: 'Increase Protein', title: 'Increase Protein', desc: 'Favours higher protein foods (>= 10g/100g) to support muscle health and satiety.' },
  { id: 'Balanced Choices', title: 'Balanced Choices', desc: 'Evaluates macronutrient and micronutrient balance holistically.' }
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

const ACTIVITY_LEVELS = [
  { id: 'Sedentary', title: 'Sedentary', desc: 'Little or no exercise; desk job.' },
  { id: 'Lightly active', title: 'Lightly Active', desc: 'Light exercise or walking 1–3 days/wk.' },
  { id: 'Moderately active', title: 'Moderately Active', desc: 'Moderate workout 3–5 days/wk.' },
  { id: 'Very active', title: 'Very Active', desc: 'Hard daily exercise or heavy physical work.' }
];

export default function OnboardingModal({ isOpen, activeProfile, onComplete }) {
  useLockBodyScroll(isOpen);

  const [step, setStep] = useState(1); // 1 = Terms & Disclaimer, 2 = Profile Setup
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [termsError, setTermsError] = useState(false);

  const parseGoals = (goalStr) => {
    if (!goalStr) return ['Balanced Choices'];
    const parts = goalStr.split(',').map(s => s.trim()).filter(Boolean);
    return parts.length > 0 ? parts : ['Balanced Choices'];
  };

  const [formData, setFormData] = useState({
    name: (activeProfile?.name && activeProfile.name !== 'Nandan' && activeProfile.name !== 'Guest User') ? activeProfile.name : '',
    goals: parseGoals(activeProfile?.goal),
    dietary_preference: activeProfile?.dietary_preference || 'No preference',
    allergens: activeProfile?.allergens_to_avoid ? activeProfile.allergens_to_avoid.split(',').map(s => s.trim()).filter(Boolean) : [],
    customAllergen: '',
    activity_level: activeProfile?.activity_level || 'Moderately active',
    age_group: activeProfile?.age_group || '18-24'
  });

  useEffect(() => {
    if (activeProfile) {
      setFormData(prev => ({
        ...prev,
        name: (activeProfile.name && activeProfile.name !== 'Nandan' && activeProfile.name !== 'Guest User') ? activeProfile.name : prev.name,
        goals: parseGoals(activeProfile.goal || prev.goals.join(', ')),
        dietary_preference: activeProfile.dietary_preference || prev.dietary_preference,
        allergens: activeProfile.allergens_to_avoid ? activeProfile.allergens_to_avoid.split(',').map(s => s.trim()).filter(Boolean) : prev.allergens,
        activity_level: activeProfile.activity_level || prev.activity_level,
        age_group: activeProfile.age_group || prev.age_group
      }));
    }
  }, [activeProfile]);

  if (!isOpen) return null;

  const toggleGoal = (goalId) => {
    setFormData(prev => {
      const exists = prev.goals.includes(goalId);
      let nextGoals;
      if (exists) {
        if (prev.goals.length === 1) return prev;
        nextGoals = prev.goals.filter(g => g !== goalId);
      } else {
        nextGoals = [...prev.goals, goalId];
      }
      return { ...prev, goals: nextGoals };
    });
  };

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

  const handleProceedToProfile = () => {
    if (!acceptedTerms) {
      setTermsError(true);
      return;
    }
    setTermsError(false);
    setStep(2);
  };

  const handleFinishSetup = () => {
    const payload = {
      ...activeProfile,
      name: formData.name.trim() || 'Guest User',
      goal: formData.goals.join(', '),
      dietary_preference: formData.dietary_preference,
      allergens_to_avoid: formData.allergens.join(', '),
      activity_level: formData.activity_level,
      age_group: formData.age_group
    };
    onComplete(payload);
  };

  return (
    <div 
      className="modal-overlay" 
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(10, 28, 18, 0.82)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 10000,
        padding: '16px',
        backdropFilter: 'blur(5px)'
      }}
    >
      <div 
        className="modal-card" 
        style={{
          background: '#fff',
          borderRadius: 16,
          maxWidth: 680,
          width: '100%',
          maxHeight: '92vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.35)',
          overflow: 'hidden',
          padding: 0
        }}
      >
        {/* Onboarding Header */}
        <div style={{
          padding: '20px 24px',
          background: 'linear-gradient(135deg, #143828 0%, #1e4d38 100%)',
          color: '#fff',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <img 
              src={logoImg} 
              alt="EATGOOD" 
              style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                background: '#fff',
                padding: 3,
                objectFit: 'contain',
                boxShadow: '0 2px 8px rgba(0,0,0,0.2)'
              }}
            />
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <h2 style={{ fontSize: '1.25rem', color: '#fff', margin: 0, fontWeight: 800 }}>
                  Welcome to EATGOOD
                </h2>
                <span style={{
                  fontSize: '0.68rem',
                  background: 'rgba(255,255,255,0.2)',
                  color: '#fff',
                  padding: '2px 8px',
                  borderRadius: 10,
                  fontWeight: 700,
                  textTransform: 'uppercase'
                }}>
                  Initial Setup
                </span>
              </div>
              <p style={{ fontSize: '0.78rem', color: '#b0c9bb', margin: '2px 0 0' }}>
                AI-Powered Personalized Food Safety & Nutrition Assessment
              </p>
            </div>
          </div>

          {/* Stepper Indicator */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{
              width: 26,
              height: 26,
              borderRadius: '50%',
              background: step === 1 ? '#fff' : '#2e7d32',
              color: step === 1 ? '#143828' : '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '0.78rem',
              fontWeight: 800
            }}>
              {step > 1 ? <Check size={14} /> : '1'}
            </div>
            <div style={{ width: 20, height: 2, background: step > 1 ? '#2e7d32' : 'rgba(255,255,255,0.3)' }} />
            <div style={{
              width: 26,
              height: 26,
              borderRadius: '50%',
              background: step === 2 ? '#fff' : 'rgba(255,255,255,0.2)',
              color: step === 2 ? '#143828' : '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '0.78rem',
              fontWeight: 800
            }}>
              2
            </div>
          </div>
        </div>

        {/* Scrollable Step Content */}
        <div style={{ padding: '24px', overflowY: 'auto', flex: 1, overscrollBehavior: 'contain' }}>
          
          {/* STEP 1: TERMS OF SERVICE & DISCLAIMER */}
          {step === 1 && (
            <div>
              <div style={{ marginBottom: 18 }}>
                <h3 style={{ fontSize: '1.25rem', color: 'var(--color-primary)', marginBottom: 4 }}>
                  Platform Terms & Health Safety Disclaimer
                </h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', lineHeight: 1.5 }}>
                  Before you begin exploring packaged foods and scanning labels, please review and accept our foundational privacy guarantee and food safety disclaimer.
                </p>
              </div>

              {/* 3 Core Platform Pillars */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 12, marginBottom: 20 }}>
                <div style={{
                  padding: '12px 14px',
                  background: '#f1f8e9',
                  border: '1px solid #c8e6c9',
                  borderRadius: 10
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#2e7d32', fontWeight: 700, fontSize: '0.85rem', marginBottom: 4 }}>
                    <Lock size={16} />
                    <span>100% Local-First Privacy</span>
                  </div>
                  <p style={{ fontSize: '0.76rem', color: '#1b5e20', margin: 0, lineHeight: 1.4 }}>
                    Your health goals, allergen restrictions, and food photographs stay entirely on your device. Zero cloud egress of personal information.
                  </p>
                </div>

                <div style={{
                  padding: '12px 14px',
                  background: '#fff8e1',
                  border: '1px solid #ffe082',
                  borderRadius: 10
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#e65100', fontWeight: 700, fontSize: '0.85rem', marginBottom: 4 }}>
                    <AlertTriangle size={16} />
                    <span>Not Medical Advice</span>
                  </div>
                  <p style={{ fontSize: '0.76rem', color: '#b73800', margin: 0, lineHeight: 1.4 }}>
                    EATGOOD provides computational nutritional assessments based on WHO/FSSAI reference models. It does not replace medical consultation.
                  </p>
                </div>

                <div style={{
                  padding: '12px 14px',
                  background: '#ffebee',
                  border: '1px solid #ffcdd2',
                  borderRadius: 10
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#c62828', fontWeight: 700, fontSize: '0.85rem', marginBottom: 4 }}>
                    <ShieldAlert size={16} />
                    <span>Severe Allergens Notice</span>
                  </div>
                  <p style={{ fontSize: '0.76rem', color: '#b71c1c', margin: 0, lineHeight: 1.4 }}>
                    For life-threatening anaphylactic food allergies, always inspect physical packaging. Formulations and factory cross-contact conditions may vary.
                  </p>
                </div>
              </div>

              {/* Scrollable Terms & Policy Summary */}
              <div style={{
                background: '#f8faf7',
                border: '1px solid var(--color-border)',
                borderRadius: 10,
                padding: '14px 18px',
                maxHeight: 180,
                overflowY: 'auto',
                fontSize: '0.8rem',
                color: 'var(--color-text-main)',
                lineHeight: 1.55,
                marginBottom: 20
              }}>
                <h4 style={{ margin: '0 0 6px', color: 'var(--color-primary)', fontSize: '0.88rem' }}>
                  Summary of Terms of Service & Data Ethics:
                </h4>
                <p style={{ margin: '0 0 8px' }}>
                  <strong>1. Educational Scope:</strong> EATGOOD evaluates food labels against published reference criteria (WHO SEARO Nutrient Profile Model 2017 and FSSAI guidelines). It does not issue official statutory compliance or certification.
                </p>
                <p style={{ margin: '0 0 8px' }}>
                  <strong>2. OCR & Barcode Verification:</strong> Optical text extraction from photographs and third-party barcode lookups (such as Open Food Facts) are subject to packaging clarity and community data accuracy. Users should confirm values before relying on results.
                </p>
                <p style={{ margin: '0 0 8px' }}>
                  <strong>3. Experimental Machine Learning:</strong> Any integrated suitability prediction operates as an experimental secondary perspective trained on synthetic benchmarks; deterministic evidence-based standards remain primary ground truth.
                </p>
                <p style={{ margin: 0 }}>
                  <strong>4. Limitation of Liability:</strong> Software is provided &quot;as is&quot;. Developers disclaim liability for individual health outcomes or consumer purchase decisions resulting from the tool.
                </p>
              </div>

              {/* Required Terms Acceptance Checkbox */}
              <div 
                onClick={() => {
                  setAcceptedTerms(!acceptedTerms);
                  setTermsError(false);
                }}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 12,
                  padding: '14px 16px',
                  borderRadius: 10,
                  border: termsError ? '2px solid #c62828' : (acceptedTerms ? '2px solid var(--color-accent)' : '1px solid var(--color-border)'),
                  background: acceptedTerms ? 'var(--color-accent-subtle)' : '#fff',
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                  marginBottom: 10
                }}
              >
                <div style={{
                  width: 22,
                  height: 22,
                  borderRadius: 6,
                  border: acceptedTerms ? '2px solid var(--color-accent)' : '2px solid var(--color-border)',
                  background: acceptedTerms ? 'var(--color-accent)' : '#fff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                  marginTop: 2
                }}>
                  {acceptedTerms && <Check size={16} color="#fff" strokeWidth={3} />}
                </div>

                <div style={{ fontSize: '0.85rem', color: 'var(--color-text-main)', lineHeight: 1.45 }}>
                  <strong style={{ color: acceptedTerms ? 'var(--color-primary)' : 'inherit' }}>
                    I have read, understood, and accept the Terms of Service, Privacy Policy, and Food Safety Disclaimer.
                  </strong>
                  <div style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)', marginTop: 2 }}>
                    Acceptance is required to configure your personalized nutrition profile and use the platform.
                  </div>
                </div>
              </div>

              {termsError && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#c62828', fontSize: '0.78rem', marginBottom: 12 }}>
                  <AlertCircle size={14} />
                  <span>Please check the acceptance box to proceed to profile setup.</span>
                </div>
              )}
            </div>
          )}

          {/* STEP 2: PERSONALIZED PROFILE SETUP */}
          {step === 2 && (
            <div>
              <div style={{ marginBottom: 20 }}>
                <h3 style={{ fontSize: '1.25rem', color: 'var(--color-primary)', marginBottom: 4 }}>
                  Configure Your Nutrition Profile
                </h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', lineHeight: 1.5 }}>
                  Set your individual health goals, dietary preferences, and allergens. This profile directly calculates the <strong>Layer 2 Personalized Suitability Score (1–100)</strong> and enforces <strong>Layer 3 Safety Exclusions</strong>.
                </p>
              </div>

              {/* Name Input */}
              <div style={{ marginBottom: 20 }}>
                <label style={{ display: 'block', fontWeight: 700, fontSize: '0.85rem', color: 'var(--color-primary)', marginBottom: 6 }}>
                  Your Name / Profile Nickname:
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={e => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g. Alex"
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: 8,
                    border: '1px solid var(--color-border)',
                    fontSize: '0.9rem',
                    background: '#fff'
                  }}
                />
              </div>

              {/* 1. Nutrition Goals */}
              <div style={{ marginBottom: 22 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
                  <label style={{ fontWeight: 700, fontSize: '0.88rem', color: 'var(--color-primary)', margin: 0 }}>
                    1. Primary Nutrition Goals *
                  </label>
                  <span style={{ fontSize: '0.75rem', color: 'var(--color-accent)', fontWeight: 600 }}>
                    (Select one or more)
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 8 }}>
                  {GOALS.map(g => {
                    const isSelected = formData.goals.includes(g.id);
                    return (
                      <div
                        key={g.id}
                        onClick={() => toggleGoal(g.id)}
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
                          <span style={{ fontWeight: 700, fontSize: '0.88rem', color: isSelected ? 'var(--color-primary)' : 'var(--color-text-main)' }}>
                            {g.title}
                          </span>
                          <div style={{
                            width: 18,
                            height: 18,
                            borderRadius: 4,
                            border: isSelected ? '2px solid var(--color-accent)' : '1px solid var(--color-border)',
                            background: isSelected ? 'var(--color-accent)' : '#fff',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                          }}>
                            {isSelected && <Check size={12} color="#fff" strokeWidth={3} />}
                          </div>
                        </div>
                        <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', margin: '3px 0 0' }}>
                          {g.desc}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* 2. Dietary Preference */}
              <div style={{ marginBottom: 22 }}>
                <label style={{ display: 'block', fontWeight: 700, fontSize: '0.88rem', color: 'var(--color-primary)', marginBottom: 8 }}>
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
                          padding: '7px 14px',
                          borderRadius: 20,
                          fontSize: '0.82rem',
                          fontWeight: 600,
                          border: isSelected ? '2px solid var(--color-accent)' : '1px solid var(--color-border)',
                          background: isSelected ? 'var(--color-accent-subtle)' : '#fff',
                          color: isSelected ? 'var(--color-primary)' : 'var(--color-text-main)',
                          cursor: 'pointer'
                        }}
                      >
                        {pref}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* 3. Allergens to Avoid */}
              <div style={{ marginBottom: 22 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                  <label style={{ fontWeight: 700, fontSize: '0.88rem', color: 'var(--color-primary)', margin: 0 }}>
                    3. Allergens to Avoid (Strict Safety Exclusions)
                  </label>
                  <ShieldAlert size={15} color="#c62828" />
                </div>
                <p style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginBottom: 8 }}>
                  Conflicting items trigger critical red alerts and are excluded from alternatives:
                </p>

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10 }}>
                  {COMMON_ALLERGENS.map(allg => {
                    const isChecked = formData.allergens.includes(allg);
                    return (
                      <button
                        type="button"
                        key={allg}
                        onClick={() => toggleAllergen(allg)}
                        style={{
                          padding: '5px 10px',
                          borderRadius: 6,
                          fontSize: '0.78rem',
                          fontWeight: 600,
                          border: isChecked ? '1px solid #c62828' : '1px solid var(--color-border)',
                          background: isChecked ? '#ffebee' : '#fff',
                          color: isChecked ? '#c62828' : 'var(--color-text-main)',
                          cursor: 'pointer'
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
                      fontSize: '0.82rem'
                    }}
                  />
                  <button type="submit" className="btn-secondary" style={{ padding: '8px 14px', fontSize: '0.82rem' }}>
                    Add
                  </button>
                </form>
              </div>

              {/* 4. Daily Activity Level */}
              <div style={{ marginBottom: 20 }}>
                <label style={{ display: 'block', fontWeight: 700, fontSize: '0.88rem', color: 'var(--color-primary)', marginBottom: 6 }}>
                  4. Daily Physical Activity Level
                </label>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 8 }}>
                  {ACTIVITY_LEVELS.map(act => {
                    const isSelected = formData.activity_level === act.id;
                    return (
                      <div
                        key={act.id}
                        onClick={() => setFormData({ ...formData, activity_level: act.id })}
                        style={{
                          padding: '8px 10px',
                          borderRadius: 8,
                          border: isSelected ? '2px solid var(--color-accent)' : '1px solid var(--color-border)',
                          background: isSelected ? 'var(--color-accent-subtle)' : '#fff',
                          cursor: 'pointer',
                          transition: 'all 0.15s',
                          textAlign: 'center'
                        }}
                      >
                        <div style={{ fontWeight: 700, fontSize: '0.82rem', color: isSelected ? 'var(--color-primary)' : 'var(--color-text-main)' }}>
                          {act.title}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', marginTop: 2, lineHeight: 1.25 }}>
                          {act.desc}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Privacy Footer Note */}
              <div style={{
                background: '#f8faf7',
                border: '1px solid var(--color-border)',
                borderRadius: 8,
                padding: '10px 14px',
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                fontSize: '0.75rem',
                color: 'var(--color-text-subtle)'
              }}>
                <Info size={15} color="var(--color-accent)" style={{ flexShrink: 0 }} />
                <span>You can edit or update your profile anytime via "Change Profile" or the User Profile page.</span>
              </div>
            </div>
          )}
        </div>

        {/* Modal Bottom Actions Footer */}
        <div style={{
          padding: '16px 24px',
          borderTop: '1px solid var(--color-border)',
          background: '#f8faf7',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 12
        }}>
          {step === 1 ? (
            <>
              <div style={{ fontSize: '0.75rem', color: 'var(--color-text-subtle)' }}>
                Step 1 of 2: Terms & Safety Agreement
              </div>
              <button
                type="button"
                className="btn-primary"
                onClick={handleProceedToProfile}
                style={{
                  padding: '10px 22px',
                  fontSize: '0.9rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  fontWeight: 700
                }}
              >
                <span>Continue to Profile Setup</span>
                <ArrowRight size={16} />
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setStep(1)}
                style={{
                  padding: '10px 16px',
                  fontSize: '0.85rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6
                }}
              >
                <ArrowLeft size={15} />
                <span>Back to Terms</span>
              </button>

              <button
                type="button"
                className="btn-primary"
                onClick={handleFinishSetup}
                style={{
                  padding: '10px 24px',
                  fontSize: '0.92rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  fontWeight: 700,
                  background: 'var(--color-primary)'
                }}
              >
                <CheckCircle2 size={16} />
                <span>Save Profile & Start Exploring</span>
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
