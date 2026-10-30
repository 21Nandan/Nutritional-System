import React, { useEffect, useState } from 'react';
import { apiFetch } from '../api';
import { assistAvailable } from '../aiPhoto';

// "Explain these ingredients": what each item on the list is and why it's used. productId for catalogue
// products; ingredients (the text shown) for the visitor's own entries. Hidden when unavailable.
export default function IngredientExplainer({ productId, ingredients }) {
  const [available, setAvailable] = useState(false);
  const [items, setItems] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    assistAvailable().then((ok) => { if (!cancelled) setAvailable(ok); });
    return () => { cancelled = true; };
  }, []);
  useEffect(() => { setItems(null); setError(''); }, [productId, ingredients]);

  if (!available || !String(ingredients || '').trim()) return null;

  const explain = async () => {
    setLoading(true);
    setError('');
    try {
      const body = productId ? { product_id: productId } : { ingredients };
      const data = await apiFetch('/api/ai/explain-ingredients', { method: 'POST', body });
      setItems(data.items || []);
    } catch {
      setError('The ingredients couldn’t be explained right now. Try again later.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ingredient-explainer">
      {!items && (
        <button type="button" className="btn-secondary btn-compact" onClick={explain} disabled={loading}>
          {loading ? 'Explaining…' : 'Explain these ingredients'}
        </button>
      )}
      {error && <p role="alert" className="claim-scanner-error">{error}</p>}
      {items && (
        <ul className="ingredient-list">
          {items.map((it) => (
            <li key={it.as_listed}>
              <strong>{it.as_listed}</strong>: {it.what_it_is} {it.why_used}
              {it.note && <span className="ingredient-note"> Note: {it.note}.</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
