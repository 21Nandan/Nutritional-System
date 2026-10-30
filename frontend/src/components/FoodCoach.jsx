import React, { useEffect, useState } from 'react';
import { ChevronRight } from 'lucide-react';
import { apiFetch } from '../api';
import { GradeBadge } from './ScoreDisplay';

const EXAMPLES = ['High protein snack without peanuts', 'Low sugar breakfast cereal', 'A better swap for my biscuits'];

// "Ask about your food": patterns across the visitor's saved and recent products, and questions answered
// with products from the catalogue that fit their profile. ownIds: saved and recent catalogue product ids.
export default function FoodCoach({ ownIds, onSelectProduct }) {
  const [insights, setInsights] = useState(null);
  const [question, setQuestion] = useState('');
  const [asking, setAsking] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const idsKey = ownIds.join(',');

  useEffect(() => {
    if (ownIds.length < 2) { setInsights(null); return undefined; }
    const controller = new AbortController();
    apiFetch('/api/ai/coach/insights', { method: 'POST', body: { product_ids: ownIds }, signal: controller.signal })
      .then(setInsights)
      .catch(() => setInsights(null));
    return () => controller.abort();
  }, [idsKey]); // eslint-disable-line react-hooks/exhaustive-deps

  const ask = async (q) => {
    const text = (q ?? question).trim();
    if (!text) return;
    setQuestion(text);
    setAsking(true);
    setError('');
    setResult(null);
    try {
      setResult(await apiFetch('/api/ai/coach/ask', { method: 'POST', body: { question: text, product_ids: ownIds } }));
    } catch (err) {
      setError(err.message);
    } finally {
      setAsking(false);
    }
  };

  return (
    <div className="food-coach">
      {insights?.patterns?.length > 0 && (
        <div className="food-coach-insights">
          <strong>From your {insights.count} saved and recent products</strong>
          <ul>{insights.patterns.map((t) => <li key={t}>{t}</li>)}</ul>
          {insights.lowest?.length > 0 && (
            <p>
              Worth swapping:{' '}
              {insights.lowest.map((l, i) => (
                <React.Fragment key={l.product_id}>
                  {i > 0 && ', '}
                  <button type="button" className="compare-swap-link" onClick={() => onSelectProduct(l.product_id)}>{l.name}</button>
                  {` (grade ${l.grade})`}
                </React.Fragment>
              ))}
              . Its page lists healthier alternatives.
            </p>
          )}
        </div>
      )}

      <form className="food-coach-ask" onSubmit={(e) => { e.preventDefault(); ask(); }}>
        <input
          type="text"
          value={question}
          maxLength={500}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. A low sugar snack for my kid's tiffin"
          aria-label="Ask about food that fits your profile"
        />
        <button type="submit" className="btn-primary btn-compact" disabled={asking || !question.trim()}>
          {asking ? 'Finding…' : 'Ask'}
        </button>
      </form>
      {!result && !asking && (
        <div className="food-coach-examples">
          {EXAMPLES.map((ex) => (
            <button key={ex} type="button" className="btn-secondary btn-compact" onClick={() => ask(ex)}>{ex}</button>
          ))}
        </div>
      )}
      {error && <p role="alert" className="profile-error">{error}</p>}
      {result && (
        <div className="food-coach-result" role="status">
          {result.answer && <p>{result.answer}</p>}
          {result.products?.length > 0 ? (
            <ul className="profile-list">
              {result.products.map((p) => (
                <li key={p.product_id}>
                  <button type="button" className="profile-item" onClick={() => onSelectProduct(p.product_id)}>
                    <GradeBadge grade={p.general_grade} size="sm" showLabel={false} />
                    <span className="profile-item-text">
                      <span className="profile-item-brand">{p.brand}</span>
                      <span className="profile-item-name">{p.product_name}</span>
                      <span className="profile-item-meta">Goal Match {p.personalized_score ?? 'N/A'}/100 · {p.category}</span>
                    </span>
                    <ChevronRight size={16} color="var(--color-text-subtle)" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            !result.answer && <p>No catalogue products matched that. Try different words.</p>
          )}
        </div>
      )}
    </div>
  );
}
