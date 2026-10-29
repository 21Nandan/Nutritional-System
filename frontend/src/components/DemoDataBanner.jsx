import React, { useEffect, useState } from 'react';
import { Info } from 'lucide-react';
import { apiFetch } from '../api';

// Always-visible notice: the catalogue is demo data and nothing here is medical advice.
export default function DemoDataBanner({ onOpenAudit }) {
  const [dataset, setDataset] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const controller = new AbortController();
    apiFetch('/api/dataset', { signal: controller.signal })
      .then(setDataset)
      .catch((err) => {
        if (err.name !== 'AbortError') setError(err.message);
      });
    return () => controller.abort();
  }, []);

  return (
    <div className="demo-banner" role="note" aria-label="About this information">
      <Info size={16} aria-hidden="true" />
      <p>
        <strong>Informational only — not medical advice.</strong>{' '}
        {dataset && dataset.provenance === 'synthetic' && (
          <>
            Catalogue nutrition values are <strong>demo data</strong> generated for testing, not read from real
            packs (dataset {dataset.dataset_version}). Always check the label.{' '}
          </>
        )}
        {error && <>Dataset information is unavailable right now ({error}). </>}
        <button type="button" className="demo-banner-link" onClick={onOpenAudit}>
          About the data
        </button>
      </p>
    </div>
  );
}
