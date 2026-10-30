import React, { useRef, useState } from 'react';
import { Camera, ImageUp, ScanText } from 'lucide-react';
import { apiFetch } from '../api';
import { claimsFromText, readTextFromImage } from '../ocr';

// "Check the pack's claims": the visitor photographs the front of the pack (or types what it says),
// the text is read on their device, they confirm the claim lines, and the server checks them against
// this product's values. productId for catalogue products; product (the entered values) for scans.
export default function ClaimScanner({ productId, product, onChecked, children }) {
  const cameraRef = useRef(null);
  const uploadRef = useRef(null);
  const [claimsText, setClaimsText] = useState('');
  const [reading, setReading] = useState(null); // { status, progress } while reading a photo
  const [readNote, setReadNote] = useState('');
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState('');

  const handlePhoto = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    setError('');
    setReadNote('');
    setReading({ status: 'Preparing', progress: 0 });
    try {
      const text = await readTextFromImage(file, (status, progress) => setReading({ status, progress }));
      const found = claimsFromText(text);
      if (found.length === 0) {
        setReadNote('No claims could be read from that photo. Try a closer, well-lit photo of the front, or type the claims below.');
      } else {
        setClaimsText((prev) => [prev.trim(), ...found].filter(Boolean).join('\n'));
        setReadNote(`Read ${found.length} possible claim${found.length === 1 ? '' : 's'}. Check the wording and remove anything that isn't a claim.`);
      }
    } catch {
      setError('The photo could not be read on this device. Type the claims below instead.');
    } finally {
      setReading(null);
    }
  };

  const handleCheck = async () => {
    setChecking(true);
    setError('');
    try {
      // A catalogue product is checked by its id; anything else against the values shown on the page.
      const body = productId ? { claims: claimsText, product_id: productId } : { claims: claimsText, product };
      const data = await apiFetch('/api/claims/check', { method: 'POST', body });
      onChecked(data.claims || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setChecking(false);
    }
  };

  const phase = reading?.status?.includes('recogniz') ? 'Reading the text' : 'Loading the text reader';

  return (
    <section className="card claim-scanner" aria-labelledby="claim-scanner-title">
      <h3 id="claim-scanner-title">
        <ScanText size={20} aria-hidden="true" /> Check the pack&apos;s claims
      </h3>
      <p className="claim-scanner-intro">
        Photograph the front of the pack, or type what it claims (&ldquo;High protein&rdquo;, &ldquo;No added sugar&rdquo;…).
        The photo is read on your device and isn&apos;t uploaded; each claim is then checked against this product&apos;s values.
      </p>

      <div className="claim-scanner-actions">
        <button type="button" className="btn-primary btn-compact" onClick={() => cameraRef.current?.click()} disabled={!!reading}>
          <Camera size={16} aria-hidden="true" /> <span>Take a photo</span>
        </button>
        <button type="button" className="btn-secondary btn-compact" onClick={() => uploadRef.current?.click()} disabled={!!reading}>
          <ImageUp size={16} aria-hidden="true" /> <span>Upload a photo</span>
        </button>
        <input ref={cameraRef} type="file" accept="image/*" capture="environment" hidden onChange={handlePhoto} />
        <input ref={uploadRef} type="file" accept="image/*" hidden onChange={handlePhoto} />
      </div>

      {reading && (
        <div className="claim-scanner-progress" role="status">
          <span>{phase}… {Math.round((reading.progress || 0) * 100)}%</span>
          <span className="claim-scanner-track" aria-hidden="true"><span style={{ width: `${Math.round((reading.progress || 0) * 100)}%` }} /></span>
        </div>
      )}
      {readNote && <p className="claim-scanner-note" role="status">{readNote}</p>}

      <label htmlFor="claim-scanner-text" className="claim-scanner-label">Claims on the pack, one per line</label>
      <textarea
        id="claim-scanner-text"
        rows={4}
        value={claimsText}
        onChange={(e) => setClaimsText(e.target.value)}
        placeholder={'High protein\nNo added sugar\nGluten-free'}
      />
      {error && <p role="alert" className="claim-scanner-error">{error}</p>}
      <button type="button" className="btn-primary btn-compact" onClick={handleCheck} disabled={checking || !claimsText.trim()}>
        {checking ? 'Checking…' : 'Check these claims'}
      </button>
      {children}
    </section>
  );
}
