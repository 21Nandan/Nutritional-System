import React, { useEffect, useRef, useState } from 'react';
import { Camera } from 'lucide-react';
import { assistAvailable, readPhotoWithAi } from '../aiPhoto';


// The form fields a label photo fills (the same names in Manual Entry, the product page's edit form and
// the contribution form). Values the photo didn't show are left as they were.
export function applyLabelReading(read, prev) {
  const filled = Object.fromEntries(
    Object.entries(read.values || {}).filter(([, v]) => v != null).map(([k, v]) => [k, String(v)]),
  );
  return {
    ...prev,
    ...filled,
    ...(read.product_name && !prev.product_name ? { product_name: read.product_name } : {}),
    ...(read.brand && !prev.brand ? { brand: read.brand } : {}),
    ...(read.ingredients ? { ingredients: read.ingredients } : {}),
    ...(read.allergens ? { allergens_declared: read.allergens } : {}),
    ...(read.serving_size ? { serving_size: String(read.serving_size) } : {}),
    measurement_basis: read.measurement_basis || prev.measurement_basis,
    ...(read.measurement_basis === 'per 100ml' ? { serving_size_unit: 'ml' } : {}),
  };
}

// "Fill from a label photo": hidden unless photo reading is available. setForm takes an updater.
export default function LabelPhotoButton({ setForm }) {
  const inputRef = useRef(null);
  const [available, setAvailable] = useState(false);
  const [reading, setReading] = useState(false);
  const [note, setNote] = useState('');

  useEffect(() => {
    let cancelled = false;
    assistAvailable().then((ok) => { if (!cancelled) setAvailable(ok); });
    return () => { cancelled = true; };
  }, []);

  const handlePhoto = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    setReading(true);
    setNote('');
    const read = await readPhotoWithAi('read-label', file);
    setReading(false);
    if (!read) {
      setNote('The label couldn’t be read. Enter the values yourself.');
      return;
    }
    const count = Object.values(read.values || {}).filter((v) => v != null).length;
    setForm((prev) => applyLabelReading(read, prev));
    setNote(count
      ? `Filled ${count} value${count === 1 ? '' : 's'} from the photo. Check each one against the pack.`
      : 'No values could be read from that photo. Try a sharper photo of the nutrition table, or enter them yourself.');
  };

  if (!available) return null;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', margin: '10px 0' }}>
      <button type="button" className="btn-secondary btn-compact" onClick={() => inputRef.current?.click()} disabled={reading}>
        <Camera size={15} aria-hidden="true" />
        <span>{reading ? 'Reading the label…' : 'Fill from a label photo'}</span>
      </button>
      <input ref={inputRef} type="file" accept="image/*" capture="environment" hidden onChange={handlePhoto} />
      {note && <span role="status" style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>{note}</span>}
    </div>
  );
}
